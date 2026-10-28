import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from plugins.deepark_companion import trends

class TrendsTests(unittest.TestCase):
    def test_only_recent_game_items_with_canonical_video_ids(self):
        base={'title':'明日方舟新梗','bvid':'BV1234567890','pubdate':99999}
        data={'code':0,'data':{'result':[base,{**base,'pubdate':1},{**base,'bvid':'https://evil.test/'},{**base,'title':'其他游戏新闻'}]}}
        self.assertEqual(len(trends.parse(data,100000)),1)
        self.assertEqual(trends.parse(data,100000)[0]['url'],'https://www.bilibili.com/video/BV1234567890')
    def test_rejected_search_is_not_successful_refresh(self):
        with self.assertRaises(ValueError):trends.parse({'code':-412},100000)
    def test_expired_cache_is_not_used(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'trends.json';path.write_text(json.dumps({'fetched':1,'items':[{'published_unix':100000}]}))
            self.assertEqual(trends.read(path,100000),[])
