"""Local Kokoro voices: no reference upload, voice cloning, or audio effects."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ROOT / 'voice-natural-runtime'
MODEL_DIR = ROOT / 'voice-models' / 'kokoro'
GEORGE = 'afnica:kokoro:george'
DANIEL = 'afnica:kokoro:daniel'
BLEND = 'afnica:kokoro:blend'
VOICE_IDS = (GEORGE, DANIEL, BLEND)


def available_voices():
    if sys.version_info[:2] != (3, 12):
        return []
    if not all(p.is_file() for p in (RUNTIME/'kokoro_onnx'/'__init__.py',
                                   MODEL_DIR/'kokoro-v1.0.onnx', MODEL_DIR/'voices-v1.0.bin')):
        return []
    if (MODEL_DIR/'kokoro-v1.0.onnx').stat().st_size < 300_000_000 or (MODEL_DIR/'voices-v1.0.bin').stat().st_size < 20_000_000:
        return []
    return [{'id':key, 'name':name, 'culture':'en-GB', 'gender':'Male'} for key, name in (
        (DANIEL, 'AFNICA · Natural British Daniel'),
        (GEORGE, 'AFNICA · Natural British George'),
        (BLEND, 'AFNICA · Natural British Blend'))]


def parameters(rate=-1, volume=85):
    rate = max(-4, min(4, int(rate)))
    return max(.7, min(1.3, .96 * (1.06 ** (rate + 1)))), max(0, min(100, int(volume))) / 100


def synthesize(request):
    """Return WAV bytes. Separate process keeps Stop responsive during inference."""
    import io
    import wave
    if request.get('voice') not in VOICE_IDS:
        raise ValueError('Voce necunoscută')
    text = request.get('text')
    if not isinstance(text, str) or not text.strip() or len(text) > 8000:
        raise ValueError('Text invalid')
    if request.get('action') not in ('render','speak'):
        raise ValueError('Acțiune invalidă')
    sys.path.insert(0, str(RUNTIME))
    import numpy as np
    import onnxruntime as ort
    ort.disable_telemetry_events()
    from kokoro_onnx import Kokoro
    options = ort.SessionOptions()
    options.intra_op_num_threads = 4
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(MODEL_DIR/'kokoro-v1.0.onnx'),
                                   sess_options=options, providers=['CPUExecutionProvider'])
    engine = Kokoro.from_session(session, str(MODEL_DIR/'voices-v1.0.bin'))
    key = request['voice']
    voice = 'bm_george' if key == GEORGE else 'bm_daniel'
    if key == BLEND:
        voice = .7 * engine.get_voice_style('bm_george') + .3 * engine.get_voice_style('bm_daniel')
    speed, volume = parameters(request.get('rate',-1), request.get('volume',85))
    samples, sr = engine.create(text, voice=voice, speed=speed, lang='en-gb')
    if not len(samples) or not np.all(np.isfinite(samples)):
        raise ValueError('Audio invalid')
    samples = samples / max(1.,float(np.max(np.abs(samples)))) * (.92 * volume)
    result = io.BytesIO()
    with wave.open(result,'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sr)
        wav.writeframes((samples*32767).astype('<i2').tobytes())
    return result.getvalue(), {'ok':True,'engine':'kokoro-local','seconds':round(len(samples)/sr,2)}


def worker(request):
    data, result = synthesize(request)
    if request['action'] == 'render':
        Path(request['path']).write_bytes(data)
    else:
        import winsound
        winsound.PlaySound(data, winsound.SND_MEMORY)
    return result


if __name__ == '__main__':
    import json
    try:
        result = worker(json.loads(sys.stdin.read()))
    except Exception:
        result = {'ok':False, 'error':'Vocea Kokoro locală nu a putut fi generată sau redată. Verifică modelul, runtime-ul Python 3.12 și ieșirea audio. Vocile anterioare rămân disponibile.'}
    print(json.dumps(result))
