"""Offline atomic config/persona/companion update; preserve all chat and plugin data."""
import datetime,json,os,shutil,sqlite3,subprocess
from pathlib import Path
os.umask(0o077)
r=Path('/home/grainrain/astrbot/data')
b=Path('/home/grainrain/astrbot-backups')/('ecosystem-config-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));b.mkdir(mode=0o700)
tools=json.loads(Path('/tmp/deepark-ecosystem-tools.json').read_text())
subprocess.run(['docker','stop','astrbot'],check=True,stdout=subprocess.DEVNULL)
def write(p,c):
 t=p.with_suffix('.ecosystem-tmp');t.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n');t.chmod(0o600);os.replace(t,p)
try:
 shutil.copy2(r/'cmd_config.json',b/'cmd_config.json');shutil.copytree(r/'config',b/'config')
 target=r/'plugins/astrbot_plugin_deepark_companion';shutil.copytree(target,b/'companion')
 with sqlite3.connect(r/'data_v4.db') as db,sqlite3.connect(b/'data_v4.db') as backup:
  db.backup(backup)
  prompt=Path('/tmp/deepark-ecosystem-persona.txt').read_text()
  assert prompt.startswith('你是 deepark')
  result=db.execute('UPDATE personas SET system_prompt=?,tools=?,updated_at=? WHERE persona_id=?',(prompt,json.dumps(tools['memory']+tools['admin']),datetime.datetime.now(datetime.timezone.utc).isoformat(),'deepark'))
  assert result.rowcount==1;db.commit()
 c=json.loads((r/'cmd_config.json').read_text(encoding='utf-8-sig'))
 c['agent_runner']['config']['persona']['persona_id']='deepark'
 c['platform_settings']['segmented_reply'].update(enable=True,only_llm_result=True,regex=r'.*?(?:\r?\n+|[。？！~…]+)|.+$')
 c['provider_ltm_settings']['active_reply']['enable']=False
 write(r/'cmd_config.json',c)
 p=r/'config/astrbot_plugin_deepark_companion_config.json';comp=json.loads(p.read_text(encoding='utf-8-sig'))
 comp.update(memory_backend='livingmemory',ecosystem_tool_guard=True,memory_tools=tools['memory'],admin_social_tools=tools['admin'],auto_memory=False)
 write(p,comp)
 for source in Path('/tmp/deepark-adapter-test/plugin').iterdir():
  if source.is_file() and source.suffix in ('.py','.json','.yaml'):shutil.copy2(source,target/source.name)
 print('Configuration backup: '+str(b),flush=True)
finally:subprocess.run(['docker','start','astrbot'],check=True,stdout=subprocess.DEVNULL)
