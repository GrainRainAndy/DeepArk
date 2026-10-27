import datetime,tempfile,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from plugin.core import Store
from plugin import social
class ParticipationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.path=Path(self.tmp.name)/'s.db';self.s=Store(self.path,{'group_reply_hourly_limit':300,'participation_probe_hourly_limit':300});self.addCleanup(self.s.close)
 def test_rolling_reply_cap_survives_restart_and_is_scoped(self):
  self.assertTrue(hasattr(self.s,'reserve_reply'))
  for i in range(300):self.assertTrue(self.s.reserve_reply('g',10000+i))
  self.assertFalse(self.s.reserve_reply('g',10301));self.assertTrue(self.s.reserve_reply('other',10301))
  other=Store(self.path,{'group_reply_hourly_limit':300})
  try:
   self.assertFalse(other.reserve_reply('g',10302));self.assertTrue(other.reserve_reply('g',13600));self.assertFalse(other.reserve_reply('g',13600))
  finally:other.close()
 def test_probe_limit_can_exceed_old_thirty(self):
  for i in range(300):self.assertTrue(self.s.reserve_followup_probe('g',10000+i*6),i)
  self.assertFalse(self.s.reserve_followup_probe('g',11801))
 def test_night_wrap_and_quiet_hours(self):
  self.s.policy.update(active_start_hour=9,active_end_hour=4)
  for h in (0,3,9,23):self.assertTrue(self.s.in_hours(h),h)
  for h in (4,5,8):self.assertFalse(self.s.in_hours(h),h)
 def test_noise_and_meaningful_corrections(self):
  self.assertTrue(hasattr(social,'is_noise'))
  for x in ('*','（（','哈哈哈','😂','嗯','草'):self.assertTrue(social.is_noise(x),x)
  for x in ('别回了','不是阿米娅，是能天使','为什么这么说','换个话题','你说的不对'):self.assertFalse(social.is_noise(x),x)
 def test_relevance_json_fails_closed(self):
  self.assertTrue(hasattr(social,'keep_reply'))
  self.assertTrue(social.keep_reply('{"keep":true}'))
  for x in ('{"keep":false}','{"keep":"true"}','yes','{}'):self.assertFalse(social.keep_reply(x))
if __name__=='__main__':unittest.main()
