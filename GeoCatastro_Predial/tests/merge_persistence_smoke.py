import os, sys, tempfile
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
base=Path('C:/Program Files/QGIS 3.44.12')
_dlls=[os.add_dll_directory(str(base/p)) for p in ('bin','apps/qt5/bin','apps/qgis-ltr/bin')]
from qgis.core import QgsApplication,QgsProject,QgsVectorLayer,QgsFeature,QgsField,QgsGeometry,QgsVectorLayerJoinInfo,QgsFillSymbol,QgsSingleSymbolRenderer
from qgis.PyQt.QtCore import QVariant
app=QgsApplication([],False);app.initQgis()
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root.parent))
from GeoCatastro_Predial.merge_persistence import save_consolidated
from GeoCatastro_Predial.consultas_dialog import resolve_field
project=QgsProject.instance()
layer=QgsVectorLayer('Polygon?crs=EPSG:4326','Merge','memory')
layer.dataProvider().addAttributes([QgsField('CODIGO',QVariant.String),QgsField('MANZANA_VEREDA_CODIGO',QVariant.String)])
layer.updateFields()
f=QgsFeature(layer.fields());f.setAttributes(['000123','001']);f.setGeometry(QgsGeometry.fromWkt('POLYGON((0 0,1 0,1 1,0 1,0 0))'));layer.dataProvider().addFeatures([f])
table=QgsVectorLayer('None','R1','memory');table.dataProvider().addAttributes([QgsField('CODIGO',QVariant.String),QgsField('Nombre',QVariant.String)]);table.updateFields()
f=QgsFeature(table.fields());f.setAttributes(['000123','José Pérez']);table.dataProvider().addFeatures([f]);project.addMapLayer(table)
j=QgsVectorLayerJoinInfo();j.setJoinLayer(table);j.setJoinFieldName('CODIGO');j.setTargetFieldName('CODIGO');j.setPrefix('R1_');layer.addJoin(j)
layer.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({'style':'no','outline_style':'solid','outline_color':'0,0,0,255','outline_width':'1','outline_width_unit':'MM'})))
folder=Path(tempfile.mkdtemp(prefix='geocatastro_shp_'))
saved, omissions, path=save_consolidated(layer,str(folder/'merge.shp'),table)
assert saved.providerType()=='ogr' and not saved.vectorJoins()
assert next(saved.getFeatures())[resolve_field(saved,'Nombre')]=='José Pérez'
assert next(saved.getFeatures())[resolve_field(saved,'VEREDA_CODIGO')]=='001'
assert omissions.featureCount()==1
for output in (saved,omissions):
 message,ok=output.saveNamedStyle(str(Path(output.source()).with_suffix('.qml')));assert ok,message
project.clear();project.addMapLayer(saved);project.addMapLayer(omissions)
project.setFileName(str(folder/'proyecto.qgz'));assert project.write()
project.clear();assert project.read(str(folder/'proyecto.qgz'))
restored=next(x for x in project.mapLayers().values() if x.name()=='Merge')
assert restored.isValid() and restored.featureCount()==1
assert next(restored.getFeatures())[resolve_field(restored,'Nombre')]=='José Pérez'
props=restored.renderer().symbol().symbolLayer(0).properties()
assert props['style']=='no' and float(props['outline_width'])==1 and props['outline_width_unit']=='MM',props
assert props['outline_color'].startswith('0,0,0,255'),props
try:save_consolidated(restored,path)
except ValueError:pass
else:raise AssertionError('No protege archivos existentes')
print('OK: SHP y DBF, joins materializados, busqueda con alias, proyecto reabierto, estilo sin relleno negro 1 mm y proteccion de archivos existentes.')
