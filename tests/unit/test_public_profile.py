import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'plugins' / 'deepark_companion'))

class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('public_profile'), 'public profile layer not implemented')
        from public_profile import PublicProfiles, identity, parse_command
        self.identity,self.parse=identity,parse_command
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/'profiles.db'
        self.store=PublicProfiles(self.path)
        self.addCleanup(self.tmp.cleanup);self.addCleanup(self.store.close)
        self.who=self.identity('deepark:FriendMessage:12345','99999','12345')

    def test_same_authenticated_qq_across_group_and_private(self):
        group=self.identity('deepark:GroupMessage:45678','99999','12345')
        self.assertEqual(self.who,group)
        self.store.remember(self.who,'昵称','小雨','deepark:FriendMessage:12345')
        self.assertEqual(self.store.snapshot(group)[1],{'昵称':'小雨'})

    def test_sender_platform_and_bot_are_separate(self):
        self.store.remember(self.who,'喜欢的干员','阿米娅','private')
        for scope,bot,user in [('deepark:GroupMessage:45678','99999','54321'),('other:FriendMessage:12345','99999','12345'),('deepark:FriendMessage:12345','88888','12345')]:
            self.assertEqual(self.store.snapshot(self.identity(scope,bot,user))[1],{})

    def test_invalid_identity_and_spoofed_private_session(self):
        for args in [('deepark:FriendMessage:12345','99999','54321'),('bad','99999','12345'),('deepark:GroupMessage:45678','','12345'),('deepark:GroupMessage:45678','12345','12345')]:
            self.assertIsNone(self.identity(*args))

    def test_reopen_update_and_revoke_version(self):
        self.store.remember(self.who,'昵称','小雨','private')
        rev,rows=self.store.snapshot(self.who)
        from public_profile import PublicProfiles
        other=PublicProfiles(self.path)
        try:self.assertEqual(other.snapshot(self.who),(rev,rows))
        finally:other.close()
        self.store.remember(self.who,'昵称','雨雨','group')
        updated=self.store.snapshot(self.who)
        self.assertGreater(updated[0],rev);self.assertEqual(updated[1],{'昵称':'雨雨'})
        self.store.forget(self.who,'昵称')
        self.assertGreater(self.store.snapshot(self.who)[0],updated[0]);self.assertEqual(self.store.snapshot(self.who)[1],{})

    def test_forget_all_only_removes_own_profile(self):
        other=self.identity('deepark:GroupMessage:45678','99999','54321')
        for who in (self.who,other):self.store.remember(who,'昵称','abc','group')
        self.store.forget(self.who,'全部')
        self.assertEqual(self.store.snapshot(self.who)[1],{})
        self.assertEqual(self.store.snapshot(other)[1],{'昵称':'abc'})

    def test_only_explicit_whole_commands_are_recognized(self):
        self.assertEqual(self.parse('/deepark 公开记住 昵称=小雨'),('remember','昵称','小雨'))
        self.assertEqual(self.parse('/deepark 公开记忆'),('list','',''))
        self.assertEqual(self.parse('/deepark 取消公开 全部'),('forget','全部',''))
        for text in ['我喜欢阿米娅','他说 /deepark 公开记住 昵称=小雨','/deeparkx 公开记忆','/deepark 记住 昵称=小雨']:
            self.assertIsNone(self.parse(text))

    def test_reject_unknown_field_multiline_and_oversize(self):
        for field,value in [('地址','test'),('昵称','x'*81),('昵称','a\nb'),('昵称',''),('昵称','a\x00b')]:
            with self.assertRaises(ValueError):self.store.remember(self.who,field,value,'private')
        self.assertEqual(self.store.snapshot(self.who)[1],{})

if __name__=='__main__':unittest.main()
