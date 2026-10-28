"""Bounded synthetic ASR probe; reuse secrets only on the server."""
import json
import pathlib
import time
import urllib.request
import urllib.parse
import uuid

config=json.loads(pathlib.Path('/home/grainrain/astrbot/data/cmd_config.json').read_text(encoding='utf-8-sig'))
pid=config['agent_runner']['config']['model']['provider_id']
provider=next(p for p in config['provider'] if p['id']==pid)
source=next(s for s in config['provider_sources'] if s['id']==provider['provider_source_id'])
base=source['api_base'].rstrip('/')
assert urllib.parse.urlsplit(base).hostname=='llmapi.paratera.com'
key=source['key'];key=key[0] if isinstance(key,list) else key
boundary=uuid.uuid4().hex
audio=pathlib.Path('/tmp/deepark-synthetic.wav').read_bytes()
body=(f'--{boundary}\r\nContent-Disposition: form-data; name="model"\r\n\r\nGLM-ASR-2512\r\n--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="synthetic.wav"\r\nContent-Type: audio/wav\r\n\r\n'.encode()+audio+f'\r\n--{boundary}--\r\n'.encode())
start=time.monotonic()
try:
    req=urllib.request.Request(base+'/audio/transcriptions',data=body,headers={'Authorization':'Bearer '+key,'Content-Type':'multipart/form-data; boundary='+boundary})
    with urllib.request.urlopen(req,timeout=60) as response:data=json.load(response)
    print(json.dumps({'model':'GLM-ASR-2512','seconds':round(time.monotonic()-start,2),'text':data.get('text'),'usage':data.get('usage')},ensure_ascii=False))
except Exception as exc:
    detail=''
    if getattr(exc,'code',None):
        try:
            data=json.loads(exc.read(4096))
            error=data.get('error',{})
            detail=str(error.get('message','') if isinstance(error,dict) else error).replace(key,'[REDACTED]')[:400]
        except Exception:pass
    print(json.dumps({'model':'GLM-ASR-2512','error':type(exc).__name__,'status':getattr(exc,'code',None),'detail':detail},ensure_ascii=False))
