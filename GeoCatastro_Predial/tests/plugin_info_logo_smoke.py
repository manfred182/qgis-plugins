import os, sys
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
base=Path('C:/Program Files/QGIS 3.44.12')
_dlls=[os.add_dll_directory(str(base/p)) for p in ('bin','apps/qt5/bin','apps/qgis-ltr/bin')]
from qgis.PyQt.QtWidgets import QApplication
from qgis.PyQt.QtCore import QUrl,QEventLoop,QTimer
from qgis.PyQt.QtGui import QFontDatabase
from qgis.PyQt.QtWebKitWidgets import QWebView
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from plugin_info_logo import PluginInfoLogo
app=QApplication([])
for font in ('arial.ttf','arialbd.ttf'):
 QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+font)
view=QWebView();view.setObjectName('wvDetails');view.resize(960,600)
from qgis.PyQt import sip
from qgis.PyQt.QtWidgets import QWidget
wrapped_view=sip.cast(view,QWidget)
icon=root/'icons/consulta_catastral_info.png'
helper=PluginInfoLogo(str(icon))
helper._attach(wrapped_view)
assert len(helper.views)==1
def load(html):
 loop=QEventLoop();view.loadFinished.connect(loop.quit)
 view.setHtml(html);QTimer.singleShot(5000,loop.quit);loop.exec_()
 view.loadFinished.disconnect(loop.quit);app.processEvents()
url=QUrl.fromLocalFile(str(icon)).toString()
other=QUrl.fromLocalFile(str(root/'icons/icon.png')).toString()
load('<html><body style="font-family:Arial"><img src="'+url+'" style="float:right;max-width:64px;max-height:64px;"><h1>GeoCatastro Predial</h1><h3>Consulta catastral</h3><p>Informacion del complemento instalado en QGIS.</p><p>Autor: Jose Orlando Castillo Ospina</p></body></html>')
view.show();app.processEvents();helper.refresh()
element=view.page().mainFrame().findFirstElement('img')
assert element.geometry().width()==256,element.geometry().width()
assert element.geometry().height()==256
(root/'output').mkdir(exist_ok=True)
view.grab().save(str(root/'output/plugin_info_logo_preview.png'))
helper.shutdown();app.processEvents()
assert 'max-width:64px' in element.attribute('style')
helper=PluginInfoLogo(str(icon))
load('<html><body><img src="'+other+'" style="max-width:64px;max-height:64px;"></body></html>')
assert not view.page().mainFrame().findFirstElement('img').hasAttribute('data-geocatastro-original-style')
helper.shutdown()
print('OK: logo 256x256, restauracion al descargar y otros complementos sin cambios.')
