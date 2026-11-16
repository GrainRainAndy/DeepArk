"""Real SDK models, fake event transport/provider; never connect to QQ or models."""
import asyncio
from collections import deque
import json
import time
import types
import unittest
from unittest.mock import AsyncMock, patch
from astrbot.api.provider import ProviderRequest, LLMResponse
from astrbot.core.message.components import Plain, At
from plugins.deepark_topic_context.main import DeeparkTopicContext
from plugins.deepark_topic_context.core import TopicStore
from plugins.deepark_companion.main import DeeparkCompanion


class TopicAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.scope='qq:GroupMessage:42'
        self.bot=DeeparkTopicContext.__new__(DeeparkTopicContext)
        self.bot.config={'enabled':True,'allowed_sessions':[self.scope],'classifier_provider_id':'fake'}
        self.bot.store=TopicStore(); self.bot.inflight=set()
        self.bot.global_probes=deque(); self.bot.semaphore=asyncio.Semaphore(2)
        self.native={'platform_settings':{'id_whitelist':['42']},'plugin_set':['*']}
        self.prefs={}
        async def classify(**kw):
            payload=json.loads(kw['prompt'])
            return LLMResponse(role='assistant',completion_text=json.dumps({'messages':[
                {'id':m['id'],'topic':'synthetic game','relation':'main'} for m in payload['messages']]}))
        self.provider=AsyncMock(side_effect=classify)
        self.bot.context=types.SimpleNamespace(get_config=lambda _:self.native,llm_generate=self.provider)
        async def read(**kw):return self.prefs.get(kw['key'],{})
        self.mock=patch('plugins.deepark_topic_context.main.sp.get_async',read)
        self.mock.start();self.addCleanup(self.mock.stop)

    def event(self,mid='1',text='synthetic game question',addressed=False):
        extra={}
        return types.SimpleNamespace(unified_msg_origin=self.scope,get_group_id=lambda:'42',
            get_platform_name=lambda:'aiocqhttp',plugins_name=None,get_sender_id=lambda:'user1',
            get_self_id=lambda:'bot',is_at_or_wake_command=addressed,
            message_obj=types.SimpleNamespace(message_id=mid,message=[Plain(text=text)]+([At(qq='bot')] if addressed else [])),
            set_extra=lambda k,v:extra.update({k:v}),get_extra=lambda k,d=None:extra.get(k,d))

    async def test_observe_and_enrich_preserves_tool_history(self):
        e=self.event(); await self.bot.observe(e)
        req=ProviderRequest(system_prompt='persona',contexts=[{'role':'user','content':'keep'}])
        await self.bot.inject(e,req)
        self.assertIn('synthetic game',req.system_prompt)
        self.assertEqual(req.contexts,[{'role':'user','content':'keep'}])
        self.assertEqual(self.provider.await_count,1)
        prompt=req.system_prompt; await self.bot.inject(e,req)
        self.assertEqual(req.system_prompt,prompt)
        second=ProviderRequest(system_prompt='persona')
        await self.bot.inject(e,second)
        self.assertIn('TOPIC_DATA_JSON',second.system_prompt)

    async def test_disabled_and_revoked_authorization(self):
        e=self.event(); self.bot.config['enabled']=False
        await self.bot.observe(e); self.provider.assert_not_awaited()
        self.bot.config['enabled']=True
        await self.bot.observe(e)
        self.native['platform_settings']['id_whitelist']=[]
        req=ProviderRequest(system_prompt='persona'); await self.bot.inject(e,req)
        self.assertEqual(req.system_prompt,'persona')
        self.assertNotIn(self.scope,self.bot.store.sessions)

    async def test_unknown_group_private_and_service_disabled(self):
        e=self.event(); e.get_group_id=lambda:''
        await self.bot.observe(e); self.provider.assert_not_awaited()
        e=self.event(); self.prefs['session_service_config']={'llm_enabled':False}
        await self.bot.observe(e); self.provider.assert_not_awaited()
        self.prefs.clear(); self.bot.config['allowed_sessions']=[]
        await self.bot.observe(e); self.provider.assert_not_awaited()

    async def test_explicit_mention_not_companion_wakeup(self):
        e=self.event(addressed=True); await self.bot.observe(e)
        e.is_at_or_wake_command=True
        data=await self.bot.snapshot(e)
        self.assertEqual(data['addressed_id'],'1')
        e=self.event('2'); await self.bot.observe(e)
        e.is_at_or_wake_command=True
        self.assertIsNone((await self.bot.snapshot(e))['addressed_id'])

    async def test_timeout_keeps_context_and_does_not_raise(self):
        self.provider.side_effect=asyncio.TimeoutError
        e=self.event(); await self.bot.observe(e)
        self.assertEqual(len(self.bot.store.sessions[self.scope].messages),1)
        self.assertEqual(self.bot.store.sessions[self.scope].topic,'')

    async def test_revoke_during_provider_call(self):
        async def revoke(**kw):
            self.bot.config['enabled']=False
            return LLMResponse(role='assistant',completion_text='{"messages":[]}')
        self.provider.side_effect=revoke
        await self.bot.observe(self.event())
        self.assertNotIn(self.scope,self.bot.store.sessions)

    async def test_forget_during_provider_call_cannot_restore_state(self):
        async def forget(**kw):
            self.bot.store.forget(self.scope)
            return LLMResponse(role='assistant',completion_text='{"messages":[{"id":"1","topic":"x","relation":"main"}]}')
        self.provider.side_effect=forget
        await self.bot.observe(self.event())
        self.assertNotIn(self.scope,self.bot.store.sessions)

    async def test_duplicate_throttle_and_global_budget(self):
        e=self.event(); await self.bot.observe(e); await self.bot.observe(e)
        await self.bot.observe(self.event('2'))
        self.assertEqual(self.provider.await_count,1)
        self.bot.global_probes=deque([time.monotonic()]*120)
        s=self.bot.store.sessions[self.scope]; s.last_probe=-1000000
        await self.bot.observe(self.event('3'))
        self.assertEqual(self.provider.await_count,1)

    async def test_forgetting_command_purges_topic(self):
        await self.bot.observe(self.event())
        await self.bot.observe(self.event('2','/deepark 忘记 全部'))
        self.assertNotIn(self.scope,self.bot.store.sessions)

    async def test_bridge_present_absent_and_failure(self):
        companion=DeeparkCompanion.__new__(DeeparkCompanion)
        e=self.event(); self.assertIsNone(await companion.topic_snapshot(e))
        await self.bot.observe(e)
        self.assertEqual((await companion.topic_snapshot(e))['main_topic'],'synthetic game')
        async def fail():raise RuntimeError('synthetic failure')
        e.set_extra('deepark_topic_snapshot',fail)
        self.assertIsNone(await companion.topic_snapshot(e))

    async def test_bridge_supplies_dynamic_decision_history(self):
        companion=DeeparkCompanion.__new__(DeeparkCompanion)
        seen=[]
        async def generate(scope,prompt,*args,**kwargs):seen.append(json.loads(prompt)); return '{"action":"skip"}'
        companion.generate=generate; companion.config={}
        history=[{'subject':'synthetic','text':str(i)} for i in range(12)]
        await companion.participation_decision(self.scope,history,[],{'topic_context':{'main_topic':'x'}})
        self.assertEqual(len(seen[-1]['recent_messages']),12)
        await companion.participation_decision(self.scope,history,[],{})
        self.assertEqual(len(seen[-1]['recent_messages']),8)

    async def test_revoked_response_clears_text_tools_and_chain(self):
        e=self.event(); stopped=[]; e.stop_event=lambda:stopped.append(True)
        await self.bot.observe(e)
        req=ProviderRequest(system_prompt='persona'); await self.bot.inject(e,req)
        self.bot.store.forget(self.scope)
        response=LLMResponse(role='assistant',completion_text='stale',tools_call_name=['fake'],tools_call_args=[{}])
        await self.bot.guard_response(e,response)
        self.assertEqual(response.completion_text,'')
        self.assertEqual(response.tools_call_name,[])
        self.assertIsNone(response.result_chain)
        self.assertTrue(stopped)

    async def test_failed_classification_preserves_existing_prompt(self):
        self.provider.side_effect=asyncio.TimeoutError
        e=self.event(); await self.bot.observe(e)
        req=ProviderRequest(system_prompt='persona'); await self.bot.inject(e,req)
        self.assertEqual(req.system_prompt,'persona')

    async def test_bot_context_is_request_scoped_and_budgeted(self):
        e=self.event(); await self.bot.observe(e)
        req=ProviderRequest(system_prompt='persona')
        e.set_extra('deepark_topic_bot_context',(req,[{'subject':'@bot','text':'b'*300}]))
        await self.bot.inject(e,req)
        data=json.loads(req.system_prompt.split('TOPIC_DATA_JSON:\n')[1])
        self.assertEqual(data['recent_bot_messages'][0]['text'],'b'*300)
        self.assertLessEqual(sum(len(m['text']) for m in data['messages'])+300,data['metrics']['context_chars'])
        other=ProviderRequest(system_prompt='persona'); await self.bot.inject(e,other)
        data=json.loads(other.system_prompt.split('TOPIC_DATA_JSON:\n')[1])
        self.assertEqual(data['recent_bot_messages'],[])

    async def test_companion_and_topic_inject_once_and_keep_bot_reply(self):
        from pathlib import Path
        import tempfile
        from plugins.deepark_companion.core import Store
        temp=tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        companion=DeeparkCompanion.__new__(DeeparkCompanion)
        companion.config={'enabled':True,'memory_backend':'local'}
        companion.context=self.bot.context
        companion.store=Store(Path(temp.name)/'test.db'); self.addCleanup(companion.store.close)
        e=self.event(text='unique synthetic human message',addressed=True)
        e.get_message_str=lambda:'unique synthetic human message'
        companion.store.observe(self.scope,'user1','1',e.get_message_str(),time.time())
        companion.store.record_bot(self.scope,'unique synthetic bot answer',time.time())
        await self.bot.observe(e)
        req=ProviderRequest(system_prompt='persona',contexts=[])
        await companion.inject(e,req)
        await self.bot.inject(e,req)
        self.assertEqual(req.system_prompt.count('unique synthetic human message'),1)
        self.assertEqual(req.system_prompt.count('unique synthetic bot answer'),1)
        self.assertEqual(req.system_prompt.count('TOPIC_DATA_JSON'),1)
        self.assertTrue(e.get_extra('enable_streaming') is False)
