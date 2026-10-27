"""Exercise the production authorization method without starting AstrBot."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest


tree = ast.parse((Path(__file__).parents[1] / 'plugin/main.py').read_text())
klass = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'DeeparkCompanion')
method = next(n for n in klass.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'allowed')


class AuthorizationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.scope = 'deepark:GroupMessage:123'
        self.settings = {'platform_settings': {'enable_id_white_list': True, 'id_whitelist': [self.scope]}}
        self.session = {}
        async def get_async(**kwargs):
            return self.session if kwargs['key'] == 'session_service_config' else {}
        namespace = {'sp': SimpleNamespace(get_async=get_async)}
        exec(compile(ast.Module(body=[method], type_ignores=[]), 'allowed', 'exec'), namespace)
        self.allowed = namespace['allowed']
        self.owner = SimpleNamespace(config={'enabled': True, 'allow_groups': ['old-group']},
                                     context=SimpleNamespace(get_config=lambda scope: self.settings))

    async def test_whitelist_addition_and_removal_take_effect_immediately(self):
        self.assertTrue(await self.allowed(self.owner, self.scope, '123'))
        self.settings['platform_settings']['id_whitelist'] = []
        self.assertFalse(await self.allowed(self.owner, self.scope, '123'))

    async def test_private_and_other_platform_entries_do_not_authorize_group(self):
        for entry in ['deepark:FriendMessage:123', 'other:GroupMessage:123']:
            self.settings['platform_settings']['id_whitelist'] = [entry]
            self.assertFalse(await self.allowed(self.owner, self.scope, '123'))

    async def test_numeric_group_entry_and_disabled_whitelist(self):
        self.settings['platform_settings'] = {'enable_id_white_list': False, 'id_whitelist': ['123']}
        self.assertTrue(await self.allowed(self.owner, self.scope, '123'))
        self.settings['platform_settings']['id_whitelist'] = []
        self.assertFalse(await self.allowed(self.owner, self.scope, '123'))

    async def test_session_and_plugin_controls_still_apply(self):
        self.assertTrue(await self.allowed(self.owner, self.scope, '123'))
        self.session['llm_enabled'] = False
        self.assertFalse(await self.allowed(self.owner, self.scope, '123'))
        self.session.clear()
        self.settings['plugin_set'] = ['other']
        self.assertFalse(await self.allowed(self.owner, self.scope, '123'))
