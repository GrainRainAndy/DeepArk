"""Real SDK events and scheduler; all native/model/send boundaries are local fakes."""
import asyncio,types,unittest
from unittest.mock import AsyncMock,patch
from contextlib import aclosing
from astrbot.core.platform.astr_message_event import AstrMessageEvent
from astrbot.core.platform.astrbot_message import AstrBotMessage,MessageMember
from astrbot.core.platform.platform_metadata import PlatformMetadata
from astrbot.core.platform.message_type import MessageType
from astrbot.core.message.components import Plain,Image
from astrbot.core.pipeline.scheduler import PipelineScheduler
from plugins.deepark_companion.batch_bridge import BatchBridge

class Tests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.calls=[];self.sent=[];self.release=asyncio.Event();self.started=asyncio.Event()
        outer=self
        class Native:
            async def process(self,event):
                outer.calls.append(event.get_message_str())
                if event.get_message_str()=='hold':
                    outer.started.set();await outer.release.wait()
                if event.get_message_str()=='error':raise ValueError('synthetic')
                yield
        self.Native=Native;self.original=Native.process
        self.plugin=types.SimpleNamespace(config={'enabled':True,'batching_enabled':True,'batching_sessions':['test:FriendMessage:u'],'batch_quiet_seconds':.025,'batch_max_seconds':.08},context=types.SimpleNamespace(get_config=lambda scope:{'plugin_set':['*']}))
        self.bridge=BatchBridge(self.plugin)
        self.pref=patch('plugins.deepark_companion.batch_bridge.sp.get_async',new=AsyncMock(return_value={}));self.pref.start()
        self.addCleanup(self.pref.stop);self.addAsyncCleanup(self.bridge.close)
        self.bridge.install(Native)
    def event(self,text,scope='u',media=False):
        obj=AstrBotMessage();obj.type=MessageType.FRIEND_MESSAGE;obj.message_id=text;obj.sender=MessageMember(scope,'test');obj.self_id='bot';obj.group=None;obj.session_id=scope;obj.message=[Image(file='fake.png')] if media else [Plain(text)];obj.message_str=text
        e=AstrMessageEvent(text,obj,PlatformMetadata('aiocqhttp','test','test'),scope);e.is_at_or_wake_command=True
        return e
    async def consume(self,e):
        async with aclosing(self.Native().process(e)) as g:
            async for _ in g:
                self.sent.append(e.get_message_str())
                await asyncio.sleep(.015)
    async def test_burst_and_backlog_preserve_content_exactly_once(self):
        a=self.event('hold');task=asyncio.create_task(self.consume(a));await self.started.wait()
        es=[self.event(x) for x in ['a','b','c']];ts=[asyncio.create_task(self.consume(e)) for e in es]
        await asyncio.sleep(.04);self.assertEqual(self.calls,['hold'])
        self.release.set();await asyncio.gather(task,*ts)
        self.assertEqual(self.calls,['hold','a\nb\nc']);self.assertEqual(self.sent,self.calls)
        self.assertEqual(es[0].get_extra('deepark_batch_message_ids'),['a','b','c'])
        self.assertEqual(es[0].message_obj.message[0].text,'a\nb\nc')
    async def test_command_bypasses_busy_turn(self):
        task=asyncio.create_task(self.consume(self.event('hold')));await self.started.wait()
        await asyncio.wait_for(self.consume(self.event('/provider')), .1)
        self.assertIn('/provider',self.calls);self.release.set();await task
    async def test_media_is_fifo_barrier(self):
        task=asyncio.create_task(self.consume(self.event('hold')));await self.started.wait()
        ts=[asyncio.create_task(self.consume(e)) for e in [self.event('a'),self.event('image',media=True),self.event('b')]]
        await asyncio.sleep(.01);self.release.set();await asyncio.gather(task,*ts)
        self.assertEqual(self.calls,['hold','a','image','b'])
    async def test_other_session_and_disabled_plugin_bypass(self):
        e=self.event('other','someone');await self.consume(e);self.assertIsNone(e.get_extra('deepark_batch_count'))
        self.plugin.config['enabled']=False;e=self.event('disabled');await self.consume(e);self.assertIsNone(e.get_extra('deepark_batch_count'))
    async def test_failure_does_not_lock_next_turn(self):
        with self.assertRaises(ValueError):await self.consume(self.event('error'))
        await asyncio.wait_for(self.consume(self.event('after')),.2);self.assertEqual(self.calls,['error','after'])
    async def test_unload_restores_original(self):
        await self.bridge.close();self.assertIs(self.Native.process,self.original)
    async def test_gate_held_through_downstream_send(self):
        sent_start=asyncio.Event();release_send=asyncio.Event();outer=self
        class Send:
            async def process(self,e):
                if e.get_message_str()=='first':sent_start.set();await release_send.wait()
                outer.sent.append(e.get_message_str())
        sched=object.__new__(PipelineScheduler);sched.stages=[self.Native(),Send()]
        first=asyncio.create_task(sched._process_stages(self.event('first')))
        await sent_start.wait();later=asyncio.create_task(sched._process_stages(self.event('later')))
        await asyncio.sleep(.04);self.assertEqual(self.calls,['first'])
        release_send.set();await asyncio.gather(first,later);self.assertEqual(self.calls,['first','later'])

    async def test_unprefixed_registered_command_bypasses(self):
        from astrbot.core.star.filter.command import CommandFilter
        e=self.event('发说说 内容');e.set_extra('activated_handlers',[types.SimpleNamespace(event_filters=[CommandFilter('发说说')])])
        await self.consume(e);self.assertIsNone(e.get_extra('deepark_batch_count'))
    async def test_pending_reset_drops_only_unprocessed_batch(self):
        from astrbot.core.star.filter.command import CommandFilter
        a=asyncio.create_task(self.consume(self.event('hold')));await self.started.wait()
        b=asyncio.create_task(self.consume(self.event('old')));await asyncio.sleep(.01)
        e=self.event('/reset');e.set_extra('activated_handlers',[types.SimpleNamespace(event_filters=[CommandFilter('reset')])])
        await self.consume(e);self.release.set();await asyncio.gather(a,b)
        self.assertEqual(self.calls,['hold','/reset'])
    async def test_merged_text_rechecked_by_native_safety(self):
        self.plugin.context.get_config=lambda scope:{'plugin_set':['*'],'content_safety':{'internal_keywords':{'enable':True,'extra_keywords':['a\\s+b']},'baidu_aip':{'enable':False}}}
        a=asyncio.create_task(self.consume(self.event('a')));b=asyncio.create_task(self.consume(self.event('b')))
        await asyncio.gather(a,b);self.assertEqual(self.calls,[])

if __name__=='__main__':unittest.main()
