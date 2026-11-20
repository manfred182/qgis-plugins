# -*- coding: utf-8 -*-
"""
ProjectGIS - Plugin para convertir tablas de coordenadas Excel a Shapefile/GeoPackage
"""
import os
import sys

# Agregar directorio del plugin al path para imports
plugin_dir = os.path.dirname(__file__)
if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)


def classFactory(iface):
    from .coord_excel2gis import ProjectGIS
    return ProjectGIS(iface)
