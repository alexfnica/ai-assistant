import unittest
from unittest.mock import patch
from jarvis.natural_voice import parameters, GEORGE, DANIEL, BLEND, synthesize
from jarvis.voice import preferred_voice
from jarvis.natural_voice import available_voices


class NaturalVoiceTests(unittest.TestCase):
    def test_default_is_close_to_normal_speed(self):
        self.assertEqual(parameters(), (.96,.85))

    def test_limits(self):
        self.assertEqual(parameters(99,1000),parameters(4,100))
        self.assertEqual(parameters(-99,-100),parameters(-4,0))
        self.assertLess(parameters(-4)[0],parameters(4)[0])

    def test_input_rejected_before_model_load(self):
        for text in (None,'',' '*3,'a'*8001):
            with self.assertRaises(ValueError):
                synthesize({'voice':GEORGE,'action':'render','text':text})
        with self.assertRaises(ValueError):
            synthesize({'voice':'untrusted','action':'render','text':'hello'})

    def test_distinct_presets_and_default(self):
        self.assertEqual(len({GEORGE,DANIEL,BLEND}),3)
        natural = {'id':GEORGE,'culture':'en-GB','gender':'Male'}
        old = {'id':'piper','culture':'en-GB','gender':'Male'}
        self.assertEqual(preferred_voice([natural,old]),natural)

    def test_installed_inventory_defaults_to_daniel(self):
        with patch('jarvis.natural_voice.sys.version_info', (3,12)), \
             patch('pathlib.Path.is_file', return_value=True), \
             patch('pathlib.Path.stat') as stat:
            stat.return_value.st_size = 400_000_000
            voices = available_voices()
        self.assertEqual(preferred_voice(voices)['id'], DANIEL)
        self.assertEqual({v['id'] for v in voices}, {DANIEL, GEORGE, BLEND})
