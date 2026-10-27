"""Backup and replace plugin code only; preserve configuration and memory."""
import datetime
from pathlib import Path
import shutil
import subprocess

target=Path('/home/grainrain/astrbot/data/plugins/astrbot_plugin_deepark_companion')
backup=Path('/home/grainrain/astrbot-backups')/('companion-update-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
assert target.is_dir()
backup.mkdir(mode=0o700)
subprocess.run(['docker','stop','astrbot'],check=True,stdout=subprocess.DEVNULL)
try:
    shutil.copytree(target,backup/'plugin')
    for source in Path('/tmp/deepark-adapter-test/plugin').iterdir():
        if source.is_file() and source.suffix in ('.py','.json','.yaml'):shutil.copy2(source,target/source.name)
    rollback=backup/'rollback.sh'
    rollback.write_text('#!/bin/sh\nset -eu\ndocker stop astrbot >/dev/null\ntrap \'docker start astrbot >/dev/null\' EXIT\nmv '+str(target)+' '+str(backup/'replaced-plugin')+'\ncp -a '+str(backup/'plugin')+' '+str(target)+'\n')
    rollback.chmod(0o700)
    print('Plugin backup: '+str(backup))
finally:
    subprocess.run(['docker','start','astrbot'],check=True,stdout=subprocess.DEVNULL)
