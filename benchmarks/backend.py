"""Bounded, synthetic-only endpoint benchmark. No QQ and no configuration writes."""
import concurrent.futures,json,pathlib,sqlite3,time,urllib.request,urllib.parse
r=pathlib.Path('/home/grainrain/astrbot/data');c=json.loads((r/'cmd_config.json').read_text(encoding='utf-8-sig'))
p=next(x for x in c['provider'] if x['id']==c['agent_runner']['config']['model']['provider_id'])
s=next(x for x in c['provider_sources'] if x['id']==p['provider_source_id']);base=s['api_base'].rstrip('/')
assert urllib.parse.urlsplit(base).hostname=='llmapi.paratera.com'
key=s['key'];key=key[0] if isinstance(key,list) else key
with sqlite3.connect('file:'+str(r/'data_v4.db')+'?mode=ro',uri=True) as db:persona=db.execute('SELECT system_prompt FROM personas WHERE persona_id=?',('deepark',)).fetchone()[0]

def run(label,disabled=False,stream=True,long=False):
 body={'model':p['model'],'messages':[{'role':'system','content':'Follow the requested output format.' if long else persona},{'role':'user','content':'依次写出1至100的编号，每行格式为“编号：这是一段用于测试生成速度的文字。”，不要省略，持续输出。' if long else '今天午饭忘了吃，现在有点饿，等会还得开会。'}],'max_tokens':384,'stream':stream,**p.get('custom_extra_body',{})}
 if disabled:body['thinking']={'type':'disabled'}
 if stream:body['stream_options']={'include_usage':True}
 req=urllib.request.Request(base+'/chat/completions',data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
 start=time.monotonic();first=None;visible=None;last=None;parts=[];reason_chars=0;usage={};finish=None;headers=None
 try:
  with urllib.request.urlopen(req,timeout=60) as resp:
   headers=time.monotonic()-start
   if stream:
    for raw in resp:
     if time.monotonic()-start>90:raise TimeoutError('wall deadline')
     if not raw.startswith(b'data:'):continue
     data=raw[5:].strip()
     if data==b'[DONE]':break
     x=json.loads(data)
     if x.get('usage'):usage=x['usage']
     for choice in x.get('choices',[]):
      delta=choice.get('delta',{});content=delta.get('content') or '';reason=delta.get('reasoning_content') or ''
      now=time.monotonic()-start
      if content or reason:
       if first is None:first=now
       last=now
      if content:
       if visible is None:visible=now
       parts.append(content)
      reason_chars+=len(reason)
      finish=choice.get('finish_reason') or finish
   else:
    x=json.load(resp);usage=x.get('usage',{});m=x['choices'][0]['message'];parts=[m.get('content') or ''];reason_chars=len(m.get('reasoning_content') or '');finish=x['choices'][0].get('finish_reason')
  duration=time.monotonic()-start;tokens=usage.get('completion_tokens');out={'label':label,'thinking_disabled_requested':disabled,'stream':stream,'seconds':round(duration,3),'headers_s':round(headers,3),'first_output_s':round(first,3) if first is not None else None,'first_visible_s':round(visible,3) if visible is not None else None,'output_chars':len(''.join(parts)),'reasoning_chars':reason_chars,'usage':usage,'finish':finish,'end_to_end_tokens_s':round(tokens/duration,2) if tokens else None,'generation_tokens_s':round(tokens/(last-first),2) if tokens and last and first is not None and last>first else None}
 except Exception as e:out={'label':label,'error':type(e).__name__,'status':getattr(e,'code',None),'seconds':round(time.monotonic()-start,3)}
 print(json.dumps(out,ensure_ascii=False),flush=True);return out

for i in range(3):
 run('persona-default-'+str(i));run('persona-disabled-'+str(i),True)
for disabled in [False,True]:run('persona-nonstream-'+str(disabled),disabled,False)
for i in range(2):run('generation-single-'+str(i),True,long=True)
start=time.monotonic()
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 results=list(pool.map(lambda i:run('generation-concurrent3-'+str(i),True,long=True),range(3)))
duration=time.monotonic()-start;total=sum(x.get('usage',{}).get('completion_tokens',0) for x in results)
print(json.dumps({'label':'concurrent3-summary','seconds':round(duration,3),'completion_tokens':total,'aggregate_tokens_s':round(total/duration,2)}),flush=True)
