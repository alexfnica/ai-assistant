"""Offline Piper subprocess adapter. No uploads or voice cloning."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / 'voice-models' / 'en_GB-northern_english_male-medium.onnx'
VOICE_ID = 'afnica:piper:british-calm'
HUD_ID = 'afnica:piper:british-hud'


def available_voices():
    if sys.version_info[:2] != (3, 12) or not MODEL.is_file() or not Path(str(MODEL)+'.json').is_file():
        return []
    if not (ROOT / 'voice-runtime' / 'piper' / '__init__.py').is_file():
        return []
    return [{'id':VOICE_ID, 'name':'AFNICA · British Calm (local AI)', 'culture':'en-GB', 'gender':'Male'},
            {'id':HUD_ID, 'name':'AFNICA · British HUD (efect discret)', 'culture':'en-GB', 'gender':'Male'}]


def parameters(rate, volume):
    rate = max(-4, min(4, int(rate)))
    volume = max(0, min(100, int(volume)))
    return 1.20 * (1.10 ** (-rate-1)), volume / 100


def worker(request):
    import io
    import wave
    sys.path.insert(0, str(ROOT / 'voice-runtime'))
    import numpy as np
    import onnxruntime
    onnxruntime.disable_telemetry_events()
    from piper import PiperVoice, SynthesisConfig
    if request.get('voice') not in (VOICE_ID, HUD_ID):
        raise ValueError('Voce necunoscută')
    if request.get('action') not in ('speak', 'render'):
        raise ValueError('Acțiune necunoscută')
    text = request.get('text')
    if not isinstance(text, str) or not text.strip() or len(text) > 8000:
        raise ValueError('Text invalid')
    length, volume = parameters(request.get('rate', -1), request.get('volume', 85))
    voice = PiperVoice.load(MODEL)
    config = SynthesisConfig(length_scale=length, noise_scale=.5, noise_w_scale=.65, volume=1)
    chunks = []
    for chunk in voice.synthesize(text, syn_config=config):
        if chunks:
            chunks.append(np.zeros(int(voice.config.sample_rate * .18), dtype=np.float32))
        chunks.append(chunk.audio_float_array)
    samples = np.concatenate(chunks)
    if request['voice'] == HUD_ID:
        delay = int(voice.config.sample_rate * .014)
        dry = samples.copy()
        samples[delay:] += .07 * dry[:-delay]
        samples *= 1 - .025 * np.sin(2*np.pi*35*np.arange(len(samples))/voice.config.sample_rate)
    samples = samples / max(1.0, float(np.max(np.abs(samples)))) * (.90 * volume)
    output = io.BytesIO()
    with wave.open(output, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(voice.config.sample_rate)
        wav.writeframes((samples * 32767).astype('<i2').tobytes())
    if request['action'] == 'render':
        Path(request['path']).write_bytes(output.getvalue())
    else:
        import winsound
        winsound.PlaySound(output.getvalue(), winsound.SND_MEMORY)
    return {'ok':True, 'engine':'piper-local', 'seconds':round(len(samples)/voice.config.sample_rate,2)}


if __name__ == '__main__':
    import json
    try:
        result = worker(json.loads(sys.stdin.read()))
    except Exception:
        result = {'ok':False, 'error':'Vocea AI locală nu a putut fi redată. Verifică ieșirea audio și pachetul Python 3.12; poți selecta o voce Windows.'}
    print(json.dumps(result))
