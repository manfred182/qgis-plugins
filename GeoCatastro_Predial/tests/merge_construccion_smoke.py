"""Smoke test: consolidacion de Terrenos + Construcciones en UNA sola capa.

Valida el diseno final: una sola capa de memoria combina predios (terrenos)
y construcciones, con TIPO_UNIDAD/CLASE para la categorizacion, un unico
join de R1/R2 y un unico guardado a shapefile.
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
base = Path('C:/Program Files/QGIS 3.44.15')
_dlls = [os.add_dll_directory(str(base / p)) for p in ('bin', 'apps/qt5/bin', 'apps/qgis-ltr/bin')]

from qgis.core import (  # noqa: E402
    QgsApplication, QgsProject, QgsVectorLayer, QgsFeature, QgsField,
    QgsGeometry, QgsCategorizedSymbolRenderer,
)
from qgis.PyQt.QtCore import QVariant  # noqa: E402
from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox  # noqa: E402

app = QgsApplication([], False)
app.initQgis()

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root.parent))
from GeoCatastro_Predial import merge_dialog as md  # noqa: E402
from GeoCatastro_Predial.consultas_dialog import resolve_field  # noqa: E402

project = QgsProject.instance()


def _memory_layer(name, codigo, wkt):
    layer = QgsVectorLayer('Polygon?crs=EPSG:4326', name, 'memory')
    layer.dataProvider().addAttributes([QgsField('CODIGO', QVariant.String)])
    layer.updateFields()
    feature = QgsFeature(layer.fields())
    feature.setAttributes([codigo])
    feature.setGeometry(QgsGeometry.fromWkt(wkt))
    layer.dataProvider().addFeatures([feature])
    return layer


def _table(name, rows):
    table = QgsVectorLayer('None', name, 'memory')
    table.dataProvider().addAttributes(
        [QgsField('CODIGO', QVariant.String), QgsField('Nombre', QVariant.String)])
    table.updateFields()
    feats = []
    for codigo, nombre in rows:
        feature = QgsFeature(table.fields())
        feature.setAttributes([codigo, nombre])
        feats.append(feature)
    table.dataProvider().addFeatures(feats)
    return table


urb = _memory_layer('U_TERRENO', '000123', 'POLYGON((0 0,1 0,1 1,0 1,0 0))')
rur = _memory_layer('R_TERRENO', '000456', 'POLYGON((2 0,3 0,3 1,2 1,2 0))')
constr_urb = _memory_layer(
    'U_CONSTRUCCION', '000123', 'POLYGON((0.2 0.2,0.4 0.2,0.4 0.4,0.2 0.4,0.2 0.2))')
constr_rur = _memory_layer(
    'R_CONSTRUCCION', '000456', 'POLYGON((2.2 0.2,2.4 0.2,2.4 0.4,2.2 0.4,2.2 0.2))')

r1 = _table('R1', [('000123', 'Jose Perez'), ('000456', 'Ana Gomez')])
r2 = _table('R2', [('000123', 'Matricula A'), ('000456', 'Matricula B')])


class _Combo:
    def __init__(self, value=None):
        self._value = value

    def currentData(self):
        return self._value

    def text(self):
        return self._value or ''


dialog = md.MergeConsolidacionDialog.__new__(md.MergeConsolidacionDialog)
dialog.log = []
dialog._info = lambda msg: dialog.log.append(msg)


class _Progress:
    def setValue(self, value):
        pass


dialog.progress = _Progress()
dialog.iface = None
dialog.cbo_ver_cod_v = _Combo(None)
dialog.cbo_ver_nom_v = _Combo(None)
dialog.cbo_manz_cod_m = _Combo(None)
dialog.inp_pre_r1 = _Combo('R1_')
dialog.inp_pre_r2 = _Combo('R2_')


def _source_group():
    class _Group:
        def addLayer(self, layer):
            pass

    return _Group()


def _add_source_layer(layer, group):
    project.addMapLayer(layer, False)


dialog._source_group = _source_group
dialog._add_source_layer = _add_source_layer

combined = (
    [(urb, 'URBANO', 'PREDIO'), (rur, 'RURAL', 'PREDIO')]
    + [(constr_urb, 'URBANO', 'CONSTRUCCION'), (constr_rur, 'RURAL', 'CONSTRUCCION')])

consolidated = dialog._build_consolidated(combined, None, None, 'Catastro_Consolidado')
assert consolidated.featureCount() == 4, 'deben entrar los 2 predios + 2 construcciones'

clase_field = resolve_field(consolidated, 'CLASE') or 'CLASE'
tipo_field = resolve_field(consolidated, 'TIPO_UNIDAD') or 'TIPO_UNIDAD'
clases = {feat[clase_field] for feat in consolidated.getFeatures()}
tipos = {feat[tipo_field] for feat in consolidated.getFeatures()}
assert clases == {'PREDIO_URBANO', 'PREDIO_RURAL', 'CONSTRUCCION_URBANO', 'CONSTRUCCION_RURAL'}, clases
assert tipos == {'PREDIO', 'CONSTRUCCION'}, tipos

# Capa "distractora" ya presente y activa en el proyecto antes de consolidar,
# para probar que la nueva capa no depende del punto de insercion ambiente de
# QGIS (que normalmente sigue a la capa/grupo seleccionado en el panel).
distractor = _memory_layer('Capa_Previa_Activa', '999999', 'POLYGON((9 9,10 9,10 10,9 10,9 9))')
project.addMapLayer(distractor)

consolidated.setRenderer(dialog._build_catastro_renderer())
assert isinstance(consolidated.renderer(), QgsCategorizedSymbolRenderer)
assert len(consolidated.renderer().categories()) == 8
dialog._add_layer_at_root(consolidated)
consolidated_id = consolidated.id()

root_children = project.layerTreeRoot().children()
assert root_children[0].layerId() == consolidated_id, (
    'La capa consolidada (temporal) debe quedar de primera en el panel de capas, '
    f'sin importar la capa activa previa; orden actual: {[c.name() for c in root_children]}')

r1_normalized, r1_keys = dialog._build_normalized_join_table(r1, 'CODIGO', 'R1')
r2_normalized, r2_keys = dialog._build_normalized_join_table(r2, 'CODIGO', 'R2')
project.addMapLayer(r1_normalized, False)
project.addMapLayer(r2_normalized, False)

dialog._attach_join(consolidated, r1_normalized, md._JOIN_KEY, md._JOIN_KEY, 'R1_', 'R1', r1_keys)
dialog._attach_join(consolidated, r2_normalized, md._JOIN_KEY, md._JOIN_KEY, 'R2_', 'R2', r2_keys)

folder = Path(tempfile.mkdtemp(prefix='geocatastro_constr_'))
target_path = str(folder / 'Catastro_Consolidado.shp')


def _fake_get_save_file_name(parent, caption, directory, file_filter):
    return target_path, file_filter


QFileDialog.getSaveFileName = staticmethod(_fake_get_save_file_name)
QMessageBox.information = staticmethod(lambda *a, **k: None)
QMessageBox.warning = staticmethod(lambda *a, **k: None)

saved = dialog._offer_save_consolidated(
    consolidated, default_filename='Catastro_Consolidado.shp')
assert saved.providerType() == 'ogr'
assert not saved.vectorJoins()

names = {feat[resolve_field(saved, 'Nombre')] for feat in saved.getFeatures()}
assert names == {'Jose Perez', 'Ana Gomez'}, names
saved_clases = {feat[resolve_field(saved, 'CLASE')] for feat in saved.getFeatures()}
assert saved_clases == {'PREDIO_URBANO', 'PREDIO_RURAL', 'CONSTRUCCION_URBANO', 'CONSTRUCCION_RURAL'}, saved_clases

# La capa temporal debe haber desaparecido sola al guardar...
assert project.mapLayer(consolidated_id) is None, (
    'La capa temporal debe desaparecer automáticamente al guardar')
# ...y la capa final (shapefile) debe seguir de primera en el panel...
root_children = project.layerTreeRoot().children()
assert root_children[0].layerId() == saved.id(), (
    'La capa guardada debe quedar de primera en el panel de capas; '
    f'orden actual: {[c.name() for c in root_children]}')
# ...y seguir categorizada (el renderer se clona al guardar como shapefile).
assert isinstance(saved.renderer(), QgsCategorizedSymbolRenderer), (
    'La capa guardada debe conservar la simbología categorizada')
assert len(saved.renderer().categories()) == 8

print('OK: capa consolidada queda de primera en el panel (ignorando la capa activa '
      'previa), se activa sola, el temporal desaparece al guardar y la capa final '
      'sigue categorizada con R1/R2 materializados.')
