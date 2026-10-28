"""Read-only production configuration checks in SDK; no network or message sends."""
import asyncio,json
from pathlib import Path
from types import SimpleNamespace
from astrbot.api import sp
from astrbot.core.platform.astr_message_event import AstrMessageEvent
from astrbot.core.platform.astrbot_message import AstrBotMessage,MessageMember
from astrbot.core.platform.platform_metadata import PlatformMetadata
from astrbot.core.platform.message_type import MessageType
from astrbot.core.message.components import Plain
from data.plugins.astrbot_plugin_deepark_companion.batch_bridge import BatchBridge
async def main():
 r=Path('/AstrBot/data');c=json.loads((r/'cmd_config.json').read_text(encoding='utf-8-sig'))
 def config(name):return json.loads((r/'config'/name).read_text(encoding='utf-8-sig'))
 cfg=config('astrbot_plugin_deepark_companion_config.json');lm=config('astrbot_plugin_livingmemory_config.json');pc=config('astrbot_plugin_proactive_chat_config.json')
 bridge=BatchBridge(SimpleNamespace(config=cfg,context=SimpleNamespace(get_config=lambda scope:c)))
 for scope in cfg['batching_sessions']:
  platform,typ,user=scope.split(':');assert typ=='FriendMessage'
  assert platform in {p['id'] for p in c['platform'] if p.get('enable')}
  assert scope in c['platform_settings']['id_whitelist']
  assert scope in lm['access_control']['allowed_ids'].splitlines()
  assert scope in pc['friend_settings']['session_list']
  msg=AstrBotMessage();msg.type=MessageType.FRIEND_MESSAGE;msg.message_id='synthetic-verification';msg.sender=MessageMember(user,'synthetic');msg.self_id='synthetic-bot';msg.group=None;msg.session_id=user;msg.message=[Plain('synthetic')];msg.message_str='synthetic'
  e=AstrMessageEvent('synthetic',msg,PlatformMetadata('aiocqhttp','synthetic',platform),user);e.is_at_or_wake_command=True
  assert e.unified_msg_origin==scope
  assert await bridge.eligible(e)
  model=await sp.session_get(scope,'provider_perf_chat_completion',None)
  assert model=='deepseek/deepseek-flash',model
  print('PASS: actual private UMO matches batching/native/memory/proactive scopes; official model selection preserved')
 await bridge.close()
asyncio.run(main())
