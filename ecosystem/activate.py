import importlib.util,json
spec=importlib.util.spec_from_file_location('admin','/tmp/deepark-ecosystem-api.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
enabled={x['name'] for x in a.call('GET','/plugins')['data'] if x['activated']}
for name in ['astrbot_plugin_livingmemory','meme_manager','astrbot_plugin_qzone','astrbot_plugin_qqprofile']:
 if name not in enabled:a.call('PATCH','/plugins/enabled',{'plugin_id':name,'enabled':True},timeout=180)
 print('Enabled '+name,flush=True)
for tool in json.loads(a.Path('/tmp/deepark-ecosystem-tools.json').read_text())['admin']+['qqprofile_switch_persona','qqprofile_list_personas']:
 a.call('PATCH','/tools/'+tool+'/permission',{'permission':'admin'})
for cmd in a.call('GET','/commands')['data']['items']:
 if cmd.get('plugin')=='astrbot_plugin_qzone':
  a.call('PATCH','/commands/'+cmd['handler_full_name'],{'permission_group':'admin'})
print('Admin tool and command permissions saved',flush=True)
ext='/plugins/extensions/meme_manager'
a.call('POST',ext+'/community/index/fetch',{},timeout=120)
print('Meme community index fetched',flush=True)
a.call('POST',ext+'/community/install',{'pack_id':'deepseek-fanart-meme-pack','set_as_default':True},timeout=900)
print('DeepSeek fanart pack installed',flush=True)
