import os
import json
import time
import wave
from pathlib import Path

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
import numpy as np
import torch
import whisper

root = Path(__file__).parent
torch.set_num_threads(4)
start = time.time()
model = whisper.load_model(str(Path.home() / '.cache' / 'whisper' / 'base.pt'), device='cpu')
print('MODEL_LOADED', round(time.time() - start, 1), flush=True)
with wave.open(str(root / 'audio16k.wav'), 'rb') as wav:
    sr = wav.getframerate()
    samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
segments = []

def stamp(seconds):
    minutes, seconds = divmod(int(seconds), 60)
    return f'{minutes:02d}:{seconds:02d}'

for chunk_index, offset in enumerate(range(0, len(samples), sr * 180)):
    offset_seconds = offset / sr
    chunk_start = time.time()
    result = model.transcribe(samples[offset:offset + sr * 180], language='es', fp16=False,
                              temperature=0, beam_size=3, verbose=False,
                              condition_on_previous_text=False)
    for segment in result['segments']:
        segment['start'] += offset_seconds
        segment['end'] += offset_seconds
        segment['id'] = len(segments)
        segments.append(segment)
        print(f"[{stamp(segment['start'])}-{stamp(segment['end'])}] {segment['text'].strip()}", flush=True)
    (root / 'transcript_base.json').write_text(json.dumps({'language': 'es', 'segments': segments}, ensure_ascii=False, indent=2), encoding='utf-8')
    (root / 'transcript_base.txt').write_text('\n'.join(f"[{stamp(s['start'])}-{stamp(s['end'])}] {s['text'].strip()}" for s in segments), encoding='utf-8')
    print('CHUNK_DONE', chunk_index, round(offset_seconds, 1), 'seconds_compute', round(time.time() - chunk_start, 1), flush=True)
print('TRANSCRIPTION_DONE', round(time.time() - start, 1), flush=True)
