"""Probe production decision provider through real SDK; synthetic only."""
import asyncio
import json
from pathlib import Path
import sys
import time
from astrbot.core.provider.sources.openai_source import ProviderOpenAIOfficial
sys.path.insert(0,'/AstrBot/data/plugins/astrbot_plugin_deepark_companion')
from social import PROMPT,choose

async def main():
    c=json.loads(Path('/AstrBot/data/cmd_config.json').read_text(encoding='utf-8-sig'))
    p=next(x for x in c['provider'] if x['id']=='deepark-decision')
    source=next(x for x in c['provider_sources'] if x['id']==p['provider_source_id'])
    model=ProviderOpenAIOfficial({**source,**p},c['provider_settings'])
    try:
        data={'allowed_actions':['followup','skip'],'recent_messages':[{'subject':'@bot','text':'阿米娅这个皮肤挺好看'},{'subject':'u1','text':'为什么这么说？'}]}
        started=time.monotonic()
        r=await asyncio.wait_for(model.text_chat(prompt=json.dumps(data,ensure_ascii=False),system_prompt=PROMPT,contexts=[],request_max_retries=1),20)
        print(json.dumps({'decision':choose(r.completion_text,['followup']),'seconds':round(time.monotonic()-started,2),'thinking_disabled_configured':p['custom_extra_body']['thinking']['type']=='disabled'},ensure_ascii=False))
    finally:await model.terminate()

asyncio.run(main())
