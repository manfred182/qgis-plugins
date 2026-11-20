from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'tmp' / 'video'
OUT.mkdir(parents=True, exist_ok=True)
FF = Path(r'C:\Users\Jose Castillo Ospina\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-full_build\bin\ffmpeg.exe')
VIDEO = ROOT / 'Tutorial_1_Instalacion QGIS.mp4'
times = list(range(5, 1848, 30))

def extract(t):
    f = OUT / f'frame_{t:04d}.jpg'
    if not f.exists():
        subprocess.run([str(FF), '-hide_banner', '-loglevel', 'error', '-ss', str(t), '-i', str(VIDEO), '-frames:v', '1', '-q:v', '2', '-y', str(f)], check=True)
    return t, f

with ThreadPoolExecutor(max_workers=4) as pool:
    frames = list(pool.map(extract, times))
font = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 24)
for start in range(0, len(frames), 12):
    batch = frames[start:start + 12]
    sheet = Image.new('RGB', (1920, 4 * 390), '#eeeeee')
    d = ImageDraw.Draw(sheet)
    for idx, (t, f) in enumerate(batch):
        im = Image.open(f)
        im.thumbnail((640, 360))
        x, y = (idx % 3) * 640, (idx // 3) * 390
        sheet.paste(im, (x, y + 30))
        d.text((x + 10, y + 2), f'{t//60:02d}:{t%60:02d}', font=font, fill='black')
    target = OUT / f'overview_{start//12+1:02d}.jpg'
    sheet.save(target, quality=88)
    print(target)
