"""Two synthetic group scenarios; no QQ dispatch, secrets remain on server."""
import json
from pathlib import Path
import time
import urllib.request
import urllib.parse

config=json.loads(Path('/home/grainrain/astrbot/data/cmd_config.json').read_text(encoding='utf-8-sig'))
pid=config['agent_runner']['config']['model']['provider_id']
p=next(p for p in config['provider'] if p['id']==pid)
s=next(s for s in config['provider_sources'] if s['id']==p['provider_source_id'])
base=s['api_base'].rstrip('/')
assert urllib.parse.urlsplit(base).hostname=='llmapi.paratera.com'
key=s['key'];key=key[0] if isinstance(key,list) else key
persona=(Path(__file__).resolve().parents[2] / 'resources/persona.txt').read_text()
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from plugins.deepark_companion.social import PROMPT,choose
cases=[
 ('追问','我觉得阿米娅这个皮肤挺好看','为什么这么说？',['followup']),
 ('附和','我觉得阿米娅这个皮肤挺好看','哈哈',['followup']),
 ('别人互聊','我觉得阿米娅这个皮肤挺好看','小王你晚上来不来开黑',['followup']),
 ('兴趣插话','此前机器人未参与','这次明日方舟音乐你们最喜欢哪首？',['interject']),
]
for label,previous,current,actions in cases:
 payload={'allowed_actions':actions+['skip'],'recent_messages':[{'subject':'@bot','text':previous},{'subject':'u1','text':current}],'hints':{}}
 body={'model':p['model'],'messages':[{'role':'system','content':PROMPT},{'role':'user','content':json.dumps(payload,ensure_ascii=False)}],'max_tokens':700,'stream':False,'thinking':{'type':'disabled'}}
 req=urllib.request.Request(base+'/chat/completions',data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
 started=time.monotonic()
 try:
  with urllib.request.urlopen(req,timeout=30) as r:data=json.load(r)
  raw=data['choices'][0]['message'].get('content') or ''
  print(json.dumps({'case':label,'decision':choose(raw,actions),'raw':raw,'seconds':round(time.monotonic()-started,2),'usage':data.get('usage')},ensure_ascii=False),flush=True)
 except Exception as exc:print(json.dumps({'case':label,'error':type(exc).__name__}),flush=True)
