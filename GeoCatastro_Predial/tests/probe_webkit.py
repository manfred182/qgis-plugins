import os
from pathlib import Path
_dlls=[os.add_dll_directory(str(p)) for p in [Path('C:/Program Files/QGIS 3.44.12/bin'),Path('C:/Program Files/QGIS 3.44.12/apps/qt5/bin'),Path('C:/Program Files/QGIS 3.44.12/apps/qgis-ltr/bin')]]
from qgis.PyQt.QtWebKitWidgets import QWebView
print('QtWebKit disponible', QWebView)
