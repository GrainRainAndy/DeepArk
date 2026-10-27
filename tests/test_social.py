import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from plugin.social import choose

class SocialTests(unittest.TestCase):
    def decision(self,**kwargs):
        obj={'action':'followup','addressed':.9,'interest':.1,'value':.7,'interruption':.1};obj.update(kwargs)
        return json.dumps(obj)
    def test_directed_reply_does_not_require_high_interest(self):
        self.assertEqual(choose(self.decision(),['followup']),'followup')
    def test_high_interest_does_not_override_low_addressed_or_permission(self):
        self.assertEqual(choose(self.decision(addressed=.1,interest=1),['followup']),'skip')
        self.assertEqual(choose(self.decision(),['interject']),'skip')
    def test_interjection_requires_value_and_low_disruption(self):
        self.assertEqual(choose(self.decision(action='interject',interest=.9),['interject']),'interject')
        self.assertEqual(choose(self.decision(action='interject',interest=.9,interruption=.9),['interject']),'skip')
        self.assertEqual(choose(self.decision(action='interject',addressed=False,interest=.9),['interject']),'interject')
    def test_bad_output_fails_closed(self):
        for raw in ('YES','{}',self.decision(interest=True),self.decision(interest=float('nan')),self.decision(action='shell')):
            self.assertEqual(choose(raw,['followup']),'skip')
