"""Real SDK events, temporary storage, fake preference boundary; no QQ or model calls."""
import asyncio
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch, AsyncMock
from plugin.main import DeeparkCompanion
from plugin.core import Store
from plugin.public_profile import PublicProfiles, identity
from astrbot.api.provider import ProviderRequest, LLMResponse
from astrbot.core.platform.astr_message_event import AstrMessageEvent
from astrbot.core.platform.astrbot_message import AstrBotMessage, MessageMember
from astrbot.core.platform.platform_metadata import PlatformMetadata
from astrbot.core.platform.message_type import MessageType
from astrbot.core.message.components import Plain, Reply

class ProfileSDKTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.bot=object.__new__(DeeparkCompanion)
        self.private='deepark:FriendMessage:12345';self.group='deepark:GroupMessage:45678'
        self.bot.config={'enabled':True,'public_profile_enabled':True,'public_profile_sessions':[self.private,self.group],'allow_groups':[self.group],'memory_backend':'livingmemory'}
        self.native={'platform_settings':{'enable_id_white_list':True,'id_whitelist':[self.private,self.group]},'plugin_set':['*'],'provider_settings':{'enable':True}}
        self.bot.context=SimpleNamespace(get_config=lambda _:self.native)
        self.bot.store=Store(Path(self.tmp.name)/'state.db',self.bot.config);self.addCleanup(self.bot.store.close)
        self.bot.public_profiles=PublicProfiles(Path(self.tmp.name)/'public.db');self.addCleanup(self.bot.public_profiles.close)
        self.bot.news_context=lambda:''
        self.preferences={}
        async def prefs(**kw):return self.preferences.get(kw['key'],kw.get('default'))
        self.patcher=patch('plugin.main.sp.get_async',side_effect=prefs);self.patcher.start();self.addCleanup(self.patcher.stop)

    def event(self,text='你好',group=False,user='12345',bot='99999',instance='deepark'):
        m=AstrBotMessage();m.type=MessageType.GROUP_MESSAGE if group else MessageType.FRIEND_MESSAGE
        m.self_id=bot;m.sender=MessageMember(user,'相同昵称');m.group_id='45678' if group else '';m.session_id=m.group_id if group else user
        m.message_id='synthetic';m.message=[Plain(text)];m.message_str=text
        e=AstrMessageEvent(text,m,PlatformMetadata('aiocqhttp','synthetic',instance),m.session_id);e.is_at_or_wake_command=True
        return e

    async def command(self,event):
        self.assertTrue(hasattr(self.bot,'public_profile_command'),'SDK command hook not implemented')
        return [x async for x in self.bot.public_profile_command(event)]

    async def test_explicit_private_consent_recalled_in_group(self):
        e=self.event('/deepark 公开记住 喜欢的干员=阿米娅')
        self.assertTrue(await self.command(e));self.assertTrue(e.is_stopped())
        req=ProviderRequest(system_prompt='persona',contexts=[])
        await self.bot.inject(self.event(group=True),req)
        self.assertIn('阿米娅',req.system_prompt)
        self.assertIn('12345',req.system_prompt)
        other=ProviderRequest(system_prompt='persona',contexts=[])
        await self.bot.inject(self.event(group=True,user='54321'),other)
        self.assertNotIn('阿米娅',other.system_prompt)

    async def test_group_consent_recalled_in_private(self):
        await self.command(self.event('/deepark 公开记住 昵称=小雨',group=True))
        req=ProviderRequest(system_prompt='persona',contexts=[])
        await self.bot.inject(self.event(),req)
        self.assertIn('小雨',req.system_prompt)

    async def test_plain_chat_cannot_implicitly_consent(self):
        self.assertEqual(await self.command(self.event('我喜欢阿米娅')),[])
        req=ProviderRequest(system_prompt='persona',contexts=[])
        await self.bot.inject(self.event(group=True),req)
        self.assertNotIn('阿米娅',req.system_prompt)

    async def test_quote_cannot_grant_consent(self):
        e=self.event('/deepark 公开记住 昵称=小雨')
        e.message_obj.message.insert(0,Reply(id='quoted',sender_id='54321'))
        await self.command(e)
        self.assertEqual(self.bot.public_profiles.snapshot(identity(self.private,'99999','12345'))[1],{})

    async def test_unauthorized_scope_cannot_write_or_read(self):
        await self.command(self.event('/deepark 公开记住 昵称=小雨'))
        self.bot.config['public_profile_sessions']=[self.private]
        self.assertEqual(await self.command(self.event('/deepark 公开记住 昵称=坏值',group=True)),[])
        req=ProviderRequest(system_prompt='persona',contexts=[])
        await self.bot.inject(self.event(group=True),req)
        self.assertNotIn('小雨',req.system_prompt)

    async def test_disabled_session_and_native_whitelist_block(self):
        for key,value in [('session_service_config',{'session_enabled':False}),('session_plugin_config',{self.private:{'disabled_plugins':['deepark_companion']}})]:
            self.preferences={key:value}
            self.assertEqual(await self.command(self.event('/deepark 公开记住 昵称=小雨')),[])
        self.preferences={};self.native['platform_settings']['id_whitelist']=[self.group]
        self.assertEqual(await self.command(self.event('/deepark 公开记住 昵称=小雨')),[])
        self.assertEqual(self.bot.public_profiles.snapshot(identity(self.private,'99999','12345'))[1],{})

    async def test_revoke_blocks_inflight_reply_before_meme_hook(self):
        await self.command(self.event('/deepark 公开记住 昵称=小雨'))
        e=self.event(group=True);req=ProviderRequest(system_prompt='persona',contexts=[])
        await self.bot.inject(e,req)
        await self.command(self.event('/deepark 取消公开 全部'))
        response=LLMResponse(role='assistant',completion_text='小雨来啦')
        await self.bot.after_response(e,response)
        self.assertTrue(e.is_stopped());self.assertEqual(response.completion_text,'')
        req2=ProviderRequest(system_prompt='persona',contexts=[])
        await self.bot.inject(self.event(),req2);self.assertNotIn('小雨',req2.system_prompt)

    async def test_disabling_profile_during_generation_blocks_reply(self):
        await self.command(self.event('/deepark 公开记住 昵称=小雨'))
        e=self.event();await self.bot.inject(e,ProviderRequest(system_prompt='persona',contexts=[]))
        self.bot.config['public_profile_enabled']=False
        response=LLMResponse(role='assistant',completion_text='小雨')
        await self.bot.after_response(e,response)
        self.assertEqual(response.completion_text,'')

    async def test_revoke_during_output_safety_check_blocks_reply(self):
        await self.command(self.event('/deepark 公开记住 昵称=小雨'))
        e=self.event(group=True);await self.bot.inject(e,ProviderRequest(system_prompt='persona',contexts=[]))
        started,release=asyncio.Event(),asyncio.Event()
        async def check(*args):
            started.set();await release.wait();return True
        self.bot.output_allowed=check
        response=LLMResponse(role='assistant',completion_text='小雨来啦')
        task=asyncio.create_task(self.bot.after_response(e,response))
        await asyncio.wait_for(started.wait(),2)
        await self.command(self.event('/deepark 取消公开 全部'))
        release.set();await task
        self.assertEqual(response.completion_text,'');self.assertTrue(e.is_stopped())

    async def test_streaming_disabled_before_native_agent_build(self):
        from astrbot.core.pipeline.process_stage.method.agent_sub_stages import internal
        from astrbot.core.astr_main_agent import MainAgentBuildConfig
        await self.command(self.event('/deepark 公开记住 昵称=小雨'))
        e=self.event(group=True)
        await self.command(e)  # ALL listener runs before native agent processing.
        e.send_typing=AsyncMock();e.stop_typing=AsyncMock();e.send=AsyncMock()
        stage=internal.InternalAgentSubStage();stage.streaming_response=True;stage.show_reasoning=False
        stage.main_agent_cfg=MainAgentBuildConfig(tool_call_timeout=60)
        stage.ctx=SimpleNamespace(plugin_manager=SimpleNamespace(context=SimpleNamespace(get_config=lambda **kw:self.native)))
        captured=[]
        async def build(**kw):captured.append(kw['config'].streaming_response);return None
        with patch.object(internal,'build_main_agent',side_effect=build), patch.object(internal,'try_capture_follow_up',return_value=None), patch.object(internal,'call_event_hook',new=AsyncMock(return_value=False)), patch.object(internal.SessionServiceManager,'should_process_llm_request',new=AsyncMock(return_value=True)):
            async for _ in stage.process(e,''):pass
        self.assertEqual(captured,[False])

    async def test_public_command_disables_default_llm(self):
        e=self.event('/deepark 公开记忆')
        await self.command(e)
        # SDK flag is inverted: True prohibits the native default LLM request.
        self.assertTrue(e.call_llm)

if __name__=='__main__':unittest.main()
