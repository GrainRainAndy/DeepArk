import asyncio
from pathlib import Path
import sys
import time
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'plugins'/'deepark_companion'))
from batching import TurnBuffer

class BatchTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.b=TurnBuffer(quiet=.04,maximum=.10,max_messages=3,max_chars=100)
        self.addAsyncCleanup(self.b.close)
    async def test_idle_burst_one_leader_preserves_order(self):
        a=asyncio.create_task(self.b.enter('s','a',True,1))
        await asyncio.sleep(.015)
        b=asyncio.create_task(self.b.enter('s','b',True,1))
        turn=await a
        self.assertEqual(turn.items,['a','b']);self.assertIsNone(await b)
        await self.b.finish(turn);self.assertEqual(self.b.session_count,0)
    async def test_active_backlog_is_one_next_turn(self):
        first=await self.b.enter('s','first',True,5)
        tasks=[asyncio.create_task(self.b.enter('s',x,True,1)) for x in ['a','b','c']]
        await asyncio.sleep(.06);self.assertTrue(all(not t.done() for t in tasks))
        await self.b.finish(first)
        results=await asyncio.gather(*tasks);turn=results[0]
        self.assertEqual(turn.items,['a','b','c']);self.assertEqual(results[1:],[None,None])
        await self.b.finish(turn)
    async def test_media_barrier_and_limits(self):
        first=await self.b.enter('s','first',True,1)
        specs=[('a',True),('image',False),('b',True),('c',True),('d',True),('e',True)]
        tasks=[asyncio.create_task(self.b.enter('s',x,merge,1)) for x,merge in specs]
        await asyncio.sleep(.01);await self.b.finish(first)
        for index,expected in [(0,['a']),(1,['image']),(2,['b','c','d']),(5,['e'])]:
            turn=await tasks[index];self.assertEqual(turn.items,expected);await self.b.finish(turn)
        self.assertIsNone(await tasks[3]);self.assertIsNone(await tasks[4])
    async def test_hard_deadline_prevents_starvation(self):
        start=time.monotonic();tasks=[asyncio.create_task(self.b.enter('s','a',True,1))]
        for i in range(4):
            await asyncio.sleep(.025)
            if tasks[0].done():break
            tasks.append(asyncio.create_task(self.b.enter('s',str(i),True,1)))
        turn=await asyncio.wait_for(tasks[0],.08)
        self.assertLess(time.monotonic()-start,.19)
        await self.b.finish(turn)
        for t in tasks[1:]:
            x=await t
            if x:await self.b.finish(x)
    async def test_separate_sessions_not_blocked(self):
        a=await self.b.enter('a','x',True,1)
        b=await self.b.enter('b','y',True,1)
        self.assertEqual(b.items,['y']);await self.b.finish(a);await self.b.finish(b)
    async def test_cancel_pending_does_not_wedge_next(self):
        first=await self.b.enter('s','first',True,1)
        a=asyncio.create_task(self.b.enter('s','a',True,1));b=asyncio.create_task(self.b.enter('s','b',True,1))
        await asyncio.sleep(.01);a.cancel()
        with self.assertRaises(asyncio.CancelledError):await a
        await self.b.finish(first);turn=await b;self.assertEqual(turn.items,['b']);await self.b.finish(turn)
    async def test_close_releases_waiters_without_dropping(self):
        a=asyncio.create_task(self.b.enter('s','a',True,1));b=asyncio.create_task(self.b.enter('s','b',True,1))
        await asyncio.sleep(.01);await self.b.close()
        ra,rb=await asyncio.gather(a,b);self.assertEqual(ra.items,['a']);self.assertEqual(rb.items,['b'])
    async def test_character_limit_splits_without_truncation(self):
        self.b.max_chars=3
        a=asyncio.create_task(self.b.enter('s','aa',True,2));b=asyncio.create_task(self.b.enter('s','bb',True,2))
        turn=await a;self.assertEqual(turn.items,['aa']);await self.b.finish(turn)
        turn=await b;self.assertEqual(turn.items,['bb']);await self.b.finish(turn)

    async def test_close_cannot_resurrect_absorbed_messages(self):
        self.b.max_messages=2
        async def leader():
            turn=await self.b.enter('s','a',True,1)
            await self.b.close()
            return turn
        a=asyncio.create_task(leader());b=asyncio.create_task(self.b.enter('s','b',True,1))
        ra,rb=await asyncio.gather(a,b)
        self.assertEqual(ra.items,['a','b']);self.assertIsNone(rb)
        await self.b.finish(ra)
    async def test_close_cannot_resurrect_reset_discarded_messages(self):
        active=await self.b.enter('s','active',True,1)
        pending=asyncio.create_task(self.b.enter('s','old',True,1))
        await asyncio.sleep(.01)
        await self.b.discard_pending('s');await self.b.close()
        self.assertIsNone(await pending);await self.b.finish(active)
