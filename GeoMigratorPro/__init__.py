# -*- coding: utf-8 -*-
"""
GeoMigrator Pro - Plugin QGIS
Autores: Jose Castillo Ospina / Jarvix Studio
Con asistencia de: Claude (Anthropic)
"""


def classFactory(iface):
    try:
        from .main_plugin import GeoMigratorPro
        return GeoMigratorPro(iface)
    except Exception:
        import traceback
        from qgis.PyQt.QtWidgets import QMessageBox
        QMessageBox.critical(
            None,
            "GeoMigrator Pro - Error al cargar",
            "No se pudo cargar el plugin.\n\n" + traceback.format_exc()
        )
        raise
