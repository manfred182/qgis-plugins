import os, sys
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
_dll_handles = [os.add_dll_directory(str(p)) for p in (Path('C:/Program Files/QGIS 3.44.15/bin'), Path('C:/Program Files/QGIS 3.44.15/apps/qt5/bin'), Path('C:/Program Files/QGIS 3.44.15/apps/qgis-ltr/bin'))]
from qgis.core import QgsApplication,QgsVectorLayer,QgsFeature,QgsGeometry,QgsProject
app=QgsApplication([],False)
app.initQgis()
from qgis.PyQt.QtGui import QFontDatabase
for font in ('arial.ttf','arialbd.ttf'):
 QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+font)
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from map_pdf_export import export_predial_selection_pdf
layer=QgsVectorLayer('Polygon?crs=EPSG:4326','Predios de prueba','memory')
records=[]
for i in range(2):
 x=-75.7+i*.003
 f=QgsFeature(); f.setGeometry(QgsGeometry.fromWkt(f'POLYGON(({x} 1.6,{x+.002} 1.6,{x+.002} 1.602,{x} 1.602,{x} 1.6))'))
 layer.dataProvider().addFeatures([f])
for f in layer.getFeatures():
 records.append((f.id(), [('Codigo predial',str(f.id()).zfill(30)),('Propietario','Propietario de prueba'),('Manzana o vereda','001 / Vereda de prueba'),('Area de terreno','45.000 m2')]))
QgsProject.instance().addMapLayer(layer)
out=Path(__file__).resolve().parents[1]/'output/pdf/ejemplo_consulta_vereda.pdf'
result=export_predial_selection_pdf(None,layer,records,str(out),overview=True)
assert result['page_count']==3,result
assert result['feature_ids']==[r[0] for r in records]
print(result)
# Also verify transformation from a projected layer.
from qgis.core import QgsCoordinateTransform,QgsCoordinateReferenceSystem
projected=QgsVectorLayer('Polygon?crs=EPSG:3116','Proyectada','memory')
for source in layer.getFeatures():
 g=source.geometry(); g.transform(QgsCoordinateTransform(layer.crs(),projected.crs(),QgsProject.instance()))
 f=QgsFeature(); f.setGeometry(g); projected.dataProvider().addFeatures([f])
ids=[f.id() for f in projected.getFeatures()]
export_predial_selection_pdf(None,projected,[(ids[0],records[0][1])],str(out.parent/'prueba_proyectada.pdf'))
print('PDF geographic and projected smoke OK')
