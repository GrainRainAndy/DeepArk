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
persona=Path('/tmp/deepark-persona.txt').read_text()
cases=[
    ('本人偏好','当前用户u1。可信程序提供的本群本人记忆：我喜欢阿米娅；不要剧透新剧情。','今天有什么轻松话题能聊？'),
    ('区分成员','当前用户u2。近期群聊：u1说“我喜欢阿米娅”。没有u2的个人偏好记忆。','你还记得我最喜欢哪个干员吗？'),
]
for label,context,prompt in cases:
    payload={'model':p['model'],'messages':[{'role':'system','content':persona+'\n'+context},{'role':'user','content':prompt}],'max_tokens':1000,'stream':False}
    req=urllib.request.Request(base+'/chat/completions',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    started=time.monotonic()
    try:
        with urllib.request.urlopen(req,timeout=60) as r:data=json.load(r)
        print(json.dumps({'case':label,'reply':data['choices'][0]['message'].get('content'),'seconds':round(time.monotonic()-started,2),'usage':data.get('usage')},ensure_ascii=False),flush=True)
    except Exception as exc:print(json.dumps({'case':label,'error':type(exc).__name__}),flush=True)
