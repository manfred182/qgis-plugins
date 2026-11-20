# -*- coding: utf-8 -*-
"""
Capa de compatibilidad para múltiples versiones de QGIS (3.x - 4.x)
"""


def get_qgis_version_int():
    try:
        from qgis.PyQt.QtCore import Qgis
        return Qgis.versionInt()
    except ImportError:
        from qgis.core import Qgis
        return Qgis.versionInt()


def get_qgis_version_str():
    try:
        from qgis.PyQt.QtCore import Qgis
        return Qgis.version()
    except ImportError:
        from qgis.core import Qgis
        return Qgis.version()


def get_iface():
    try:
        from qgis.utils import iface
        return iface
    except ImportError:
        return None


def import_qgs_project():
    from qgis.core import QgsProject
    return QgsProject


def import_qgs_vector_layer():
    from qgis.core import QgsVectorLayer
    return QgsVectorLayer


def import_qgs_feature():
    from qgis.core import QgsFeature
    return QgsFeature


def import_qgs_field():
    from qgis.core import QgsField
    return QgsField


def import_qgs_fields():
    from qgis.core import QgsFields
    return QgsFields


def import_qgs_geometry():
    from qgis.core import QgsGeometry
    return QgsGeometry


def import_qgs_point_xy():
    from qgis.core import QgsPointXY
    return QgsPointXY


def import_qgs_coordinate_reference_system():
    from qgis.core import QgsCoordinateReferenceSystem
    return QgsCoordinateReferenceSystem


def import_qgs_vector_file_writer():
    from qgis.core import QgsVectorFileWriter
    return QgsVectorFileWriter


def import_qgs_wkb_types():
    from qgis.core import QgsWkbTypes
    return QgsWkbTypes


def import_qgs_feature_request():
    from qgis.core import QgsFeatureRequest
    return QgsFeatureRequest


def import_qvariant():
    from qgis.PyQt.QtCore import QVariant
    return QVariant


def import_qfile_dialog():
    from qgis.PyQt.QtWidgets import QFileDialog
    return QFileDialog


def import_qmessage_box():
    from qgis.PyQt.QtWidgets import QMessageBox
    return QMessageBox


def import_qinput_dialog():
    from qgis.PyQt.QtWidgets import QInputDialog
    return QInputDialog


def add_layer_to_project(layer, name=None):
    try:
        QgsProject = import_qgs_project()
        project = QgsProject.instance()
        project.addMapLayer(layer)
    except ImportError:
        pass
    return layer


def log_message(message, level=0):
    try:
        from qgis.core import QgsMessageLog
        QgsMessageLog.logMessage(message, "ProjectGIS", level)
    except ImportError:
        levels = {0: "INFO", 1: "WARN", 2: "ERROR"}
        print(f"[ProjectGIS][{levels.get(level, 'INFO')}] {message}")


def log_info(message):
    log_message(message, 0)


def log_warning(message):
    log_message(message, 1)


def log_error(message):
    log_message(message, 2)
