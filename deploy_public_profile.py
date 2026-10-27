"""Deploy reviewed companion files; preserve all session and upstream memory settings."""
import datetime
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess

os.umask(0o077)
r=Path('/home/grainrain/astrbot/data')
target=r/'plugins/astrbot_plugin_deepark_companion'
config=r/'config/astrbot_plugin_deepark_companion_config.json'
source=Path('/tmp/deepark-profile-tests/plugin')
scopes=['deepark:FriendMessage:1431209261','deepark:GroupMessage:107861837']
c=json.loads((r/'cmd_config.json').read_text(encoding='utf-8-sig'))
lm=json.loads((r/'config/astrbot_plugin_livingmemory_config.json').read_text(encoding='utf-8-sig'))
assert lm['filtering_settings']['memory_scope_mode']=='session'
assert all(s in c['platform_settings']['id_whitelist'] and s in lm['access_control']['allowed_ids'].splitlines() for s in scopes)
assert (source/'public_profile.py').exists()
b=Path('/home/grainrain/astrbot-backups')/('public-profile-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
b.mkdir(mode=0o700)
subprocess.run(['docker','stop','astrbot'],check=True,stdout=subprocess.DEVNULL)
ready=False
try:
 shutil.copytree(target,b/'plugin')
 shutil.copy2(config,b/config.name)
 shutil.copy2(r/'cmd_config.json',b/'cmd_config.json')
 shutil.copy2(r/'config/astrbot_plugin_livingmemory_config.json',b/'astrbot_plugin_livingmemory_config.json')
 state=r/'plugin_data/deepark_companion'
 if state.exists():shutil.copytree(state,b/'companion-state')
 with sqlite3.connect(r/'data_v4.db') as src,sqlite3.connect(b/'data_v4.db') as dst:src.backup(dst)
 ready=True
 for name in ('main.py','public_profile.py','_conf_schema.json','metadata.yaml'):
  shutil.copy2(source/name,target/name)
 cfg=json.loads(config.read_text(encoding='utf-8-sig'))
 cfg.update(public_profile_enabled=True,public_profile_sessions=scopes)
 temp=config.with_suffix('.profile-tmp');temp.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n');os.replace(temp,config)
 rollback=b/'rollback.sh'
 rollback.write_text('#!/bin/sh\nset -eu\ndocker stop astrbot >/dev/null\ntrap \'docker start astrbot >/dev/null\' EXIT\ncp -a '+str(b/'plugin')+'/. '+str(target)+'/\ninstall -m 600 '+str(b/config.name)+' '+str(config)+'\n')
 rollback.chmod(0o700)
 print('Backup: '+str(b),flush=True)
except BaseException:
 if ready:
  shutil.copytree(b/'plugin',target,dirs_exist_ok=True);shutil.copy2(b/config.name,config)
 raise
finally:
 subprocess.run(['docker','start','astrbot'],check=True,stdout=subprocess.DEVNULL)
