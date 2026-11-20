import json
from pathlib import Path

root = Path(__file__).parent
base = json.loads((root / 'transcript_base.json').read_text(encoding='utf-8'))['segments']
middle = json.loads((root / 'transcript_priority_21_27.json').read_text(encoding='utf-8'))['segments']
tail = json.loads((root / 'transcript_priority_27min.json').read_text(encoding='utf-8'))['segments']
segments = [s for s in base if s['start'] < 1260] + middle + tail
for index, segment in enumerate(segments):
    segment['id'] = index
assert all(segments[i]['start'] <= segments[i + 1]['start'] for i in range(len(segments) - 1))
assert segments[0]['start'] == 0
assert segments[-1]['end'] > 1840

def stamp(n):
    m, s = divmod(int(n), 60)
    return f'{m:02d}:{s:02d}'

metadata = {
    'source': 'Tutorial_1_Instalacion QGIS.mp4',
    'video_duration_seconds': 1847.7333,
    'audio_duration_seconds': 1847.374021,
    'video_size': [1918, 1078],
    'fps': 30,
    'audio_codec': 'AAC LC',
    'audio_sample_rate': 48000,
    'audio_channels': 2,
    'subtitle_streams': 0,
    'transcription': 'Automatic, offline, local Whisper base multilingual model',
    'language': 'es',
    'note': 'Automatic transcription. Proper names, abbreviations and numeric interface values require visual review. Entire audio was processed; no speech was sent to external services.',
    'processed_intervals_seconds': [[0, 1260], [1260, 1620], [1620, 1847.374021]],
    'segment_count': len(segments),
    'segments': segments,
}
(root / 'transcript_complete.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
(root / 'transcript_complete.txt').write_text('\n'.join(f"[{stamp(s['start'])}-{stamp(s['end'])}] {s['text'].strip()}" for s in segments), encoding='utf-8')
print('MERGED', len(segments), 'segments', 'first', segments[0]['start'], 'last_speech_end', segments[-1]['end'])
print('All source audio intervals processed, ordered transcript saved.')
