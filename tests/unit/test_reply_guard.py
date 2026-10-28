import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'plugins'/'deepark_companion'))
from reply_guard import has_draft_leak
class GuardTests(unittest.TestCase):
 def test_observed_meme_selection_draft_is_blocked(self):
  self.assertTrue(has_draft_leak('去吧 吃完别又开会 ? No, sleep is for rest. Not fitting. Use food? Already used food recently. Maybe no image, or happy. Keep text only.去吧 吃完别又被抓去开会'))
 def test_normal_english_or_one_phrase_is_not_blocked(self):
  for s in ['今天用DeepSeek API，速度不错','Keep text only.','Maybe no image is necessary.','这张图的sleep是睡觉的意思','No, I would rather eat noodles.']:
   self.assertFalse(has_draft_leak(s))
 def test_draft_without_closing_phrase_is_not_speculatively_filtered(self):
  self.assertFalse(has_draft_leak('Not fitting. Maybe no image.'))
