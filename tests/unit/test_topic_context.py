import json
import unittest
from plugins.deepark_topic_context.core import TopicState, TopicStore

class TopicTests(unittest.TestCase):
    def add(self,s,i,topic="game",relation="main",user="a",at=None,text=None):
        now=i if at is None else at
        s.observe(str(i),user,text or "synthetic message "+str(i),now)
        self.assertTrue(s.apply(json.dumps({"messages":[{"id":str(i),"topic":topic,"relation":relation}]}),[str(i)],now))

    def test_asides_do_not_switch(self):
        s=TopicState(0)
        for i in range(5): self.add(s,i)
        self.add(s,5,"food","aside")
        self.add(s,6,"food","aside")
        self.assertEqual(s.topic,"game")
        self.assertTrue(any(m["relation"]=="aside" for m in s.context(6)["messages"]))

    def test_sustained_switch_and_old_topic_excluded(self):
        s=TopicState(0)
        self.add(s,0)
        for i in range(1,5): self.add(s,i,"food","candidate",user=str(i%2))
        self.assertEqual(s.topic,"food")
        self.assertEqual(s.context(5)["main_topic"],"food")
        self.assertIn("4",[m["id"] for m in s.context(5)["messages"]])

    def test_single_speaker_needs_four(self):
        s=TopicState(0); self.add(s,0)
        for i in range(1,4): self.add(s,i,"food","candidate")
        self.assertEqual(s.topic,"game")
        self.add(s,4,"food","candidate")
        self.assertEqual(s.topic,"food")

    def test_replay_and_duplicates(self):
        s=TopicState(0); self.add(s,0)
        self.assertFalse(s.observe("0","a","duplicate",1))
        raw=json.dumps({"messages":[{"id":"0","topic":"food","relation":"candidate"}]})
        for _ in range(10): s.apply(raw,["0"],2)
        self.assertEqual(s.topic,"game")

    def test_invalid_response_atomic(self):
        s=TopicState(0); s.observe("1","a","hello",0)
        for raw in ['bad','[]','{"messages":[{"id":"foreign","topic":"x","relation":"main"}]}']:
            self.assertFalse(s.apply(raw,["1"],1))
            self.assertEqual(s.topic,"")

    def test_mentions_keep_main(self):
        s=TopicState(0); self.add(s,0)
        self.add(s,1,"food","aside",text="please answer this")
        c=s.context(1,"1")
        self.assertEqual(c["main_topic"],"game")
        self.assertEqual(next(x for x in c["messages"] if x["id"]=="1")["relation"],"addressed")

    def test_budget_bounds(self):
        s=TopicState(0)
        for i in range(150): self.add(s,i,text="x"*2000,user=str(i%10))
        self.assertEqual(len(s.messages),96)
        c=s.context(149)
        self.assertLessEqual(sum(len(x["text"]) for x in c["messages"]),6000)
        self.assertLessEqual(c["metrics"]["estimated_idle_seconds"],900)

    def test_activity_adapts(self):
        quiet=TopicState(0); self.add(quiet,0)
        busy=TopicState(0)
        for i in range(20): self.add(busy,i,user=str(i%5))
        self.assertGreater(busy.metrics(20)["context_chars"],quiet.metrics(20)["context_chars"])
        self.assertLess(busy.metrics(20)["aside_weight"],quiet.metrics(20)["aside_weight"])

    def test_idle_expiry_and_isolation(self):
        store=TopicStore(max_sessions=2,ttl=60)
        a=store.get("a",0); self.add(a,0)
        self.assertEqual(store.get("b",1).topic,"")
        store.get("c",2)
        self.assertNotIn("a",store.sessions)
        self.assertEqual(store.get("b",100).topic,"")
        self.assertEqual(a.context(1000)["main_topic"],"")

    def test_probe_limits(self):
        s=TopicState(0); s.observe("1","a","hello",0)
        self.assertTrue(s.reserve_probe(0,hourly_limit=1))
        self.assertFalse(s.reserve_probe(20,hourly_limit=1))
        self.assertTrue(s.reserve_probe(3600,hourly_limit=1))

    def test_sparse_candidate_does_not_accumulate(self):
        s=TopicState(0); self.add(s,0)
        for i in range(1,6): self.add(s,i,"food","candidate",at=i*150,user=str(i%2))
        self.assertEqual(s.topic,"game")

    def test_long_aside_gets_reserved_context(self):
        s=TopicState(0)
        for i in range(20): self.add(s,i,text="main"*250,user=str(i%4))
        self.add(s,20,"food","aside",text="aside"*200)
        context=s.context(20)
        aside=next(m for m in context["messages"] if m["id"]=="20")
        self.assertGreater(len(aside["text"]),0)
        self.assertTrue(any(m["relation"]=="main" for m in context["messages"]))
        self.assertLessEqual(sum(len(m["text"]) for m in context["messages"]),context["metrics"]["context_chars"])

    def test_pending_backlog_does_not_replay_old_switches(self):
        s=TopicState(0)
        for i in range(20): s.observe(str(i),'a','text',i)
        self.assertEqual([m.id for m in s.pending()],[str(i) for i in range(12,20)])
        self.assertTrue(all(m.relation=='aside' for m in list(s.messages)[:12]))

    def test_idle_deadline_is_not_shortened_by_expiring_metric_window(self):
        s=TopicState(0)
        for i in range(20):self.add(s,i,user=str(i))
        deadline=s.idle_until
        self.assertGreater(deadline,400)
        self.assertEqual(s.context(350)['main_topic'],'game')
        self.assertEqual(s.context(deadline+1)['main_topic'],'')

    def test_busy_topic_requires_more_switch_evidence(self):
        s=TopicState(0)
        for i in range(8):self.add(s,i,user=str(i%4))
        for i in range(8,11):self.add(s,i,'food','candidate',user=str(i%2))
        self.assertEqual(s.topic,'game')
        self.add(s,11,'food','candidate',user='b')
        self.assertEqual(s.topic,'food')
