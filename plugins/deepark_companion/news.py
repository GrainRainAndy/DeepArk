"""Bounded official headline cache; no user-controlled URLs or credentials."""
import datetime
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
import urllib.request
import urllib.parse

ORIGIN='https://ak.hypergryph.com'

class Headlines(HTMLParser):
    def __init__(self):
        super().__init__();self.href=None;self.parts=[];self.items=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a':
            href=dict(attrs).get('href','')
            self.href=href if re.fullmatch(r'/news/[0-9]+(?:\.html)?',href) else None
            self.parts=[]
    def handle_data(self,data):
        if self.href:self.parts.append(data)
    def handle_endtag(self,tag):
        if tag!='a' or not self.href:return
        text=' '.join(self.parts)
        date=re.search(r'(20\d{2})\s*//\s*(\d{1,2})\s*/\s*(\d{1,2})',text)
        if date:
            try:
                published=datetime.date(*map(int,date.groups())).isoformat()
                title=text[date.end():].strip()
                if title and len(title)<200:self.items.append({'title':title,'published':published,'url':ORIGIN+self.href})
            except ValueError:pass
        self.href=None

def parse(html):
    parser=Headlines();parser.feed(html)
    return list({item['url']:item for item in parser.items}.values())[:8]

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def refresh(path):
    request=urllib.request.Request(ORIGIN+'/',headers={'User-Agent':'deepark-official-headlines/0.1'})
    with urllib.request.build_opener(NoRedirect).open(request,timeout=15) as response:
        raw=response.read(2_000_001)
    if len(raw)>2_000_000:raise ValueError('Oversize source')
    items=parse(raw.decode('utf-8'))
    if not items:raise ValueError('No dated headlines; keep previous cache')
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps({'fetched':time.time(),'items':items},ensure_ascii=False));tmp.replace(path)
    return len(items)

def read(path,now=None):
    now=time.time() if now is None else now
    try:
        data=json.loads(Path(path).read_text())
        if not 0<=now-data['fetched']<86400:return []
        today=datetime.datetime.fromtimestamp(now,datetime.timezone.utc).date()
        return [x for x in data['items'] if 0<=(today-datetime.date.fromisoformat(x['published'])).days<=30 and x['url'].startswith(ORIGIN+'/news/')][:8]
    except (OSError,ValueError,KeyError,TypeError):return []
