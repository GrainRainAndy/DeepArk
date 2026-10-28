"""Public Arknights community leads, not verified meme origins or popularity claims."""
import html
import json
from pathlib import Path
import re
import time
import urllib.request
import urllib.parse
from .news import NoRedirect
from .core import safe_text

def parse(data,now):
    if data.get('code')!=0:raise ValueError('Search rejected')
    out=[]
    for item in data.get('data',{}).get('result',[]):
        title=html.unescape(re.sub('<[^>]*>','',str(item.get('title','')))).strip()
        bvid=str(item.get('bvid',''))
        published=item.get('pubdate',0)
        if not isinstance(published,(int,float)) or not 0<=now-published<14*86400:continue
        if not re.fullmatch(r'BV[0-9A-Za-z]{10}',bvid):continue
        if not re.search('明日方舟|阿米娅|罗德岛|塔露拉|凯尔希|能天使|史尔特尔|博士|舟',title):continue
        if not safe_text(title,160) or len(title)>160:continue
        out.append({'title':title,'published_unix':published,'url':'https://www.bilibili.com/video/'+bvid,'status':'社区投稿标题，未观看视频，非已核实梗出处'})
    return list({x['url']:x for x in out}.values())[:6]

def refresh(path):
    query=urllib.parse.urlencode({'search_type':'video','keyword':'明日方舟 梗','order':'pubdate','page':1})
    req=urllib.request.Request('https://api.bilibili.com/x/web-interface/search/type?'+query,headers={'User-Agent':'Mozilla/5.0','Referer':'https://search.bilibili.com/'})
    with urllib.request.build_opener(NoRedirect).open(req,timeout=15) as r:raw=r.read(1_000_001)
    if len(raw)>1_000_000:raise ValueError('Oversize source')
    now=time.time();items=parse(json.loads(raw),now)
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps({'fetched':now,'items':items},ensure_ascii=False));tmp.replace(path)

def read(path,now=None):
    now=time.time() if now is None else now
    try:
        data=json.loads(Path(path).read_text())
        if not 0<=now-data['fetched']<86400:return []
        return [x for x in data['items'] if 0<=now-x['published_unix']<14*86400][:6]
    except (OSError,ValueError,KeyError,TypeError):return []
