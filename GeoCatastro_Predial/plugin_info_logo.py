"""Amplia solamente el logo local de este complemento en su ficha de QGIS.

QGIS no ofrece un tamano configurable en metadata.txt. Este adaptador actua
sobre el visor HTML mientras el complemento esta activo, sin modificar QGIS.
"""
import os
from qgis.PyQt.QtCore import QObject, QEvent, QUrl, QTimer
from qgis.PyQt.QtWidgets import QApplication


class PluginInfoLogo(QObject):
    SIZE = 256

    def __init__(self, icon_path, parent=None):
        super().__init__(parent)
        self.icon_path = os.path.normcase(os.path.abspath(icon_path))
        self.views = []
        self.enabled = True
        QApplication.instance().installEventFilter(self)
        for widget in QApplication.allWidgets():
            self._attach(widget)

    def eventFilter(self, watched, event):
        if self.enabled and event.type() == QEvent.Show:
            self._attach(watched)
        return False

    def _attach(self, view):
        if view.objectName() != 'wvDetails':
            return
        # QgsWebView creado por C++ puede llegar a Python como QWidget.
        # Recuperar la clase Qt real antes de consultar sus senales.
        if view.inherits('QWebView'):
            from qgis.PyQt import sip
            from qgis.PyQt.QtWebKitWidgets import QWebView
            view = sip.cast(view, QWebView)
        from qgis.PyQt import sip
        for attached in list(self.views):
            if sip.isdeleted(attached):
                self.views.remove(attached)
            elif sip.unwrapinstance(attached) == sip.unwrapinstance(view):
                return
        if not hasattr(view, 'loadFinished') or not hasattr(view, 'page'):
            return
        self.views.append(view)
        view.loadFinished.connect(self.refresh)
        view.page().mainFrame().contentsSizeChanged.connect(self.refresh)
        QTimer.singleShot(0, self.refresh)

    def _images(self, view):
        frame = view.page().mainFrame()
        for element in frame.findAllElements('img'):
            path = QUrl(element.attribute('src').replace('\\', '/')).toLocalFile()
            if path and os.path.normcase(os.path.abspath(path)) == self.icon_path:
                yield element

    def refresh(self, *args):
        if not self.enabled:
            return
        for view in list(self.views):
            try:
                for element in self._images(view):
                    if element.attribute('data-geocatastro-expanded') == 'true':
                        continue
                    if not element.hasAttribute('data-geocatastro-original-style'):
                        element.setAttribute('data-geocatastro-original-style', element.attribute('style'))
                    element.setAttribute('data-geocatastro-expanded', 'true')
                    element.setAttribute('style',
                        'float:right;width:256px;height:256px;max-width:256px;'
                        'max-height:256px;margin:0 0 12px 20px;')
            except RuntimeError:
                self.views.remove(view)
            except AttributeError:
                # Visores de QGIS sin QtWebKit conservan el icono estandar.
                pass

    def shutdown(self):
        self.enabled = False
        QApplication.instance().removeEventFilter(self)
        for view in self.views:
            try:
                view.loadFinished.disconnect(self.refresh)
                view.page().mainFrame().contentsSizeChanged.disconnect(self.refresh)
                for element in self._images(view):
                    if element.hasAttribute('data-geocatastro-original-style'):
                        element.setAttribute('style', element.attribute('data-geocatastro-original-style'))
                        element.removeAttribute('data-geocatastro-original-style')
                        element.removeAttribute('data-geocatastro-expanded')
            except (RuntimeError, TypeError, AttributeError):
                pass
        self.views = []
