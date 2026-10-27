"""Repair stale platform prefix for an already-authorized QQ user; no new identity."""
import datetime,json,os,shutil,sqlite3,subprocess
from pathlib import Path
r=Path('/home/grainrain/astrbot/data');os.umask(0o077)
c=json.loads((r/'cmd_config.json').read_text(encoding='utf-8-sig'))
with sqlite3.connect('file:'+str(r/'data_v4.db')+'?mode=ro',uri=True) as d:
 active=[s for (s,) in d.execute('SELECT scope_id FROM preferences WHERE key=?',('provider_perf_chat_completion',)) if ':FriendMessage:' in s]
platform_ids={p['id'] for p in c['platform'] if p.get('enable',True)}
mapping={}
for old in c['platform_settings']['id_whitelist']:
 if ':FriendMessage:' not in old:continue
 matches=[s for s in active if s.rsplit(':',1)[-1]==old.rsplit(':',1)[-1] and s.split(':',1)[0] in platform_ids]
 assert len(matches)==1,'Cannot unambiguously resolve authorized private session'
 if old!=matches[0]:mapping[old]=matches[0]
assert mapping,'No stale sessions'
b=Path('/home/grainrain/astrbot-backups')/('session-prefix-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));b.mkdir(mode=0o700)
paths=[r/'cmd_config.json']+[r/'config'/n for n in ['astrbot_plugin_deepark_companion_config.json','astrbot_plugin_livingmemory_config.json','astrbot_plugin_proactive_chat_config.json']]
def repair(x):
 if isinstance(x,dict):return {k:repair(v) for k,v in x.items()}
 if isinstance(x,list):return [repair(v) for v in x]
 if isinstance(x,str):return '\n'.join(mapping.get(line,line) for line in x.split('\n'))
 return x
subprocess.run(['docker','stop','astrbot'],check=True,stdout=subprocess.DEVNULL)
try:
 for p in paths:
  shutil.copy2(p,b/p.name);x=json.loads(p.read_text(encoding='utf-8-sig'));t=p.with_suffix('.prefix-tmp');t.write_text(json.dumps(repair(x),ensure_ascii=False,indent=2)+'\n');t.chmod(0o600);os.replace(t,p)
 print('Repaired platform prefix for '+str(len(mapping))+' existing private session; backup '+str(b),flush=True)
except BaseException:
 for p in paths:
  if (b/p.name).exists():shutil.copy2(b/p.name,p)
 raise
finally:subprocess.run(['docker','start','astrbot'],check=True,stdout=subprocess.DEVNULL)
