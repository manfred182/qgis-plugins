"""Ventana única del Semáforo de Cartera Predial."""

from pathlib import Path

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout

from .gdb_join_dialog import GdbJoinWidget


class CarteraDialog(QDialog):
    """Aloja el flujo integrado sin pestañas ni análisis duplicados.

    Se abre como una ventana independiente de nivel superior (sin padre) para
    que tenga su propio botón en la barra de tareas y pueda minimizarse,
    restaurarse y maximizarse como cualquier ventana; si fuese hija de la
    ventana principal de QGIS, en Windows se "perdería" al minimizarla.
    """

    def __init__(self, iface):
        super().__init__(None)
        self.iface = iface
        self.setWindowTitle('Semáforo de Cartera Predial — Herramienta unificada')
        icon_path = Path(__file__).with_name('icon.png')
        if icon_path.is_file():
            self.setWindowIcon(QIcon(str(icon_path)))
        # Ventana de nivel superior con botones de minimizar/maximizar/cerrar y
        # entrada propia en la barra de tareas.
        self.setWindowFlags(
            Qt.Window
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
            | Qt.WindowCloseButtonHint
            | Qt.WindowSystemMenuHint
        )
        self.resize(1240, 820)
        self.setMinimumSize(940, 650)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.workspace = GdbJoinWidget(iface, self)
        layout.addWidget(self.workspace)

    def refresh_layers(self):
        """Compatibilidad con la acción del plugin al volver a abrir la ventana."""
        return None
