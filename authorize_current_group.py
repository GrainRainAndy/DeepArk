"""Authorize the confirmed group; no outbound test messages."""
import datetime,json,os,shutil,sqlite3,subprocess
from pathlib import Path
os.umask(0o077)
r=Path('/home/grainrain/astrbot/data');scope='deepark:GroupMessage:107861837'
paths=[r/'cmd_config.json',r/'config/astrbot_plugin_deepark_companion_config.json',r/'config/astrbot_plugin_livingmemory_config.json']
b=Path('/home/grainrain/astrbot-backups')/('group-access-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));b.mkdir(mode=0o700)
subprocess.run(['docker','stop','astrbot'],check=True,stdout=subprocess.DEVNULL)
try:
 for p in paths:shutil.copy2(p,b/p.name)
 with sqlite3.connect(r/'data_v4.db') as src,sqlite3.connect(b/'data_v4.db') as dst:src.backup(dst)
 c,p,m=[json.loads(x.read_text(encoding='utf-8-sig')) for x in paths]
 assert any(x.get('id')=='deepseek/deepseek-flash' for x in c['provider'])
 w=c['platform_settings']['id_whitelist']
 if scope not in w:w.append(scope)
 c['platform_settings']['enable_id_white_list']=True
 if scope not in p['allow_groups']:p['allow_groups'].append(scope)
 p.update(dry_run=False,followup_enabled=True,decision_provider_id='deepseek/deepseek-flash')
 a=m['access_control'];ids=a['allowed_ids'].splitlines()
 if scope not in ids:ids.append(scope)
 a['allowed_ids']='\n'.join(ids);a['whitelist_enabled']=True
 for path,data in zip(paths,[c,p,m]):
  tmp=path.with_suffix('.group-tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');os.replace(tmp,path)
 with sqlite3.connect(r/'data_v4.db') as d:
  d.execute('INSERT INTO preferences (created_at,updated_at,scope,scope_id,key,value) VALUES (CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,?,?,?,?) ON CONFLICT(scope,scope_id,key) DO UPDATE SET value=excluded.value,updated_at=CURRENT_TIMESTAMP',('umo',scope,'provider_perf_chat_completion',json.dumps({'val':'deepseek/deepseek-flash'})))
 print('Backup: '+str(b))
except BaseException:
 for path in paths:
  if (b/path.name).exists():shutil.copy2(b/path.name,path)
 raise
finally:subprocess.run(['docker','start','astrbot'],check=True,stdout=subprocess.DEVNULL)
