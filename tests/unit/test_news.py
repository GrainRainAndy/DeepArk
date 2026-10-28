import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('news',Path(__file__).parents[2]/'plugins/deepark_companion/news.py')
news=importlib.util.module_from_spec(spec);spec.loader.exec_module(news)

class NewsTests(unittest.TestCase):
    def test_only_dated_official_article_links(self):
        html='<a href="/news/12"><div>活动</div><div>2026 // 10 / 24</div><div>测试活动</div></a><a href="https://evil.test/news/3">2026 // 10 / 24 假消息</a><a href="/news/4">无日期</a>'
        self.assertEqual(news.parse(html),[{'title':'测试活动','published':'2026-10-24','url':'https://ak.hypergryph.com/news/12'}])
    def test_stale_cache_disappears(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'news.json';p.write_text(json.dumps({'fetched':100,'items':[{'title':'x','published':'2026-10-24','url':'https://ak.hypergryph.com/news/1'}]}))
            self.assertEqual(news.read(p,100+86401),[])
    def test_invalid_date_not_trusted(self):
        self.assertEqual(news.parse('<a href="/news/1">2026 // 99 / 99 无效日期</a>'),[])
