"""Actual SDK + SiliconFlow + temporary FAISS; no production memory/messages."""
import asyncio,json,tempfile
from pathlib import Path
from types import SimpleNamespace
from astrbot.core.provider.sources.openai_embedding_source import OpenAIEmbeddingProvider
from astrbot.core.db.vec_db.faiss_impl.vec_db import FaissVecDB
from data.plugins.astrbot_plugin_livingmemory.core.memory_scope import resolve_memory_scope,is_event_memory_allowed
async def main():
 c=json.loads(Path('/AstrBot/data/cmd_config.json').read_text(encoding='utf-8-sig'))
 p=OpenAIEmbeddingProvider(next(p for p in c['provider'] if p['id']=='deepark-memory-sf'),{})
 mc={'access_control':{'whitelist_enabled':True,'allowed_ids':'test:FriendMessage:alice\ntest:GroupMessage:group'},'filtering_settings':{'memory_scope_mode':'session'}}
 def event(scope):return SimpleNamespace(unified_msg_origin=scope,get_sender_id=lambda:'alice',get_group_id=lambda:'group' if ':GroupMessage:' in scope else '',get_sender_name=lambda:'synthetic',get_platform_name=lambda:'test')
 private=event('test:FriendMessage:alice');group=event('test:GroupMessage:group')
 assert is_event_memory_allowed(mc,private)
 assert not is_event_memory_allowed(mc,event('test:FriendMessage:other'))
 private_scope=resolve_memory_scope(mc,private);group_scope=resolve_memory_scope(mc,group)
 assert private_scope != group_scope
 with tempfile.TemporaryDirectory(prefix='deepark-memory-') as d:
  db=FaissVecDB(doc_store_path=d+'/docs.db',index_store_path=d+'/index',embedding_provider=p)
  await db.initialize()
  try:
   await db.insert('合成测试：测试角色喜欢明日方舟的音乐',metadata={'session_id':private_scope,'persona_id':'test'},id='synthetic')
   rows=await db.retrieve('喜欢哪款游戏的音乐',metadata_filters={'session_id':private_scope})
   assert len(rows)==1
   assert not await db.retrieve('喜欢哪款游戏的音乐',metadata_filters={'session_id':group_scope})
   assert p.get_dim()==1024
   print('PASS: cloud embedding 1024D; temporary memory write/semantic recall; cross-session exclusion; unauthorized session denied')
  finally:await db.close();await p.terminate()
asyncio.run(main())
