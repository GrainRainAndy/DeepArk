import json
from pathlib import Path
import urllib.request
key=Path('/home/grainrain/astrbot/.sf-embedding-key').read_text().strip()
body={'model':'BAAI/bge-m3','input':['这是一个用于验证长期记忆向量接口的合成句子。'],'encoding_format':'float'}
req=urllib.request.Request('https://api.siliconflow.cn/v1/embeddings',data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
try:
    with urllib.request.urlopen(req,timeout=45) as r:d=json.load(r)
    print(json.dumps({'model':body['model'],'dimensions':len(d['data'][0]['embedding']),'usage':d.get('usage')}))
except Exception as exc:print(json.dumps({'error':type(exc).__name__,'status':getattr(exc,'code',None)}));raise SystemExit(1)
