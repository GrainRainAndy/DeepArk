"""Configure requested ecosystem via localhost management API; prints no secrets."""
import importlib.util,json,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('admin','/tmp/deepark-ecosystem-api.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
c=a.config(); model=c['agent_runner']['config']['model']['provider_id']
whitelist=c['platform_settings']['id_whitelist']
friends=[s for s in whitelist if ':FriendMessage:' in s]
assert friends, 'No authorized private session'
key=Path('/home/grainrain/astrbot/.sf-embedding-key').read_text().strip()
pid='deepark-memory-sf'
p={'id':pid,'type':'openai_embedding','provider':'openai','provider_type':'embedding','enable':True,'embedding_api_key':key,'embedding_api_base':'https://api.siliconflow.cn/v1','embedding_model':'BAAI/bge-m3','embedding_dimensions':1024,'embedding_dimensions_mode':'auto','timeout':30,'proxy':''}
# This deployment creates the dedicated provider once.
try:a.call('GET','/providers/'+pid);exists=True
except Exception:exists=False
a.call('PUT' if exists else 'POST','/providers/'+pid if exists else '/providers',{'config':p})
a.call('POST','/providers/test',{'provider_id':pid},timeout=90)
print('Cloud embedding provider tested',flush=True)

def update(name,fn):
 cfg=a.call('GET','/plugins/config?plugin_id='+name)['data']['config'];fn(cfg)
 a.call('PUT','/plugins/config',{'plugin_id':name,'config':cfg})
 print('Configured '+name,flush=True)
def memory(x):
 x['access_control'].update(whitelist_enabled=True,allowed_ids='\n'.join(whitelist))
 x['provider_settings'].update(embedding_provider_id=pid,llm_provider_id=model)
 x['filtering_settings'].update(use_persona_filtering=True,use_session_filtering=True,memory_scope_mode='session')
 x['agent_tools'].update(enable_recall_tool=True,enable_memorize_tool=True,enable_forget_tool=True)
 x['recall_engine']['rerank_enabled']=False
 x['session_manager'].update(context_window_size=50,enable_full_group_capture=True)
 x['reflection_engine']['summary_trigger_rounds']=10
update('astrbot_plugin_livingmemory',memory)
def meme(x):
 x['semantic']['enabled']=False;x['auto_collect']['enabled']=False
 x['community']['github_accelerator_url']=''
 x['generation']['trigger']['scope']='chat_and_plugin_llm'
 x['generation']['emotion']['llm']['enabled']=False
 x['generation']['emotion'].update(max_memes_per_message=1,probability=35)
 x['generation']['prompt']['quantity_guidance_enabled']=True
 x['generation']['message']['send_image_as_base64']=True
 # Local pack files are served directly; remote image storage stays unconfigured.
update('meme_manager',meme)
def qzone(x):
 x['trigger'].update(publish_cron='',comment_cron='',read_prob=0,send_admin=False,like_when_comment=False)
 for k in ['post_provider_id','comment_provider_id','reply_provider_id']:x['llm'][k]=model
update('astrbot_plugin_qzone',qzone)
update('astrbot_plugin_qqprofile',lambda x:x.update(sync_name=False))
def proactive(x):
 f=x['friend_settings'];f.update(enable=True,session_list=friends)
 f['auto_trigger_settings'].update(enable_auto_trigger=True,auto_trigger_after_minutes=120)
 f['schedule_settings'].update(min_interval_minutes=120,max_interval_minutes=480,quiet_hours='4-9',max_unanswered_times=1)
 f['tts_settings']['enable_tts']=False
 f['proactive_prompt']='现在是 {{current_time}}。你是deepark，延续既有人格。根据这段私聊最近的话题，挑一件具体小事自然接一句；话题结束可以分享一个明日方舟审美偏好或轻松想法。没有来源就不编新活动、新梗、刚刷到或线下经历。不问在干嘛，不催回复，不表达被冷落、不撒娇，不每次以问句收尾。只发一两句短话。未回复次数 {{unanswered_count}}。不调用发布空间、修改资料或其他对外操作工具。'
 f['segmented_reply_settings'].update(enable=True,regex=r'.*?(?:\r?\n+|[。？！~…]+)|.+$')
 x['group_settings']['enable']=False;x['group_settings']['session_list']=[]
 x['group_settings']['auto_trigger_settings']['enable_auto_trigger']=False
 x['group_settings']['tts_settings']['enable_tts']=False
 x['group_settings']['schedule_settings']['quiet_hours']='4-9'
 for k in ['web_admin','notification_settings','telemetry_config']:x[k]['enabled']=False
update('astrbot_plugin_proactive_chat',proactive)
mem=['recall_long_term_memory','memorize_long_term_memory']
admin=['forget_long_term_memory','llm_view_feed','llm_publish_feed','qqprofile_set_avatar','qqprofile_set_signature','qqprofile_set_status','qqprofile_set_nickname']
# Activation is separate, after the companion guard and persona are deployed.
Path('/tmp/deepark-ecosystem-tools.json').write_text(json.dumps({'memory':mem,'admin':admin}))
print('All requested plugin configurations saved',flush=True)
