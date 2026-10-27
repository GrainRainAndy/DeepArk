"""Install tested plugin with an empty group allowlist until target group is known."""
import datetime
import json
from pathlib import Path
import shutil
import subprocess

root=Path('/home/grainrain/astrbot/data')
target=root/'plugins/astrbot_plugin_deepark_companion'
conf=root/'config/astrbot_plugin_deepark_companion_config.json'
assert not target.exists(), 'Existing plugin requires upgrade-specific backup'
assert not conf.exists(), 'Existing configuration must be reviewed'
backup=Path('/home/grainrain/astrbot-backups')/('companion-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
backup.mkdir(mode=0o700)
subprocess.run(['docker','stop','astrbot'],check=True,stdout=subprocess.DEVNULL)
try:
    shutil.copy2(root/'cmd_config.json',backup/'cmd_config.json')
    (backup/'cmd_config.json').chmod(0o600)
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree('/tmp/deepark-adapter-test/plugin',target,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    conf.parent.mkdir(parents=True,exist_ok=True)
    conf.write_text(json.dumps({'enabled':True,'allow_groups':[],'proactive_enabled':False,'dry_run':True,'auto_memory':True},ensure_ascii=False,indent=2))
    conf.chmod(0o600)
    # Native behavior is unchanged until a concrete group is authorized.
    rollback=backup/'rollback.sh'
    rollback.write_text('#!/bin/sh\nset -eu\ndocker stop astrbot >/dev/null\ntrap \'docker start astrbot >/dev/null\' EXIT\nmv '+str(target)+' '+str(backup/'plugin-disabled')+'\nmv '+str(conf)+' '+str(backup/'plugin-config-disabled.json')+'\n')
    rollback.chmod(0o700)
    print(json.dumps({'backup':str(backup),'group_count':0,'proactive':False}))
finally:
    subprocess.run(['docker','start','astrbot'],check=True,stdout=subprocess.DEVNULL)
