"""Inspect only public model metadata for advertised voice generation support."""
import json
from pathlib import Path
import urllib.request
import urllib.parse

config=json.loads(Path('/home/grainrain/astrbot/data/cmd_config.json').read_text(encoding='utf-8-sig'))
pid=config['agent_runner']['config']['model']['provider_id']
p=next(p for p in config['provider'] if p['id']==pid)
s=next(s for s in config['provider_sources'] if s['id']==p['provider_source_id'])
base=s['api_base'].rstrip('/')
assert urllib.parse.urlsplit(base).hostname=='llmapi.paratera.com'
key=s['key'];key=key[0] if isinstance(key,list) else key
req=urllib.request.Request(base+'/models',headers={'Authorization':'Bearer '+key})
with urllib.request.urlopen(req,timeout=30) as r:data=json.load(r)
items=data.get('data',[])
candidate=[]
for item in items:
    public={k:item[k] for k in ('id','modalities','output_modalities','type') if k in item}
    if any(x in json.dumps(public).lower() for x in ('tts','speech','audio','voice','omni','asr')):candidate.append(public)
print(json.dumps({'model_count':len(items),'audio_candidates':candidate},ensure_ascii=False))
