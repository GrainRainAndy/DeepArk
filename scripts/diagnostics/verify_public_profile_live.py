"""Installed code + actual scopes, synthetic facts in temporary DB; never sends messages."""
import asyncio
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from data.plugins.astrbot_plugin_deepark_companion.main import DeeparkCompanion
from data.plugins.astrbot_plugin_deepark_companion.core import Store
from data.plugins.astrbot_plugin_deepark_companion.public_profile import PublicProfiles
from astrbot.api import sp
from astrbot.api.provider import ProviderRequest,LLMResponse
from astrbot.core.platform.astr_message_event import AstrMessageEvent
from astrbot.core.platform.astrbot_message import AstrBotMessage,MessageMember
from astrbot.core.platform.platform_metadata import PlatformMetadata
from astrbot.core.platform.message_type import MessageType
from astrbot.core.message.components import Plain

def event(text,group=False,user='1431209261'):
 m=AstrBotMessage();m.type=MessageType.GROUP_MESSAGE if group else MessageType.FRIEND_MESSAGE
 m.self_id='1934473603';m.sender=MessageMember(user,'synthetic');m.group_id='107861837' if group else '';m.session_id=m.group_id if group else user
 m.message_id='synthetic-no-send';m.message=[Plain(text)];m.message_str=text
 e=AstrMessageEvent(text,m,PlatformMetadata('aiocqhttp','synthetic','deepark'),m.session_id);e.is_at_or_wake_command=True
 return e

async def main():
 r=Path('/AstrBot/data');cfg=json.loads((r/'config/astrbot_plugin_deepark_companion_config.json').read_text());native=json.loads((r/'cmd_config.json').read_text(encoding='utf-8-sig'))
 with tempfile.TemporaryDirectory() as td:
  bot=object.__new__(DeeparkCompanion);bot.config=cfg;bot.context=SimpleNamespace(get_config=lambda _:native);bot.news_context=lambda:''
  bot.store=Store(Path(td)/'state.db',cfg);bot.public_profiles=PublicProfiles(Path(td)/'public.db')
  try:
   e=event('/deepark 公开记住 昵称=合成验证昵称')
   result=[x async for x in bot.public_profile_command(e)];assert result and e.is_stopped() and e.call_llm
   group=event('你好',True)
   assert [x async for x in bot.public_profile_command(group)]==[]
   assert group.get_extra('enable_streaming') is False
   req=ProviderRequest(system_prompt='test',contexts=[]);await bot.inject(group,req)
   assert '合成验证昵称' in req.system_prompt
   other=event('你好',True,'123456789');req2=ProviderRequest(system_prompt='test',contexts=[]);await bot.inject(other,req2)
   assert '合成验证昵称' not in req2.system_prompt
   assert await sp.session_get(group.unified_msg_origin,'provider_perf_chat_completion',None)=='deepseek/deepseek-flash'
   revoke=event('/deepark 取消公开 全部');assert [x async for x in bot.public_profile_command(revoke)]
   resp=LLMResponse(role='assistant',completion_text='合成验证昵称');await bot.after_response(group,resp)
   assert resp.completion_text=='' and group.is_stopped()
   print('PASS: installed plugin + real authorized private/group scopes; same sender recall; other sender excluded; revoked inflight reply blocked; official group model preserved. Temporary data only; no messages or LLM requests.')
  finally:bot.public_profiles.close();bot.store.close()
asyncio.run(main())
