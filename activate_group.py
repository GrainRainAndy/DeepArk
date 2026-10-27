"""Run only with the user's confirmed target QQ group number. No message sends."""
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

if len(sys.argv)!=2 or not re.fullmatch(r'[1-9][0-9]{4,11}',sys.argv[1]):
    raise SystemExit('Usage: sudo python3 activate_group.py CONFIRMED_QQ_GROUP_NUMBER')
group=sys.argv[1]
root=Path('/home/grainrain/astrbot/data')
main=root/'cmd_config.json'
plugin=root/'config/astrbot_plugin_deepark_companion_config.json'
backup=Path('/home/grainrain/astrbot-backups')/('group-activation-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
backup.mkdir(mode=0o700)
subprocess.run(['docker','stop','astrbot'],check=True,stdout=subprocess.DEVNULL)
try:
    for path in (main,plugin):
        shutil.copy2(path,backup/path.name);(backup/path.name).chmod(0o600)
    cfg=json.loads(main.read_text(encoding='utf-8-sig'))
    pcfg=json.loads(plugin.read_text(encoding='utf-8-sig'))
    whitelist=cfg['platform_settings']['id_whitelist']
    if group not in whitelist:whitelist.append(group)
    cfg['platform_settings']['enable_id_white_list']=True
    cfg['provider_ltm_settings']['group_icl_enable']=False
    cfg['provider_ltm_settings']['group_message_history_enable']=False
    cfg['provider_ltm_settings']['active_reply']['enable']=False
    cfg['provider_settings']['streaming_response']=False
    pcfg.update(allow_groups=[group],proactive_enabled=True,dry_run=False)
    for path,data in ((main,cfg),(plugin,pcfg)):
        temp=path.with_suffix('.activation.tmp')
        fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as f:json.dump(data,f,ensure_ascii=False,indent=2)
        os.replace(temp,path)
    rollback=backup/'rollback.sh'
    rollback.write_text('#!/bin/sh\nset -eu\ndocker stop astrbot >/dev/null\ntrap \'docker start astrbot >/dev/null\' EXIT\n'+''.join('install -m 600 '+str(backup/p.name)+' '+str(p)+'\n' for p in (main,plugin)))
    rollback.chmod(0o700)
    print('Activated one confirmed group; backup: '+str(backup))
except Exception:
    for path in (main,plugin):
        if (backup/path.name).exists():shutil.copy2(backup/path.name,path)
    raise
finally:
    subprocess.run(['docker','start','astrbot'],check=True,stdout=subprocess.DEVNULL)
