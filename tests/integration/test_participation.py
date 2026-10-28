"""Synthetic SDK regression tests. No real sends or providers."""
import asyncio,json,time,unittest
from types import SimpleNamespace
from unittest.mock import patch,AsyncMock
from tests.integration import test_adapter as support
from tests.integration import test_public_profile as profiles
from astrbot.api.provider import LLMResponse,ProviderRequest

class ParticipationSDKTests(unittest.IsolatedAsyncioTestCase):
 asyncSetUp=support.AdapterTests.asyncSetUp
 followup_event=support.AdapterTests.followup_event
 async def prepared(self):
  e,x=await self.followup_event();e.get_extra=lambda k,d=None:x.get(k,d);e.stop_event=lambda:x.update(stopped=True)
  self.assertTrue(await self.bot.maybe_participate(e))
  async def check(*a):return True
  self.bot.output_allowed=check
  return e,x
 async def test_symbol_after_request_does_not_cancel(self):
  e,x=await self.prepared();self.bot.store.observe(self.scope,'u1','star','*',time.time()+.001)
  r=LLMResponse(role='assistant',completion_text='听懂了，不就是吐槽我嘛')
  await self.bot.after_response(e,r);self.assertTrue(r.completion_text);self.assertFalse(x.get('stopped',False))
 async def test_new_meaningful_message_gets_semantic_keep_or_drop(self):
  for keep in (True,False):
   # fresh fixtures for the second scenario
   if not keep:self.bot.store.db.execute('DELETE FROM followup_probes');self.bot.store.db.commit()
   e,x=await self.prepared();self.bot.store.observe(self.scope,'u2',str(keep),'接着聊，我也喜欢这个皮肤',time.time()+.001)
   async def generate(*a,**kw):return json.dumps({'keep':keep})
   self.bot.generate=generate
   r=LLMResponse(role='assistant',completion_text='这个配色我也喜欢')
   await self.bot.after_response(e,r);self.assertEqual(bool(r.completion_text),keep)
 async def test_new_message_during_decision_can_still_wake(self):
  e,x=await self.followup_event();e.get_extra=lambda k,d=None:x.get(k,d)
  async def judge(*a,**kw):
   self.bot.store.observe(self.scope,'u1','new','*',time.time()+.001);return 'followup'
  self.bot.participation_decision=judge
  self.assertTrue(await self.bot.maybe_participate(e))
 async def test_four_short_messages_do_not_close_followup_window(self):
  e,x=await self.followup_event();e.get_extra=lambda k,d=None:x.get(k,d)
  for i in range(5):self.bot.store.observe(self.scope,'u1',str(i),'（',time.time()+i*.001)
  self.assertTrue(await self.bot.maybe_participate(e))
 async def test_reply_budget_blocks_301st_before_send(self):
  e,x=await self.prepared()
  for _ in range(300):self.bot.store.reserve_reply(self.scope,time.time())
  r=LLMResponse(role='assistant',completion_text='不应发送')
  await self.bot.after_response(e,r);self.assertEqual(r.completion_text,'');self.assertTrue(x.get('stopped'))
 async def test_new_bot_reply_makes_previous_implicit_reply_stale(self):
  e,x=await self.prepared();self.bot.store.record_bot(self.scope,'另一轮已经回答',time.time()+.001)
  r=LLMResponse(role='assistant',completion_text='旧回复');await self.bot.after_response(e,r)
  self.assertEqual(r.completion_text,'')

 async def test_relevance_failure_skips_safely(self):
  e,x=await self.prepared();self.bot.store.observe(self.scope,'u1','correction','不对，我刚才说错了',time.time()+.001)
  async def failed(*a,**kw):raise TimeoutError()
  self.bot.generate=failed
  r=LLMResponse(role='assistant',completion_text='旧回复');await self.bot.after_response(e,r)
  self.assertEqual(r.completion_text,'')
 async def test_memory_deleted_during_final_semantic_check_blocks_reply(self):
  e,x=await self.prepared();x['deepark_revision']=0;x['deepark_generation']=0
  async def check(*a):
   self.bot.store.observe(self.scope,'u1','later','这个配色也不错',time.time()+.001);return True
  async def generate(*a,**kw):
   self.bot.store.forget(self.scope,'u1',None,time.time());return '{"keep":true}'
  self.bot.output_allowed=check;self.bot.generate=generate
  r=LLMResponse(role='assistant',completion_text='旧记忆');await self.bot.after_response(e,r)
  self.assertEqual(r.completion_text,'')
 async def test_more_messages_collected_before_decision_and_injected(self):
  e,x=await self.followup_event();e.get_extra=lambda k,d=None:x.get(k,d);e.stop_event=lambda:x.update(stopped=True)
  self.bot.config.update(group_collect_seconds=.03,memory_backend='livingmemory');self.bot.news_context=lambda:''
  seen=[]
  async def judge(scope,hist,*a):seen.extend(hist);return 'followup'
  self.bot.participation_decision=judge
  task=asyncio.create_task(self.bot.maybe_participate(e));await asyncio.sleep(.01)
  self.bot.store.observe(self.scope,'u1','supplement','尤其喜欢它的配色',time.time())
  self.assertTrue(await task);self.assertTrue(any(x['text']=='尤其喜欢它的配色' for x in seen))
  req=ProviderRequest(system_prompt='',contexts=[]);await self.bot.inject(e,req)
  self.assertIn('尤其喜欢它的配色',req.system_prompt)
 async def test_interject_enabled_at_night_but_not_quiet_hours(self):
  import datetime
  from zoneinfo import ZoneInfo
  self.bot.store.policy.update(active_start_hour=9,active_end_hour=4,bot_quiet_seconds=60,unsolicited_gap_seconds=120,interject_daily_limit=-1)
  for hour,expected in [(3,True),(4,False)]:
   now=datetime.datetime(2026,10,27,hour,30,tzinfo=ZoneInfo('Asia/Shanghai')).timestamp()
   with patch('plugins.deepark_companion.main.time.time',return_value=now):
    e,x=await self.followup_event('interject');e.get_extra=lambda k,d=None:x.get(k,d)
    self.bot.store.db.execute('UPDATE sessions SET last_bot=?,last_unsolicited=0',(now-600,));self.bot.store.db.execute('UPDATE followups SET last_bot=?',(now-600,));self.bot.store.db.execute('DELETE FROM followup_probes');self.bot.store.db.commit()
    self.assertEqual(await self.bot.maybe_participate(e),expected)

class CommandSDKTests(profiles.ProfileSDKTests):
 async def test_real_wake_stage_strips_slash_but_public_command_works(self):
  from astrbot.core.pipeline.waking_check.stage import WakingCheckStage
  from astrbot.core.star.star_handler import star_handlers_registry
  from astrbot.core.star.session_plugin_manager import SessionPluginManager
  e=self.event('/deepark 公开记住 昵称=小雨')
  stage=WakingCheckStage();stage.ctx=SimpleNamespace(astrbot_config={**self.native,'admins_id':[],'wake_prefix':['/']})
  stage.ignore_bot_self_message=True;stage.ignore_at_all=True;stage.friend_message_needs_wake_prefix=False;stage.disable_builtin_commands=False
  stage._umo_auto_name_recorder=SimpleNamespace(schedule=lambda e:None)
  with patch.object(star_handlers_registry,'get_handlers_by_event_type',return_value=[]),patch.object(SessionPluginManager,'filter_handlers_by_session',new=AsyncMock(return_value=[])):
   await stage.process(e)
  self.assertEqual(e.get_message_str(),'deepark 公开记住 昵称=小雨')
  result=await self.command(e);self.assertTrue(result)
  req=ProviderRequest(system_prompt='',contexts=[]);await self.bot.inject(self.event(group=True),req)
  self.assertIn('小雨',req.system_prompt)

 async def test_profile_withdrawal_during_final_semantic_call_blocks_reply(self):
  from plugins.deepark_companion.public_profile import identity
  self.bot.config['dry_run']=False
  await self.command(self.event('/deepark 公开记住 昵称=小雨'))
  e=self.event('为什么',group=True);now=time.time()
  self.bot.store.record_bot(self.group,'之前的回答',now-10)
  self.bot.store.observe(self.group,'12345','question','为什么',now)
  e.set_extra('deepark_followup',True);e.set_extra('deepark_participation_snapshot',now)
  await self.bot.inject(e,ProviderRequest(system_prompt='',contexts=[]))
  async def check(*a):
   self.bot.store.observe(self.group,'12345','extra','还有这个配色',time.time()+.001);return True
  async def generate(*a,**kw):
   self.bot.public_profiles.forget(identity(self.private,'99999','12345'),'全部')
   return '{"keep":true}'
  self.bot.output_allowed=check;self.bot.generate=generate
  r=LLMResponse(role='assistant',completion_text='小雨你说得对')
  await self.bot.after_response(e,r)
  self.assertEqual(r.completion_text,'')
  self.assertEqual(self.bot.store.db.execute('SELECT COUNT(*) FROM reply_reservations').fetchone()[0],0)

 async def test_group_streaming_disabled_without_public_profiles(self):
  from astrbot.core.pipeline.process_stage.method.agent_sub_stages import internal
  from astrbot.core.astr_main_agent import MainAgentBuildConfig
  self.bot.config['public_profile_enabled']=False
  self.native['provider_settings']['streaming_response']=True
  e=self.event(group=True)
  async for _ in self.bot.observe(e):pass
  e.send_typing=AsyncMock();e.stop_typing=AsyncMock();e.send=AsyncMock()
  stage=internal.InternalAgentSubStage();stage.streaming_response=True;stage.show_reasoning=False
  stage.main_agent_cfg=MainAgentBuildConfig(tool_call_timeout=60)
  stage.ctx=SimpleNamespace(plugin_manager=SimpleNamespace(context=SimpleNamespace(get_config=lambda **kw:self.native)))
  captured=[]
  async def build(**kw):captured.append(kw['config'].streaming_response);return None
  with patch.object(internal,'build_main_agent',side_effect=build),patch.object(internal,'try_capture_follow_up',return_value=None),patch.object(internal,'call_event_hook',new=AsyncMock(return_value=False)),patch.object(internal.SessionServiceManager,'should_process_llm_request',new=AsyncMock(return_value=True)):
   async for _ in stage.process(e,''):pass
  self.assertEqual(captured,[False])

if __name__=='__main__':unittest.main()
