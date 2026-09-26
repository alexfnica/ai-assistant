import tempfile
import unittest
from pathlib import Path
from jarvis.core import Core
from jarvis.storage import Store
from jarvis.integrations import Integrations
from jarvis.personality import load_prompt


class PersonalityTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.store = Store(Path(temp.name)/'test.sqlite3')
        self.core = Core(self.store)

    def test_profile_contains_user_preferences(self):
        prompt = load_prompt()
        for preference in ('British cadence', 'sir', 'Always respond in English',
                           'avoid contractions', 'Daniel', 'understated', 'proactive'):
            self.assertIn(preference, prompt)

    def test_romanian_commands_receive_english_replies(self):
        self.assertIn('Note #1 saved', self.core.handle('memorează: Peștii sunt activi').text)
        self.assertIn('Task #1 created', self.core.handle('task: Verifică filtrul').text)
        self.assertEqual(self.store.memories()[0]['content'], 'Peștii sunt activi')
        self.assertEqual(self.store.tasks()[0]['title'], 'Verifică filtrul')
        for command in ('salut','status','ajutor','personalitate','calendar','gata: -1'):
            self.assertTrue(self.core.handle(command).text.strip())

    def test_english_aliases_and_history(self):
        self.core.handle('remember: important detail')
        self.core.handle('task: check the filter')
        self.assertIn('important detail', self.core.handle('notes all').text)
        self.assertIn('no deadline', self.core.handle('tasks all').text)
        self.assertIn('completed', self.core.handle('done: 1').text)
        self.assertIn('deleted', self.core.handle('forget: 1').text)
        self.assertTrue(self.store.history()[-1]['content'].strip())

    def test_profile_forwarded_and_model_output_never_executed(self):
        calls = []
        class FakeModel:
            def reply(self, text, module, *, system_prompt):
                calls.append((text,module,system_prompt))
                return 'task: do not execute generated text'
        core = Core(self.store, Integrations(llm=FakeModel()))
        result = core.handle('explică acest plan','fishroom')
        self.assertEqual(calls[0], ('explică acest plan','fishroom',load_prompt()))
        self.assertIn('do not execute',result.text)
        self.assertEqual(self.store.tasks(),[])

    def test_missing_model_is_honest(self):
        self.assertIn('not yet connected', self.core.handle('Analyse my strategy').text)
