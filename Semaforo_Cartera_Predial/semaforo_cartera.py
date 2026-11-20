from pathlib import Path

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .cartera_dialog import CarteraDialog


class SemaforoCarteraPlugin:
    """Punto de entrada del complemento independiente."""

    MENU = '&Semáforo de Cartera'

    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None

    def initGui(self):
        if self.action:
            return
        icon = QIcon(str(Path(__file__).with_name('icon.png')))
        self.action = QAction(icon, 'Semáforo de Cartera Predial', self.iface.mainWindow())
        self.action.setObjectName('semaforo_cartera_action')
        self.action.setToolTip('Clasificar predios por estado de cartera')
        self.action.triggered.connect(self.toggle_dialog)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToVectorMenu(self.MENU, self.action)

    def unload(self):
        if self.action:
            self.iface.removePluginVectorMenu(self.MENU, self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action.deleteLater()
            self.action = None
        if self.dialog:
            self.dialog.close()
            self.dialog.deleteLater()
            self.dialog = None

    def toggle_dialog(self):
        # La ventana es independiente (sin padre) y define sus banderas en su
        # propio __init__, de modo que tenga botón propio en la barra de tareas
        # y se minimice sin perderse dentro del escritorio de QGIS.
        if not self.dialog:
            self.dialog = CarteraDialog(self.iface)
        if self.dialog.isVisible() and not self.dialog.isMinimized():
            self.dialog.hide()
        else:
            self.dialog.refresh_layers()
            self.dialog.showNormal()
            self.dialog.raise_()
            self.dialog.activateWindow()
