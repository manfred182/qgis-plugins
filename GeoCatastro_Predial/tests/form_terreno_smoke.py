"""Smoke test: FormTerreno con QGIS real (widgets Qt verdaderos).

Valida los cambios al panel de detalle: encabezados sin "(R1)"/"(R2)",
"Registro 2" renombrado a "Informacion Juridica", los campos calculados
de area en hectareas / perimetro en kilometros, la nueva seccion
"Construccion" (TIPO_CONSTRUCCION, IDENTIFICADOR, NUMERO_PISOS, etc.)
tomada directo de la tabla de atributos de la capa consolidada, y que
los combos de dominio (Estrato, Destino economico, Tipo Doc.) se
bloqueen al mostrar un resultado y se desbloqueen con Limpiar.
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
from GeoCatastro_Predial.consultas_dialog import FormTerreno  # noqa: E402

layer = QgsVectorLayer('None', 'Predios', 'memory')
layer.dataProvider().addAttributes([
    QgsField('CODIGO', QVariant.String),
    QgsField('Area Terreno(m2)', QVariant.Double),
    QgsField('SHAPE_Area', QVariant.Double),
    QgsField('SHAPE_Length', QVariant.Double),
    QgsField('TIPO_CONSTRUCCION', QVariant.String),
    QgsField('IDENTIFICADOR', QVariant.String),
    QgsField('NUMERO_PISOS', QVariant.Int),
    QgsField('ORIGEN', QVariant.String),
])
layer.updateFields()
feature = QgsFeature(layer.fields())
feature.setAttributes([
    '000123', 523591.0, 523591.3561, 3106.5524, 'CONVENCIONAL', 'A', 2,
    'RURAL_INFORMAL'])
layer.dataProvider().addFeatures([feature])
feat = next(layer.getFeatures())

form = FormTerreno()

# Los titulos de seccion son QLabel con texto "<ARROW> <titulo>"; se validan
# recorriendo los hijos directos del formulario.
from qgis.PyQt.QtWidgets import QLabel
headers = [w.text() for w in form.findChildren(QLabel) if w.text().startswith('\u25b8')]
assert any('Propietario' == h[2:] for h in headers), headers
assert not any('(R1)' in h for h in headers), headers
assert not any('(R2)' in h for h in headers), headers
assert any(h[2:] == 'Informacion Juridica' or h[2:] == 'Información Jurídica' for h in headers), headers
assert any(h[2:] == 'Áreas' for h in headers), headers
assert any(h[2:] == 'Construcción' for h in headers), headers

form.fill_from_feature(feat, layer)

assert form.f['TIPO_CONSTRUCCION'].text() == 'CONVENCIONAL', form.f['TIPO_CONSTRUCCION'].text()
assert form.f['IDENTIFICADOR'].text() == 'A', form.f['IDENTIFICADOR'].text()
assert form.f['NUMERO_PISOS'].text() == '2', form.f['NUMERO_PISOS'].text()
assert form.f['TIPO_DOMINIO'].text() == '', form.f['TIPO_DOMINIO'].text()
assert form.f['CONDICION_PREDIO'].text() == 'Informal', form.f['CONDICION_PREDIO'].text()
assert form.f['CONDICION_PREDIO'].isReadOnly()

assert form.f['Area Terreno(m2)'].text() == '523.591,00', form.f['Area Terreno(m2)'].text()
assert form.f['Area Terreno(ha)'].text() == '52,3591', form.f['Area Terreno(ha)'].text()
assert form.f['SHAPE_Area'].text() == '523.591,3561', form.f['SHAPE_Area'].text()
assert form.f['SHAPE_Area_ha'].text() == '52,3591', form.f['SHAPE_Area_ha'].text()
assert form.f['SHAPE_Length'].text() == '3.106,5524', form.f['SHAPE_Length'].text()
assert form.f['SHAPE_Length_km'].text() == '3,1066', form.f['SHAPE_Length_km'].text()
assert form.f['Area Terreno(ha)'].isReadOnly()
assert form.f['SHAPE_Area_ha'].isReadOnly()
assert form.f['SHAPE_Length_km'].isReadOnly()

# Al mostrar un resultado, los combos de dominio quedan bloqueados (no se
# deben poder abrir/cambiar mientras solo se esta consultando).
assert not form.f['TipoDoc_cbo'].isEnabled()
assert not form.f['DestinoEc_cbo'].isEnabled()
assert not form.f['Estrato_cbo'].isEnabled()

expr, not_found = form.build_expression(layer)
assert 'TIPO_CONSTRUCCION' in expr, expr
assert 'IDENTIFICADOR' in expr, expr
assert not_found == [], not_found

form.clear()
assert form.f['Area Terreno(ha)'].text() == ''
assert form.f['SHAPE_Length_km'].text() == ''
assert form.f['TIPO_CONSTRUCCION'].text() == ''
assert form.f['IDENTIFICADOR'].text() == ''

# Limpiar = nueva busqueda: los combos vuelven a ser editables como filtro.
assert form.f['TipoDoc_cbo'].isEnabled()
assert form.f['DestinoEc_cbo'].isEnabled()
assert form.f['Estrato_cbo'].isEnabled()

print('OK: encabezados renombrados (sin R1/R2, "Informacion Juridica"), '
      'areas/perimetro calculados en ha/km, la seccion "Construccion" '
      '(tomada de la tabla de atributos de la capa) se muestran, filtran y '
      'limpian correctamente, y los combos de dominio se bloquean/'
      'desbloquean segun corresponda.')
