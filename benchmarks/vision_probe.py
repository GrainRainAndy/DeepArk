"""Synthetic vision request from AstrBot container. No user pictures or config writes."""
import base64,json,struct,time,urllib.request,urllib.error,urllib.parse,zlib
from pathlib import Path
c=json.loads(Path('/AstrBot/data/cmd_config.json').read_text(encoding='utf-8-sig'))
p=next(x for x in c['provider'] if x['id']=='deepark-vision')
s=next(x for x in c['provider_sources'] if x['id']==p['provider_source_id'])
base=s['api_base'].rstrip('/');assert urllib.parse.urlsplit(base).hostname=='llmapi.paratera.com'
key=s['key'];key=key[0] if isinstance(key,list) else key
# White 320x160 canvas: red square left, blue circle right. Prompt does not reveal content.
def chunk(name,data):return struct.pack('!I',len(data))+name+data+struct.pack('!I',zlib.crc32(name+data)&0xffffffff)
raw=bytearray()
for y in range(160):
 raw.append(0)
 for x in range(320):
  color=(255,255,255)
  if 25<=x<115 and 35<=y<125:color=(240,30,30)
  if (x-240)**2+(y-80)**2<=45**2:color=(30,70,240)
  raw.extend(color)
png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',320,160,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')
body={'model':p['model'],'messages':[{'role':'user','content':[{'type':'text','text':'请识别图片中左边和右边的图形及颜色，用一句中文回答。'},{'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(png).decode()}}]}],'max_tokens':1024,'stream':False,**p.get('custom_extra_body',{})}
req=urllib.request.Request(base+'/chat/completions',data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
print(json.dumps({'provider':p['id'],'model':p['model'],'endpoint':base,'test':'synthetic image recognition'},ensure_ascii=False),flush=True)
t=time.monotonic()
try:
 with urllib.request.urlopen(req,timeout=55) as resp:
  status=resp.status;data=json.load(resp)
 choice=data.get('choices',[{}])[0];msg=choice.get('message',{});answer=msg.get('content') or ''
 print(json.dumps({'http_status':status,'elapsed_seconds':round(time.monotonic()-t,3),'answer':answer[:1500],'finish_reason':choice.get('finish_reason'),'usage':data.get('usage',{}),'has_reasoning':bool(msg.get('reasoning_content'))},ensure_ascii=False),flush=True)
except urllib.error.HTTPError as exc:
 print(json.dumps({'http_status':exc.code,'elapsed_seconds':round(time.monotonic()-t,3),'error_type':'HTTPError'}),flush=True)
except Exception as exc:
 print(json.dumps({'elapsed_seconds':round(time.monotonic()-t,3),'error_type':type(exc).__name__}),flush=True)
