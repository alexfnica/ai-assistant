import unittest
from jarvis.neural_voice import parameters, VOICE_ID, HUD_ID
from jarvis.voice import preferred_voice


class NeuralVoiceTests(unittest.TestCase):
    def test_default_profile(self):
        self.assertEqual(parameters(-1,85), (1.2,.85))

    def test_bounded_speed_and_volume(self):
        self.assertEqual(parameters(-99,200), parameters(-4,100))
        self.assertEqual(parameters(99,-1), parameters(4,0))
        self.assertGreater(parameters(-4,85)[0], parameters(4,85)[0])

    def test_neural_preferred_over_american_windows(self):
        neural = {'id':VOICE_ID, 'culture':'en-GB', 'gender':'Male'}
        david = {'id':'david', 'culture':'en-US', 'gender':'Male'}
        self.assertEqual(preferred_voice([neural,david]), neural)
        self.assertNotEqual(VOICE_ID, HUD_ID)
