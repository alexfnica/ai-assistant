import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from jarvis.storage import Store
from jarvis.holo_server import HoloServer


class HoloTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / 'test.sqlite3')
        self.server = HoloServer(('127.0.0.1', 0), self.store)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self, route, body=None, auth=True, extra=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        headers = {'X-Jarvis-Token': self.server.token} if auth else {}
        if body is not None:
            headers['Content-Type'] = 'application/json'
        headers.update(extra or {})
        conn.request('GET' if body is None else 'POST', route,
                     None if body is None else json.dumps(body), headers)
        result = conn.getresponse()
        status, data, response_headers = result.status, result.read(), dict(result.getheaders())
        conn.close()
        return status, data, response_headers

    def command(self, text, key='unique-request-1'):
        return self.request('/api/command', {'text': text, 'module': 'fishroom', 'request_id': key})

    def test_full_task_flow_and_persistence(self):
        self.assertEqual(self.command('task: Verifică filtrul')[0], 200)
        tree = json.loads(self.request('/api/tree')[1])
        self.assertEqual(len(tree), 5)
        folder = next(x for x in tree if x['module'] == 'fishroom')
        self.assertEqual(folder['files'][0]['title'], 'Verifică filtrul')
        self.assertEqual(len(Store(self.store.path).tasks()), 1)
        self.assertEqual(self.command('gata: 1', 'unique-request-2')[0], 200)
        self.assertEqual(Store(self.store.path).tasks(), [])

    def test_idempotency(self):
        first = self.command('task: Test')
        self.assertEqual(self.command('task: Test')[1], first[1])
        self.assertEqual(len(self.store.tasks()), 1)
        self.assertEqual(self.command('task: Altceva')[0], 409)

    def test_security_boundary(self):
        self.assertEqual(self.request('/api/tree', auth=False)[0], 403)
        self.assertEqual(self.request('/api/tree', extra={'Origin': 'https://evil.example'})[0], 403)
        self.assertEqual(self.request('/', extra={'Host': 'evil.example'})[0], 403)
        for path in ['/data/jarvis.sqlite3', '/jarvis/core.py', '/vendor/../../jarvis/core.py']:
            self.assertEqual(self.request(path)[0], 404)

    def test_page_and_assets(self):
        status, body, headers = self.request('/', auth=False)
        self.assertEqual(status, 200)
        self.assertIn(self.server.token.encode(), body)
        self.assertIn("connect-src 'self'", headers['Content-Security-Policy'])
        self.assertEqual(self.request('/vendor/three.module.js')[0], 200)
        self.assertIn('javascript', self.request('/vendor/vision_bundle.mjs')[2]['Content-Type'])

    def test_gestures_never_execute_commands(self):
        self.assertEqual(self.request('/api/state', {'event': 'task: unsafe', 'card': 'x'})[0], 200)
        self.assertEqual(self.store.tasks(), [])
        self.assertEqual(self.store.history(), [])

    def test_invalid_command_and_voice_disabled(self):
        self.assertEqual(self.command(None)[0], 400)
        self.assertEqual(json.loads(self.request('/api/voice')[1])['state'], 'disabled')
        self.assertEqual(self.request('/api/command', [1, 2])[0], 400)


if __name__ == '__main__':
    unittest.main()
