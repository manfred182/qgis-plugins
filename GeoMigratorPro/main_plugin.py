# -*- coding: utf-8 -*-
"""
GeoMigrator Pro - Plugin Principal
Autores: Jose Castillo Ospina / Jarvix Studio
Con asistencia de: Claude (Anthropic)
"""
import os
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsSettings


class GeoMigratorPro:

    PLUGIN_NAME = "GeoMigratorPro"

    def __init__(self, iface):
        self.iface      = iface
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))
        self.action     = None
        self.dlg        = None
        # Registrar el plugin como activo en QgsSettings
        # Esto garantiza que QGIS lo recuerde entre sesiones
        settings = QgsSettings()
        settings.setValue("PythonPlugins/" + self.PLUGIN_NAME, True)

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, "icon.png")
        self.action = QAction(
            QIcon(icon_path),
            "GeoMigrator Pro",
            self.iface.mainWindow()
        )
        self.action.setObjectName("GeoMigratorProAction")
        self.action.setStatusTip("Abrir GeoMigrator Pro")
        self.action.setWhatsThis("Herramienta de migracion de datos a PostgreSQL/PostGIS")
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToDatabaseMenu("&GeoMigrator Pro", self.action)

    def unload(self):
        if self.action:
            self.iface.removePluginDatabaseMenu("&GeoMigrator Pro", self.action)
            self.iface.removeToolBarIcon(self.action)
            del self.action
            self.action = None

    def run(self):
        from .dialog import GeoMigratorDialog
        self.dlg = GeoMigratorDialog(self.plugin_dir, self.iface)
        self.dlg.show()
        self.dlg.exec_()
