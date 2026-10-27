"""Run as root on ECS while AstrBot is stopped. No credentials are printed."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess

os.umask(0o077)
root = Path('/home/grainrain/astrbot/data')
config_path = root / 'cmd_config.json'
database_path = root / 'data_v4.db'
state = subprocess.check_output(['docker', 'inspect', 'astrbot', '--format', '{{.State.Running}}'], text=True).strip()
if state != 'false':
    raise SystemExit('Refusing to edit while AstrBot is running')
config = json.loads(config_path.read_text(encoding='utf-8-sig'))
prompt = Path('/tmp/deepark-persona.txt').read_text()
assert prompt.startswith('你是 deepark')
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
backup = Path('/home/grainrain/astrbot-backups') / ('persona-' + stamp)
backup.mkdir(mode=0o700)
shutil.copy2(config_path, backup / 'cmd_config.json')
with sqlite3.connect(database_path) as db, sqlite3.connect(backup / 'data_v4.db') as copy:
    db.backup(copy)
    assert copy.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    old = db.execute('SELECT persona_id,system_prompt,tools,skills FROM personas WHERE persona_id=?', ('deepark',)).fetchone()
    (backup / 'previous-deepark-persona.json').write_text(json.dumps(old, ensure_ascii=False))
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    db.execute('INSERT INTO personas (created_at,updated_at,persona_id,system_prompt,begin_dialogs,tools,skills,sort_order) VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(persona_id) DO UPDATE SET system_prompt=excluded.system_prompt,updated_at=excluded.updated_at', (now,now,'deepark',prompt,'[]','[]','[]',1))
    db.commit()
    assert db.execute('SELECT system_prompt FROM personas WHERE persona_id=?', ('deepark',)).fetchone()[0] == prompt

config['agent_runner']['config']['persona']['persona_id'] = 'deepark'
config['platform_settings']['ignore_bot_self_message'] = True
config['platform_settings']['ignore_at_all'] = True
config['provider_settings']['identifier'] = True
config['provider_settings']['group_name_display'] = True
# Keep history and active-reply settings unchanged until the single scheduler is tested.
temporary = config_path.with_suffix('.json.deepark-tmp')
temporary.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
temporary.chmod(0o600)
os.replace(temporary, config_path)
print(json.dumps({'backup': str(backup), 'persona': 'deepark', 'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(), 'changed': ['agent_runner.config.persona.persona_id','platform_settings.ignore_bot_self_message','platform_settings.ignore_at_all','provider_settings.identifier','provider_settings.group_name_display']}, ensure_ascii=False))
