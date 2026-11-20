import os
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import Qt
from .consultas_dialog import ConsultasPredialesDialog


class ConsultasPrediales:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.action = None
        self.dialog = None
        self.info_logo = None

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, 'icons', 'icon.png')
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
        self.action = QAction(icon, 'Consultas Catastrales', self.iface.mainWindow())
        self.action.setToolTip('Herramienta de Consulta Catastral')
        self.action.triggered.connect(self.toggle_dock)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToVectorMenu('&Consultas Catastrales', self.action)
        from .plugin_info_logo import PluginInfoLogo
        self.info_logo = PluginInfoLogo(os.path.join(
            self.plugin_dir, 'icons', 'consulta_catastral_info.png'))

    def unload(self):
        if self.info_logo:
            self.info_logo.shutdown()
            self.info_logo = None
        if self.action:
            self.iface.removePluginVectorMenu('&Consultas Catastrales', self.action)
            self.iface.removeToolBarIcon(self.action)
        if self.dialog:
            self.dialog.shutdown()
            self.dialog = None
        self.action = None

    def toggle_dock(self):
        if self.dialog and self.dialog.isVisible():
            self.dialog.hide_windows()
        else:
            if not self.dialog:
                self._create_dock()
            self.dialog.show()
            self.dialog.raise_()
            self.dialog.activateWindow()

    def _create_dock(self):
        self.dialog = ConsultasPredialesDialog(self.iface)
        self.dialog.setWindowTitle('GeoCatastro Predial')
        window_icon = QIcon()
        for filename in ('icon_32.png', 'icon_64.png', 'icon_128.png'):
            window_icon.addFile(os.path.join(self.plugin_dir, 'icons', filename))
        self.dialog.setWindowIcon(window_icon)
        # Ventana flotante independiente de QGIS
        self.dialog.setWindowFlags(
            Qt.Window |
            Qt.WindowMinimizeButtonHint |
            Qt.WindowMaximizeButtonHint |
            Qt.WindowCloseButtonHint
        )
        self.dialog.resize(660, 720)
        # Centrar en la pantalla
        screen = self.iface.mainWindow().screen()
        if screen:
            geom = screen.availableGeometry()
            self.dialog.move(
                geom.center().x() - self.dialog.width() // 2,
                geom.center().y() - self.dialog.height() // 2
            )
        self.dialog.show()
