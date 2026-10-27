"""Deploy reviewed participation changes; no messages and no provider/whitelist changes."""
import datetime,json,os,shutil,sqlite3,subprocess
from pathlib import Path
os.umask(0o077)
r=Path('/home/grainrain/astrbot/data');target=r/'plugins/astrbot_plugin_deepark_companion';cfgpath=r/'config/astrbot_plugin_deepark_companion_config.json'
src=Path('/tmp/deepark-participation-tests/plugin')
files=('main.py','core.py','social.py','relevance.py','_conf_schema.json','metadata.yaml')
for name in files:assert (src/name).is_file()
b=Path('/home/grainrain/astrbot-backups')/('participation-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));b.mkdir(mode=0o700)
subprocess.run(['docker','stop','astrbot'],check=True,stdout=subprocess.DEVNULL)
ready=False
try:
 shutil.copytree(target,b/'plugin');shutil.copy2(cfgpath,b/cfgpath.name)
 for p in (r/'cmd_config.json',r/'config/astrbot_plugin_livingmemory_config.json',r/'config/astrbot_plugin_proactive_chat_config.json'):shutil.copy2(p,b/p.name)
 state=r/'plugin_data/deepark_companion'
 if state.exists():shutil.copytree(state,b/'companion-state')
 with sqlite3.connect(r/'data_v4.db') as source,sqlite3.connect(b/'data_v4.db') as dest:source.backup(dest)
 ready=True
 cfg=json.loads(cfgpath.read_text(encoding='utf-8-sig'))
 assert cfg['allow_groups']==['deepark:GroupMessage:107861837']
 cfg.update(proactive_enabled=True,dry_run=False,group_reply_hourly_limit=300,participation_probe_hourly_limit=300,
  group_collect_seconds=1.2,followup_window_seconds=180,followup_burst_limit=12,
  interject_daily_limit=-1,idle_daily_limit=0,active_start_hour=9,active_end_hour=4,
  bot_quiet_seconds=60,unsolicited_gap_seconds=120)
 for name in files:shutil.copy2(src/name,target/name)
 temp=cfgpath.with_suffix('.participation-tmp');temp.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n');os.replace(temp,cfgpath)
 rollback=b/'rollback.sh';rollback.write_text('#!/bin/sh\nset -eu\ndocker stop astrbot >/dev/null\ntrap \'docker start astrbot >/dev/null\' EXIT\ncp -a '+str(b/'plugin')+'/. '+str(target)+'/\ninstall -m 600 '+str(b/cfgpath.name)+' '+str(cfgpath)+'\n');rollback.chmod(0o700)
 print('Backup: '+str(b),flush=True)
except BaseException:
 if ready:shutil.copytree(b/'plugin',target,dirs_exist_ok=True);shutil.copy2(b/cfgpath.name,cfgpath)
 raise
finally:subprocess.run(['docker','start','astrbot'],check=True,stdout=subprocess.DEVNULL)
