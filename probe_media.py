"""Server-only synthetic media probe. Never emits credentials or HTTP bodies on error."""
import base64
import json
import pathlib
import struct
import time
import urllib.request
import urllib.parse
import zlib

config=json.loads(pathlib.Path('/home/grainrain/astrbot/data/cmd_config.json').read_text(encoding='utf-8-sig'))
pid=config['agent_runner']['config']['model']['provider_id']
provider=next(p for p in config['provider'] if p['id']==pid)
source=next(s for s in config['provider_sources'] if s['id']==provider['provider_source_id'])
base=source['api_base'].rstrip('/')
assert urllib.parse.urlsplit(base).hostname=='llmapi.paratera.com'
key=source['key']; key=key[0] if isinstance(key,list) else key
def chunk(kind,data):
    return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
pixels=b''.join(b'\0'+b''.join(bytes((255,0,0) if x<48 else (0,0,255)) for x in range(96)) for y in range(64))
png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!IIBBBBB',96,64,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(pixels))+chunk(b'IEND',b'')
body={'model':'GLM-4.6V','messages':[{'role':'user','content':[{'type':'text','text':'描述图中左右两半分别是什么颜色，只回答颜色。'},{'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(png).decode()}}]}],'max_tokens':512,'stream':False}
start=time.monotonic()
try:
    req=urllib.request.Request(base+'/chat/completions',data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=60) as response:data=json.load(response)
    print(json.dumps({'model':body['model'],'seconds':round(time.monotonic()-start,2),'reply':data['choices'][0]['message'].get('content'),'usage':data.get('usage')},ensure_ascii=False))
except Exception as exc:
    print(json.dumps({'model':body['model'],'error':type(exc).__name__,'status':getattr(exc,'code',None)}))
