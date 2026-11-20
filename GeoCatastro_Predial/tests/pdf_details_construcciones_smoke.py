"""Smoke test: FormTerreno/_pdf_details con QGIS real (expresiones reales).

Valida que la ficha PDF (``_pdf_details``) liste las construcciones y
unidades de construccion asociadas al predio consultado (misma CODIGO,
TIPO_UNIDAD = 'CONSTRUCCION'), como en la capa consolidada del merge.
Requiere QGIS real porque usa QgsFeatureRequest con una expresion de
filtro evaluada contra una capa de verdad (no se puede probar con el
stub puro de qgis.core en tests/test_consultas_core.py).
"""
import os
import sys
from pathlib import Path

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
base = Path('C:/Program Files/QGIS 3.44.15')
_dlls = [os.add_dll_directory(str(base / p)) for p in ('bin', 'apps/qt5/bin', 'apps/qgis-ltr/bin')]

from qgis.core import QgsApplication, QgsVectorLayer, QgsFeature, QgsField  # noqa: E402
from qgis.PyQt.QtCore import QVariant  # noqa: E402

app = QgsApplication([], True)
app.initQgis()

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root.parent))
from GeoCatastro_Predial.consultas_dialog import ConsultasPredialesDialog  # noqa: E402

layer = QgsVectorLayer('None', 'Catastro_Consolidado', 'memory')
layer.dataProvider().addAttributes([
    QgsField('CODIGO', QVariant.String),
    QgsField('TIPO_UNIDAD', QVariant.String),
    QgsField('TIPO_CONSTRUCCION', QVariant.String),
    QgsField('IDENTIFICADOR', QVariant.String),
    QgsField('NUMERO_PISOS', QVariant.Int),
])
layer.updateFields()

rows = [
    ('000123', 'PREDIO', '', '', None),
    ('000123', 'CONSTRUCCION', 'CONVENCIONAL', 'A', 2),
    ('000123', 'CONSTRUCCION', 'NO CONVENCIONAL', 'B', 1),
    ('999999', 'CONSTRUCCION', 'CONVENCIONAL', 'A', 3),  # de otro predio: no debe salir
]
features = []
for codigo, tipo_unidad, tipo_c, identificador, pisos in rows:
    feature = QgsFeature(layer.fields())
    feature.setAttributes([codigo, tipo_unidad, tipo_c, identificador, pisos])
    features.append(feature)
layer.dataProvider().addFeatures(features)

predio_feat = next(
    f for f in layer.getFeatures()
    if f['TIPO_UNIDAD'] == 'PREDIO' and f['CODIGO'] == '000123')

instance = ConsultasPredialesDialog.__new__(ConsultasPredialesDialog)
details = instance._pdf_details(predio_feat, layer)
details_dict = dict(details)

assert details_dict.get('Construcciones asociadas') == '2 unidad(es)', details_dict
assert details_dict.get('Unidad A') == 'CONVENCIONAL - 2 piso(s)', details_dict
assert details_dict.get('Unidad B') == 'NO CONVENCIONAL - 1 piso(s)', details_dict
assert 'Construcciones adicionales' not in details_dict, details_dict

# Mismo resultado usando el indice precalculado (ruta real de _export_map_pdf
# cuando se exportan varios predios en un solo PDF).
index = ConsultasPredialesDialog._build_construction_index(layer)
details_indexed = dict(instance._pdf_details(predio_feat, layer, index))
assert details_indexed == details_dict, (details_indexed, details_dict)

# La construccion del otro predio (999999) no debe aparecer en ningun valor.
assert not any('999999' in str(v) for v in details_dict.values()), details_dict

# Una construccion consultada directamente no debe listarse "a si misma".
construccion_feat = next(
    f for f in layer.getFeatures()
    if f['TIPO_UNIDAD'] == 'CONSTRUCCION' and f['IDENTIFICADOR'] == 'A'
    and f['CODIGO'] == '000123')
details_construccion = dict(instance._pdf_details(construccion_feat, layer))
assert 'Construcciones asociadas' not in details_construccion, details_construccion

print('OK: la ficha PDF lista las construcciones/unidades asociadas al predio '
      '(misma CODIGO), excluye las de otros predios y no se auto-lista cuando '
      'el elemento consultado ya es una construccion.')
