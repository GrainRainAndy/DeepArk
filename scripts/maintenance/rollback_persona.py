"""Restore only deepark's persona row, never overwrite conversation databases."""
import datetime
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

root=Path('/home/grainrain/astrbot-backups').resolve()
if len(sys.argv)!=2:raise SystemExit('Usage: sudo python3 rollback_persona.py PERSONA_BACKUP_DIRECTORY')
backup=Path(sys.argv[1]).resolve()
if backup.parent!=root or not backup.name.startswith('persona-'):raise SystemExit('Expected an existing persona backup directory')
old=json.loads((backup/'previous-deepark-persona.json').read_text())
if not isinstance(old,list) or len(old)!=4 or old[0]!='deepark':
    raise SystemExit('Backup predates creation of deepark; restore default via WebUI instead')
dbpath=Path('/home/grainrain/astrbot/data/data_v4.db')
subprocess.run(['docker','stop','astrbot'],check=True,stdout=subprocess.DEVNULL)
try:
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    with sqlite3.connect(dbpath) as db:
        current=db.execute('SELECT persona_id,system_prompt,tools,skills FROM personas WHERE persona_id=?',('deepark',)).fetchone()
        saved=root/('before-persona-rollback-'+stamp+'.json')
        with saved.open('x') as f:json.dump(current,f,ensure_ascii=False)
        saved.chmod(0o600)
        db.execute('UPDATE personas SET system_prompt=?,tools=?,skills=?,updated_at=? WHERE persona_id=?',(old[1],old[2],old[3],datetime.datetime.now(datetime.timezone.utc).isoformat(),'deepark'))
        db.commit()
    print('Restored persona row only; chat histories preserved')
finally:
    subprocess.run(['docker','start','astrbot'],check=True,stdout=subprocess.DEVNULL)
