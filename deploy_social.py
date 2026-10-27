"""Deploy participation planner with a separate bounded non-thinking provider."""
import copy
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess

root=Path('/home/grainrain/astrbot/data');main=root/'cmd_config.json'
pc=root/'config/astrbot_plugin_deepark_companion_config.json'
target=root/'plugins/astrbot_plugin_deepark_companion'
backup=Path('/home/grainrain/astrbot-backups')/('social-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
backup.mkdir(mode=0o700)
subprocess.run(['docker','stop','astrbot'],check=True,stdout=subprocess.DEVNULL)
try:
    for path in (main,pc):shutil.copy2(path,backup/path.name)
    shutil.copytree(target,backup/'plugin')
    cfg=json.loads(main.read_text(encoding='utf-8-sig'));plugin=json.loads(pc.read_text(encoding='utf-8-sig'))
    pid=cfg['agent_runner']['config']['model']['provider_id']
    primary=next(p for p in cfg['provider'] if p['id']==pid)
    decision=copy.deepcopy(primary)
    decision.update(id='deepark-decision',enable=True,custom_extra_body={'thinking':{'type':'disabled'},'max_tokens':700},timeout=15)
    cfg['provider']=[p for p in cfg['provider'] if p['id']!='deepark-decision']+[decision]
    plugin.update(decision_provider_id='deepark-decision',followup_enabled=True,followup_window_seconds=120,followup_burst_limit=3)
    for path,data in ((main,cfg),(pc,plugin)):
        tmp=path.with_suffix('.social.tmp')
        fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as f:json.dump(data,f,ensure_ascii=False,indent=2)
        os.replace(tmp,path)
    for source in Path('/tmp/deepark-adapter-test/plugin').iterdir():
        if source.is_file() and not source.name.startswith('._') and source.suffix in ('.py','.json','.yaml'):shutil.copy2(source,target/source.name)
    rollback=backup/'rollback.sh'
    rollback.write_text('#!/bin/sh\nset -eu\ndocker stop astrbot >/dev/null\ntrap \'docker start astrbot >/dev/null\' EXIT\n'+''.join('install -m 600 '+str(backup/p.name)+' '+str(p)+'\n' for p in (main,pc))+'mv '+str(target)+' '+str(backup/'disabled-plugin')+'\ncp -a '+str(backup/'plugin')+' '+str(target)+'\n')
    rollback.chmod(0o700)
    print(json.dumps({'backup':str(backup),'groups':len(plugin['allow_groups']),'proactive':plugin['proactive_enabled'],'dry_run':plugin['dry_run']}))
except Exception:
    for path in (main,pc):
        if (backup/path.name).exists():shutil.copy2(backup/path.name,path)
    if (backup/'plugin').exists():shutil.copytree(backup/'plugin',target,dirs_exist_ok=True)
    raise
finally:
    subprocess.run(['docker','start','astrbot'],check=True,stdout=subprocess.DEVNULL)
