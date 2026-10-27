"""Server-local administration only. Credentials and tokens never printed."""
import base64
import hashlib
import hmac
import json
from pathlib import Path
import time
import urllib.request
import urllib.error

ROOT=Path('/home/grainrain/astrbot/data')
def config():return json.loads((ROOT/'cmd_config.json').read_text(encoding='utf-8-sig'))
def b64(data):return base64.urlsafe_b64encode(data).rstrip(b'=')
def call(method,path,body=None,timeout=120):
    cfg=config()['dashboard']
    head=b64(b'{"alg":"HS256","typ":"JWT"}')
    payload=b64(json.dumps({'username':cfg['username'],'exp':int(time.time())+900}).encode())
    unsigned=head+b'.'+payload
    token=(unsigned+b'.'+b64(hmac.new(cfg['jwt_secret'].encode(),unsigned,hashlib.sha256).digest())).decode()
    req=urllib.request.Request('http://127.0.0.1:6185/api/v1'+path,method=method,data=json.dumps(body).encode() if body is not None else None,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=timeout) as response:result=json.load(response)
    if result.get('status')=='error':raise RuntimeError('API rejected '+path)
    return result

if __name__=='__main__':
    import sys
    if sys.argv[1] in ('install','install_urls'):
        specs=[('lxfight/astrbot_plugin_livingmemory','astrbot_plugin_livingmemory'),('anka/meme_manager','meme_manager'),('Zhalslar/astrbot_plugin_qzone','astrbot_plugin_qzone'),('Zhalslar/astrbot_plugin_qqprofile','astrbot_plugin_qqprofile'),('DBJD-CR/astrbot_plugin_proactive_chat','astrbot_plugin_proactive_chat')]
        existing={p['name'] for p in call('GET','/plugins').get('data',[])}
        repos=['lxfight-s-Astrbot-Plugins/astrbot_plugin_livingmemory','anka-afk/astrbot_plugin_meme_manager','Zhalslar/astrbot_plugin_qzone','Zhalslar/astrbot_plugin_qqprofile','Pancakes-Labs/astrbot_plugin_proactive_chat']
        for (market,name),repo in zip(specs,repos):
            print('Installing '+name,flush=True)
            try:
                if name not in existing:
                    if sys.argv[1]=='install_urls':
                        branch='master' if 'livingmemory' in name else 'main'
                        call('POST','/plugins/install/url',{'url':'https://github.com/'+repo,'download_url':'https://codeload.github.com/'+repo+'/zip/refs/heads/'+branch},timeout=600)
                    else:call('POST','/plugins/install/github',{'install_method':'market','market_plugin_id':market},timeout=600)
                call('PATCH','/plugins/enabled',{'plugin_id':name,'enabled':False})
                print(name+': installed, disabled pending configuration',flush=True)
            except Exception as exc:print(name+': '+type(exc).__name__,flush=True)
    else:
        for p in call('GET','/plugins').get('data',[]):print(json.dumps({k:p.get(k) for k in ('name','version','activated','author')},ensure_ascii=False))
