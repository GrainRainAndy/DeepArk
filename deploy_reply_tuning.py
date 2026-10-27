import datetime,json,os,shutil,sqlite3,subprocess
from pathlib import Path
os.umask(0o077);r=Path('/home/grainrain/astrbot/data');b=Path('/home/grainrain/astrbot-backups')/('reply-tuning-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));b.mkdir(mode=0o700)
paths=[r/'cmd_config.json',r/'config/astrbot_plugin_deepark_companion_config.json',r/'config/meme_manager_config.json']
target=r/'plugins/astrbot_plugin_deepark_companion'
def write(p,x):
 t=p.with_suffix('.tuning-tmp');t.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n');t.chmod(0o600);os.replace(t,p)
subprocess.run(['docker','stop','astrbot'],check=True,stdout=subprocess.DEVNULL)
try:
 for p in paths:shutil.copy2(p,b/p.name)
 shutil.copytree(target,b/'plugin')
 with sqlite3.connect(r/'data_v4.db') as d,sqlite3.connect(b/'data_v4.db') as backup:
  d.backup(backup)
  old=d.execute('SELECT system_prompt FROM personas WHERE persona_id=?',('deepark',)).fetchone()[0];(b/'persona.txt').write_text(old)
  prompt=Path('/tmp/deepark-reply-persona.txt').read_text();assert prompt.startswith('你是 deepark')
  d.execute('UPDATE personas SET system_prompt=?,updated_at=? WHERE persona_id=?',(prompt,datetime.datetime.now(datetime.timezone.utc).isoformat(),'deepark'));d.commit()
 c=json.loads(paths[0].read_text(encoding='utf-8-sig'));c['provider_settings']['display_reasoning_text']=False
 official=next(p for p in c['provider'] if p['id']=='deepseek/deepseek-flash');official.setdefault('custom_extra_body',{})['thinking']={'type':'disabled'};write(paths[0],c)
 comp=json.loads(paths[1].read_text(encoding='utf-8-sig'));comp.update(batch_quiet_seconds=2.8,batch_max_seconds=5.0);write(paths[1],comp)
 meme=json.loads(paths[2].read_text(encoding='utf-8-sig'));meme['generation']['emotion']['probability']=20;meme['generation']['prompt']['quantity_guidance_enabled']=False;write(paths[2],meme)
 for src in Path('/tmp/deepark-batch-tests/plugin').iterdir():
  if src.is_file() and src.suffix in ('.py','.json','.yaml'):shutil.copy2(src,target/src.name)
 print('Backup: '+str(b),flush=True)
finally:subprocess.run(['docker','start','astrbot'],check=True,stdout=subprocess.DEVNULL)
