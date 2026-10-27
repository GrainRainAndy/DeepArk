"""Deploy short-message batching with an explicit, non-history-destructive rollback."""
import datetime,hashlib,json,os,shutil,sqlite3,subprocess
from pathlib import Path
os.umask(0o077)
r=Path('/home/grainrain/astrbot/data')
b=Path('/home/grainrain/astrbot-backups')/('batching-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));b.mkdir(mode=0o700)
target=r/'plugins/astrbot_plugin_deepark_companion';cp=r/'config/astrbot_plugin_deepark_companion_config.json'
subprocess.run(['docker','stop','astrbot'],check=True,stdout=subprocess.DEVNULL)
def write(p,c):
 t=p.with_suffix('.batch-tmp');t.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n');t.chmod(0o600);os.replace(t,p)
try:
 shutil.copytree(target,b/'plugin');shutil.copy2(cp,b/cp.name);shutil.copy2(r/'cmd_config.json',b/'cmd_config.json')
 with sqlite3.connect(r/'data_v4.db') as db,sqlite3.connect(b/'data_v4.db') as backup:db.backup(backup)
 c=json.loads((r/'cmd_config.json').read_text(encoding='utf-8-sig'))
 sessions=[x for x in c['platform_settings']['id_whitelist'] if ':FriendMessage:' in x]
 assert sessions,'No authorized private sessions'
 conf=json.loads(cp.read_text(encoding='utf-8-sig'));conf.update(batching_enabled=True,batching_sessions=sessions,batch_quiet_seconds=1.5,batch_max_seconds=4.0)
 c['platform_settings']['segmented_reply'].update(interval_method='random',interval='0.4,0.8',regex=r'.*?(?:\r?\n+|[。？！~…]+)|.+$')
 for source in Path('/tmp/deepark-batch-tests/plugin').iterdir():
  if source.is_file() and source.suffix in ('.py','.json','.yaml'):shutil.copy2(source,target/source.name)
 write(cp,conf);write(r/'cmd_config.json',c)
 rollback=b/'rollback.sh'
 rollback.write_text('#!/bin/sh\nset -eu\ndocker stop astrbot >/dev/null\ntrap \'docker start astrbot >/dev/null\' EXIT\ncp -a '+str(b/'plugin')+'/. '+str(target)+'/\ncp '+str(b/cp.name)+' '+str(cp)+'\ncp '+str(b/'cmd_config.json')+' '+str(r/'cmd_config.json')+'\n')
 rollback.chmod(0o700)
 print(json.dumps({'backup':str(b),'rollback':str(rollback),'private_session_count':len(sessions),'version':'v0.4.0','code_sha256':hashlib.sha256((target/'batch_bridge.py').read_bytes()).hexdigest()}),flush=True)
except BaseException:
 if (b/'plugin').exists():shutil.copytree(b/'plugin',target,dirs_exist_ok=True)
 if (b/cp.name).exists():shutil.copy2(b/cp.name,cp)
 if (b/'cmd_config.json').exists():shutil.copy2(b/'cmd_config.json',r/'cmd_config.json')
 raise
finally:subprocess.run(['docker','start','astrbot'],check=True,stdout=subprocess.DEVNULL)
