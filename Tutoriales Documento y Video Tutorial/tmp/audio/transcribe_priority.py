import os
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
import json
import wave
import argparse
from pathlib import Path
import numpy as np
import torch
import whisper

root = Path(__file__).parent
parser = argparse.ArgumentParser()
parser.add_argument('--start', type=int, default=1620)
parser.add_argument('--end', type=int, default=None)
parser.add_argument('--name', default='transcript_priority_27min')
args = parser.parse_args()
torch.set_num_threads(2)
model = whisper.load_model(str(Path.home() / '.cache' / 'whisper' / 'base.pt'), device='cpu')
with wave.open(str(root / 'audio16k.wav'), 'rb') as wav:
    sr = wav.getframerate()
    wav.setpos(args.start * sr)
    end = min(wav.getnframes(), args.end * sr) if args.end else wav.getnframes()
    samples = np.frombuffer(wav.readframes(end - args.start * sr), dtype=np.int16).astype(np.float32) / 32768.0
result = model.transcribe(samples, language='es', fp16=False, temperature=0, beam_size=1,
                          verbose=False, condition_on_previous_text=False)
for s in result['segments']:
    s['start'] += args.start
    s['end'] += args.start
def stamp(n):
    m, s = divmod(int(n), 60)
    return f'{m:02d}:{s:02d}'
out = '\n'.join(f"[{stamp(s['start'])}-{stamp(s['end'])}] {s['text'].strip()}" for s in result['segments'])
(root / f'{args.name}.txt').write_text(out, encoding='utf-8')
(root / f'{args.name}.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(out, flush=True)
