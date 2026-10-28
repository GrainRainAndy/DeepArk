"""Run inside AstrBot's Python environment against real SDK types; no QQ/API I/O."""
import asyncio
import json
from pathlib import Path
import tempfile
import time
import types
import unittest
from unittest.mock import patch

from plugins.deepark_companion.main import DeeparkCompanion
from plugins.deepark_companion.core import Store
from astrbot.api.provider import ProviderRequest


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def followup_event(self,decision='followup',quoted_sender=None):
        from astrbot.core.message.components import Reply
        now=time.time()
        self.bot.store.observe(self.scope,'u1','before','你怎么看？',now-15)
        self.bot.store.record_bot(self.scope,'我觉得阿米娅这个皮肤挺好看',now-10)
        self.bot.store.observe(self.scope,'u1','current','为什么这么说？',now)
        extras={}
        event=types.SimpleNamespace(unified_msg_origin=self.scope,get_group_id=lambda:'42',get_sender_id=lambda:'u1',get_self_id=lambda:'bot',get_message_str=lambda:'为什么这么说？',message_obj=types.SimpleNamespace(message=[] if quoted_sender is None else [Reply(id='ref',sender_id=quoted_sender)]),set_extra=lambda k,v:extras.update({k:v}),is_at_or_wake_command=False)
        async def judge(scope,history,actions,hints):return decision if decision in actions else 'skip'
        self.bot.participation_decision=judge
        return event,extras

    async def test_agent_followup_wakes_native_flow_during_long_cooldown(self):
        event,extras=await self.followup_event()
        self.assertTrue(await self.bot.maybe_participate(event))
        self.assertTrue(event.is_at_or_wake_command)
        self.assertTrue(extras['deepark_followup'])
        self.assertFalse(self.bot.store.reserve(self.scope,'interject',time.time()))

    async def test_agent_can_skip_even_a_quote_of_bot(self):
        event,_=await self.followup_event('skip','bot')
        self.assertFalse(await self.bot.maybe_participate(event))
        self.assertFalse(event.is_at_or_wake_command)

    async def test_quote_to_another_member_cannot_bypass_cooldown_as_followup(self):
        event,_=await self.followup_event('followup','other')
        self.assertFalse(await self.bot.maybe_participate(event))

    async def test_disabled_followup_and_muted_group_do_not_wake(self):
        event,_=await self.followup_event()
        self.bot.store.mute(self.scope,True)
        self.assertFalse(await self.bot.maybe_participate(event))

    async def test_mute_after_agent_decision_suppresses_native_response(self):
        from astrbot.api.provider import LLMResponse
        event,extras=await self.followup_event()
        event.get_extra=lambda k,d=None:extras.get(k,d)
        stopped=[];event.stop_event=lambda:stopped.append(True)
        self.assertTrue(await self.bot.maybe_participate(event))
        self.bot.store.mute(self.scope,True)
        response=LLMResponse(role='assistant',completion_text='不应该发送')
        await self.bot.after_response(event,response)
        self.assertEqual(response.completion_text,'')
        self.assertTrue(stopped)

    async def test_disable_after_agent_decision_suppresses_native_response(self):
        from astrbot.api.provider import LLMResponse
        event,extras=await self.followup_event()
        event.get_extra=lambda k,d=None:extras.get(k,d)
        event.stop_event=lambda:None
        self.assertTrue(await self.bot.maybe_participate(event))
        self.bot.config['enabled']=False
        response=LLMResponse(role='assistant',completion_text='不应该发送')
        await self.bot.after_response(event,response)
        self.assertEqual(response.completion_text,'')

    async def test_rejected_output_with_concurrent_mute_sends_no_apology(self):
        from astrbot.api.provider import LLMResponse
        event,extras=await self.followup_event()
        event.get_extra=lambda k,d=None:extras.get(k,d)
        event.stop_event=lambda:None
        self.assertTrue(await self.bot.maybe_participate(event))
        async def reject(scope,text):
            self.bot.store.mute(scope,True)
            return False
        self.bot.output_allowed=reject
        response=LLMResponse(role='assistant',completion_text='不应该发送')
        await self.bot.after_response(event,response)
        self.assertEqual(response.completion_text,'')

    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.bot=DeeparkCompanion.__new__(DeeparkCompanion)
        self.bot.config={'enabled':True,'proactive_enabled':True,'dry_run':False,'auto_memory':True}
        self.bot.store=Store(Path(self.tmp.name)/'test.db')
        self.addCleanup(self.bot.store.close)
        self.bot.busy=set()
        self.bot.tasks=set()
        self.bot.extraction_at={}
        self.bot.semaphore=asyncio.Semaphore(2)
        self.native={'platform_settings':{'enable_id_white_list':True,'id_whitelist':['42']},'provider_settings':{'enable':True},'plugin_set':['*']}
        self.preferences={}
        self.bot.context=types.SimpleNamespace(get_config=lambda _:self.native)
        async def read(**kw):return self.preferences.get(kw['key'],{})
        self.mock=patch('plugins.deepark_companion.main.sp.get_async',read)
        self.mock.start();self.addCleanup(self.mock.stop)
        self.scope='qq:GroupMessage:42'

    async def test_native_session_and_llm_disabled_stop_background(self):
        for key in ['session_enabled','llm_enabled']:
            self.preferences['session_service_config']={key:False}
            self.assertFalse(await self.bot.allowed(self.scope,'42'),key)

    async def test_per_session_plugin_disable_stops_background(self):
        self.preferences['session_plugin_config']={self.scope:{'disabled_plugins':['deepark_companion']}}
        self.assertFalse(await self.bot.allowed(self.scope,'42'))

    async def test_empty_allowlist_and_foreign_group_are_denied(self):
        self.assertFalse(await self.bot.allowed('qq:GroupMessage:99','99'))
        self.native['platform_settings']['id_whitelist']=[]
        self.assertFalse(await self.bot.allowed(self.scope,'42'))

    async def test_nonadmin_cannot_mute_or_write_group_memory(self):
        self.bot.command(self.scope,'u1','安静',False)
        self.bot.store.observe(self.scope,'u1','a','明日方舟的讨论',time.time())
        self.assertFalse(self.bot.store.db.execute('SELECT muted FROM sessions').fetchone()[0])
        self.bot.command(self.scope,'u1','群记住 梗=博士是土豆',False)
        self.assertEqual(self.bot.store.recall(self.scope,'@group','',time.time()),[])

    async def test_group_memory_shared_but_private_memory_not(self):
        self.bot.command(self.scope,'u1','群记住 梗=博士是土豆',True)
        self.bot.command(self.scope,'u1','记住 推=阿米娅',False)
        extra={}
        event=types.SimpleNamespace(unified_msg_origin=self.scope,get_group_id=lambda:'42',get_sender_id=lambda:'u2',get_message_str=lambda:'博士',set_extra=lambda k,v:extra.update({k:v}),get_extra=lambda k,d=None:extra.get(k,d))
        req=ProviderRequest(system_prompt='人格',contexts=[])
        await self.bot.inject(event,req)
        self.assertIn('博士是土豆',req.system_prompt)
        self.assertNotIn('阿米娅',req.system_prompt)

    async def test_forgotten_history_cannot_reenter_from_native_context(self):
        now=time.time()
        self.bot.store.observe(self.scope,'u1','a','我喜欢阿米娅',now)
        self.bot.store.record_bot(self.scope,'知道你喜欢阿米娅',now+0.1)
        self.bot.command(self.scope,'u1','忘记 全部',False)
        event=types.SimpleNamespace(unified_msg_origin=self.scope,get_group_id=lambda:'42',get_sender_id=lambda:'u1',get_message_str=lambda:'你好',set_extra=lambda k,v:None,get_extra=lambda k,d=None:d)
        req=ProviderRequest(system_prompt='人格',contexts=[{'role':'user','content':'我喜欢阿米娅'}])
        req.func_tool=object()  # Framework-injected history/send tools must not survive.
        await self.bot.inject(event,req)
        self.assertEqual(req.contexts,[])
        self.assertIsNone(req.func_tool)
        self.assertNotIn('阿米娅',req.system_prompt)

    async def test_model_cannot_select_another_memory_owner(self):
        async def generate(*args):return json.dumps([{'subject':'victim','key':'favorite_operator','value':'我喜欢阿米娅','evidence':'我喜欢阿米娅'}])
        self.bot.generate=generate
        await self.bot.extract(self.scope,'u1','我喜欢阿米娅',0)
        self.assertEqual(self.bot.store.recall(self.scope,'victim','',time.time()),[])
        self.assertEqual(len(self.bot.store.recall(self.scope,'u1','',time.time())),1)

    async def test_hallucinated_evidence_cannot_enter_memory(self):
        async def generate(*args):return '[{"key":"favorite_operator","value":"我喜欢能天使","evidence":"我喜欢能天使"}]'
        self.bot.generate=generate
        await self.bot.extract(self.scope,'u1','我喜欢阿米娅',0)
        self.assertEqual(self.bot.store.recall(self.scope,'u1','',time.time()),[])

    async def test_output_checks_custom_rules_and_fails_closed_on_invalid_regex(self):
        self.native['content_safety']={'internal_keywords':{'enable':True,'extra_keywords':['测试禁词']},'baidu_aip':{'enable':False}}
        self.assertFalse(await self.bot.output_allowed(self.scope,'测试禁词'))
        self.assertTrue(await self.bot.output_allowed(self.scope,'今天想聊哪个干员？'))
        self.native['content_safety']['internal_keywords']['extra_keywords']=['[']
        self.assertFalse(await self.bot.output_allowed(self.scope,'普通消息'))

    async def run_proactive(self, change=None, dry_run=False):
        # Fixed daytime clock; real Store and real MessageChain, fake network boundary.
        from datetime import datetime
        from zoneinfo import ZoneInfo
        now=datetime(2026,10,27,14,tzinfo=ZoneInfo('Asia/Shanghai')).timestamp()
        self.bot.config['dry_run']=dry_run
        self.bot.store.observe(self.scope,'u1','one','明日方舟今天想聊哪个干员',now-30)
        self.assertTrue(self.bot.store.reserve(self.scope,'interject',now))
        sent=[]
        async def send(scope,chain):sent.append((scope,chain));return True
        self.bot.context.send_message=send
        async def persona(scope):return '测试人格'
        self.bot.persona=persona
        async def check(scope,text):return True
        self.bot.output_allowed=check
        async def generate(*args):
            if change:change(now)
            return '今天有没有人想聊阿米娅？'
        self.bot.generate=generate
        with patch('plugins.deepark_companion.main.time.time',return_value=now+1):
            await self.bot.unsolicited(self.scope,'interject')
        self.assertEqual(self.bot.busy,set())
        return sent

    async def test_proactive_valid_request_sends_once_to_reserved_group(self):
        sent=await self.run_proactive()
        self.assertEqual(len(sent),1)
        self.assertEqual(sent[0][0],self.scope)

    async def test_dry_run_never_sends(self):
        self.assertEqual(await self.run_proactive(dry_run=True),[])

    async def test_mute_during_generation_prevents_send(self):
        self.assertEqual(await self.run_proactive(lambda _:self.bot.store.mute(self.scope,True)),[])

    async def test_new_group_message_during_generation_prevents_stale_send(self):
        self.assertEqual(await self.run_proactive(lambda now:self.bot.store.observe(self.scope,'u2','two','换个话题吧',now+0.5)),[])

    async def test_plugin_disable_during_generation_prevents_send(self):
        self.assertEqual(await self.run_proactive(lambda _:self.bot.config.update(enabled=False)),[])

    async def test_other_users_deletion_invalidates_inflight_reply(self):
        from astrbot.api.provider import LLMResponse
        extras={}
        event=types.SimpleNamespace(unified_msg_origin=self.scope,get_group_id=lambda:'42',get_sender_id=lambda:'u2',get_message_str=lambda:'你好',set_extra=lambda k,v:extras.update({k:v}),get_extra=lambda k,d=None:extras.get(k,d))
        self.bot.store.observe(self.scope,'u1','a','我喜欢阿米娅',time.time())
        await self.bot.inject(event,ProviderRequest(system_prompt='人格',contexts=[]))
        self.bot.store.forget(self.scope,'u1',None,time.time())
        response=LLMResponse(role='assistant',completion_text='u1喜欢阿米娅')
        await self.bot.after_response(event,response)
        self.assertNotIn('阿米娅',response.completion_text)
        self.assertFalse(self.bot.store.history(self.scope,time.time()))

    async def test_deletion_during_output_check_invalidates_reply(self):
        from astrbot.api.provider import LLMResponse
        extras={}
        event=types.SimpleNamespace(unified_msg_origin=self.scope,get_group_id=lambda:'42',get_sender_id=lambda:'u2',get_message_str=lambda:'你好',set_extra=lambda k,v:extras.update({k:v}),get_extra=lambda k,d=None:extras.get(k,d))
        await self.bot.inject(event,ProviderRequest(system_prompt='人格',contexts=[]))
        async def check(scope,text):
            self.bot.store.forget(scope,'u1',None,time.time())
            return True
        self.bot.output_allowed=check
        response=LLMResponse(role='assistant',completion_text='u1喜欢阿米娅')
        await self.bot.after_response(event,response)
        self.assertNotIn('阿米娅',response.completion_text)

    async def test_deletion_during_final_permission_check_blocks_proactive(self):
        allowed=self.bot.allowed
        calls=0
        async def check(scope,group):
            nonlocal calls
            calls+=1
            if calls==2:self.bot.store.forget(scope,'u1',None,time.time())
            return await allowed(scope,group)
        self.bot.allowed=check
        self.assertEqual(await self.run_proactive(),[])

    async def test_ecosystem_tools_follow_runtime_admin_and_initiative(self):
        from astrbot.core.agent.tool import ToolSet, FunctionTool
        self.bot.config.update(ecosystem_tool_guard=True, memory_tools=['recall_long_term_memory'], admin_social_tools=['llm_publish_feed'])
        for admin, initiative, expected in [(False,False,['recall_long_term_memory']),(True,False,['recall_long_term_memory','llm_publish_feed']),(True,True,['recall_long_term_memory'])]:
            event=types.SimpleNamespace(is_admin=lambda:admin,get_extra=lambda k,d=None:initiative if k=='deepark_followup' else d,get_group_id=lambda:'')
            req=ProviderRequest(system_prompt='人格',contexts=[])
            req.func_tool=ToolSet(tools=[FunctionTool(name=n,description='test',parameters={'type':'object'}) for n in ['recall_long_term_memory','llm_publish_feed','send_message_to_user']])
            await self.bot.inject(event,req)
            self.assertEqual([t.name for t in req.func_tool.tools],expected)

    async def test_livingmemory_keeps_native_context_without_old_memory(self):
        self.bot.config['memory_backend']='livingmemory'
        self.bot.command(self.scope,'u1','记住 推=阿米娅',False)
        event=types.SimpleNamespace(unified_msg_origin=self.scope,get_group_id=lambda:'42',get_sender_id=lambda:'u1',set_extra=lambda k,v:None,get_extra=lambda k,d=None:d)
        history=[{'role':'user','content':'native context'}]
        req=ProviderRequest(system_prompt='人格',contexts=history)
        await self.bot.inject(event,req)
        self.assertEqual(req.contexts,history)
        self.assertNotIn('阿米娅',req.system_prompt)
        self.assertIn('/lmem',self.bot.command(self.scope,'u1','记忆',False))

    async def test_batch_ack_can_be_silent_but_real_question_cannot(self):
        from astrbot.api.provider import LLMResponse
        for text,allowed in [('行（',True),('你要进群吗',False)]:
            extras={'deepark_batch_count':1}
            event=types.SimpleNamespace(get_group_id=lambda:'',get_message_str=lambda:text,get_extra=lambda k,d=None:extras.get(k,d),set_extra=lambda k,v:extras.update({k:v}),stop_event=lambda:extras.update(stopped=True))
            req=ProviderRequest(system_prompt='人格',contexts=[])
            await self.bot.inject(event,req)
            self.assertEqual(bool(extras.get('deepark_allow_silence')),allowed)
            response=LLMResponse(role='assistant',completion_text='[[DEEPARK_SILENT]]')
            await self.bot.after_response(event,response)
            self.assertEqual(response.completion_text=='',allowed)

    async def test_known_draft_leak_stops_before_sending(self):
        from astrbot.api.provider import LLMResponse
        extras={}
        e=types.SimpleNamespace(get_group_id=lambda:'',get_extra=lambda k,d=None:extras.get(k,d),stop_event=lambda:extras.update(stopped=True))
        response=LLMResponse(role='assistant',completion_text='去吧 Not fitting. Maybe no image. Keep text only.去吃饭')
        await self.bot.after_response(e,response)
        self.assertTrue(extras.get('stopped'));self.assertEqual(response.completion_text,'');self.assertIsNone(response.result_chain)


if __name__=='__main__':unittest.main()
