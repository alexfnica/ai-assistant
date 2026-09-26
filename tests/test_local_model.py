import tempfile
import unittest
from pathlib import Path
from jarvis.local_model import LocalModel
from jarvis.storage import Store
from jarvis.personality import load_prompt
from jarvis.integrations import NotConnected


class LocalModelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / 'db.sqlite3')
        self.model = LocalModel(self.store, self.temp.name)
        self.addCleanup(self.model.close)

    def test_missing_files_fail_honestly(self):
        with self.assertRaises(NotConnected):
            self.model.reply('Explain filters', 'general', system_prompt=load_prompt())

    def test_context_is_bounded_scoped_and_current_not_duplicated(self):
        self.store.remember('fishroom', 'Tank Atlas')
        self.store.remember('game', 'unrelated secret')
        for i in range(20):
            self.store.message('user', 'past ' + str(i), 'fishroom')
        self.store.message('user', 'current question', 'fishroom')
        messages = self.model.messages('current question', 'fishroom', load_prompt())
        self.assertEqual(len(messages), 9)
        self.assertIn('Tank Atlas', messages[1]['content'])
        self.assertNotIn('unrelated secret', str(messages))
        self.assertEqual(sum('current question' in m['content'] for m in messages), 1)

    def test_generated_actions_remain_text(self):
        self.model.start = lambda: None
        self.model.request = lambda *a, **k: {'choices':[{'message':{'content':'task: imaginary action'}}]}
        self.assertEqual(self.model.reply('plan', 'general', system_prompt='English'), 'task: imaginary action')
        self.assertEqual(self.store.tasks(), [])

    def test_provider_errors_do_not_leak(self):
        self.model.start = lambda: None
        def fail(*a, **k):
            raise RuntimeError('private token')
        self.model.request = fail
        with self.assertRaises(NotConnected) as error:
            self.model.reply('plan', 'general', system_prompt='English')
        self.assertNotIn('private token', str(error.exception))

    def test_large_prompt_rejected(self):
        with self.assertRaises(ValueError):
            self.model.messages('x'*3501, 'general', 'English')
