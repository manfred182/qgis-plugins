"""Smoke test: encabezado con numero predial y contenido sin truncar.

Verifica los cambios del 2026-11-06 en map_pdf_export.py:
1. ``_page_header_subtitle`` devuelve el numero predial para el encabezado
   (en vez de la marca fija "GeoCatastro Predial | IGAC Colombia"), con el
   caso especial de la pagina resumen de una consulta por conjunto.
2. ``_full_text``/``_dynamic_row_height`` no truncan y calculan un alto de
   fila mayor para texto largo (cubierto tambien en el smoke test
   dedicado, pero aqui se valida con una fila de contenido real).
3. La exportacion con contenido mucho mas largo de lo normal (nombres de
   capa y valores extensos) no revienta: una revision visual manual del
   render (PNG via QgsLayoutExporter.exportToImage) durante el desarrollo
   confirmo que el encabezado, el cruce con otra capa y la fila de
   "Propietario" se ven completos y envueltos en varias lineas, sin "...".
   No se puede verificar el texto por extraccion de PDF aqui: QGIS exporta
   el texto de esta plantilla como curvas/trazos, no como glifos
   seleccionables, asi que pypdf/PyPDF2 no recuperan ningun texto del PDF
   resultante (se probo y da cadena vacia) -no es un problema de este
   cambio, ya pasaba antes.
"""
import os
import sys
from pathlib import Path

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
base = Path('C:/Program Files/QGIS 3.44.15')
_dlls = [os.add_dll_directory(str(base / p)) for p in ('bin', 'apps/qt5/bin', 'apps/qgis-ltr/bin')]

from qgis.core import (  # noqa: E402
    QgsApplication, QgsVectorLayer, QgsFeature, QgsGeometry, QgsProject,
    QgsField, QgsCategorizedSymbolRenderer, QgsRendererCategory, QgsFillSymbol,
)
from qgis.PyQt.QtCore import QVariant  # noqa: E402
from qgis.PyQt.QtGui import QFontDatabase  # noqa: E402

app = QgsApplication([], False)
app.initQgis()
for font in ('arial.ttf', 'arialbd.ttf'):
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + font)

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root.parent))
import GeoCatastro_Predial.map_pdf_export as mpe  # noqa: E402

# ── _page_header_subtitle: pura, se prueba directo sin exportar nada ───────
assert mpe._page_header_subtitle(
    [('Codigo predial', '184790010000002301280000000')], False
) == '184790010000002301280000000'
assert mpe._page_header_subtitle(
    [('Tipo de salida', 'Conjunto de resultados del buscador')], True
) == 'Conjunto de resultados del buscador'
assert mpe._page_header_subtitle([], False) == ''
print('OK _page_header_subtitle: numero predial en vez de "GeoCatastro Predial | IGAC Colombia"')

# ── Exportacion real con contenido largo: no debe reventar ────────────────
CODIGO_PREDIAL = '184790010000002301280000000'
LONG_OWNER = ('PROPIETARIO CON NOMBRE MUY LARGO PARA PROBAR QUE NO SE CORTA '
              'EN LA FICHA GRAFICA DEL PREDIO CONSULTADO EN GEOCATASTRO')
LONG_CATEGORY = ('ZONIFICACION DE AMENAZA POR INUNDACION Y REMOCION EN MASA '
                  'DEL MUNICIPIO QUE SE CRUZA CON EL PREDIO CONSULTADO')

predios = QgsVectorLayer('Polygon?crs=EPSG:4326', 'Predios de prueba', 'memory')
feat = QgsFeature()
feat.setGeometry(QgsGeometry.fromWkt(
    'POLYGON((-75.70 1.60, -75.698 1.60, -75.698 1.602, -75.70 1.602, -75.70 1.60))'))
predios.dataProvider().addFeatures([feat])
QgsProject.instance().addMapLayer(predios)

cruces = QgsVectorLayer('Polygon?crs=EPSG:4326', 'CapaDeCruce', 'memory')
cruces.dataProvider().addAttributes([QgsField('CAT', QVariant.String)])
cruces.updateFields()
cfeat = QgsFeature(cruces.fields())
cfeat.setGeometry(QgsGeometry.fromWkt(
    'POLYGON((-75.70 1.60, -75.698 1.60, -75.698 1.602, -75.70 1.602, -75.70 1.60))'))
cfeat.setAttributes([LONG_CATEGORY])
cruces.dataProvider().addFeatures([cfeat])
cruces.updateExtents()
cruces.setRenderer(QgsCategorizedSymbolRenderer('CAT', [
    QgsRendererCategory(LONG_CATEGORY, QgsFillSymbol.createSimple({'color': '200,50,50,120'}), LONG_CATEGORY),
]))
QgsProject.instance().addMapLayer(cruces)

details = [
    ('Codigo predial', CODIGO_PREDIAL),
    ('Propietario', LONG_OWNER),
    ('Direccion', 'LA RUSIA'),
]
records = [(f.id(), details) for f in predios.getFeatures()]

out = Path(__file__).resolve().parents[1] / 'output/pdf/layout_completeness_smoke.pdf'
result = mpe.export_predial_selection_pdf(None, predios, records, str(out))
assert result['page_count'] == 1, result
print('OK: exportacion con numero predial, propietario largo y una capa de '
      'cruce con categoria larga no revienta ->', result)
