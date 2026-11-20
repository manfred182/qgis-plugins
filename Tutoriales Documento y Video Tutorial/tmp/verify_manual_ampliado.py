from pathlib import Path
import hashlib
import json
import zipfile
from docx import Document

root = Path(__file__).resolve().parent.parent
docx_path = root / 'output' / 'Manual_QGIS' / 'Manual_QGIS_Instalacion_y_Primeros_Pasos_Ampliado.docx'
document = Document(docx_path)
with zipfile.ZipFile(docx_path) as z:
    assert z.testzip() is None, 'DOCX ZIP integrity failed'
assert len(document.inline_shapes) == 11
assert len(document.tables) == 9
assert len([p for p in document.paragraphs if p.style.name == 'Heading 1']) == 25
current = root / 'tmp' / 'qa' / 'ampliado-2'
previous = root / 'tmp' / 'qa' / 'ampliado-1'
assert len(list(current.glob('page-*.png'))) == 26
assert not list(current.glob('*.pdf'))
assert not list((root / 'output').rglob('*.pdf'))
changed = []
for n in range(1, 27):
    name = f'page-{n}.png'
    old_hash = hashlib.sha256((previous / name).read_bytes()).hexdigest()
    new_hash = hashlib.sha256((current / name).read_bytes()).hexdigest()
    if old_hash != new_hash:
        changed.append(n)
print(json.dumps({'docx_bytes': docx_path.stat().st_size, 'docx_integrity': 'valid', 'pages': 26, 'figures': 11, 'tables': 9, 'pages_changed_since_visual_review': changed, 'pdf_in_output': False}, ensure_ascii=False))
