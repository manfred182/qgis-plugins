# -*- coding: utf-8 -*-
"""
Utilidades para sistemas de coordenadas de referencia (CRS)
"""
from .compatibility import (
    import_qgs_coordinate_reference_system,
    import_qgs_project,
    import_qgs_vector_file_writer,
    import_qgs_wkb_types,
    log_info,
    log_error,
)

# Opcion de deteccion automatica mostrada en el combo de CRS del dialogo
AUTO_DETECT_CRS_LABEL = "Auto-detectar (recomendado)"

# CRS comunes predefinidos
CRS_PRESETS = {
    "WGS 84 (EPSG:4326)": 4326,
    "WGS 84 / UTM Zona 1N": 32601,
    "WGS 84 / UTM Zona 2N": 32602,
    "WGS 84 / UTM Zona 3N": 32603,
    "WGS 84 / UTM Zona 4N": 32604,
    "WGS 84 / UTM Zona 5N": 32605,
    "WGS 84 / UTM Zona 6N": 32606,
    "WGS 84 / UTM Zona 7N": 32607,
    "WGS 84 / UTM Zona 8N": 32608,
    "WGS 84 / UTM Zona 9N": 32609,
    "WGS 84 / UTM Zona 10N": 32610,
    "WGS 84 / UTM Zona 11N": 32611,
    "WGS 84 / UTM Zona 12N": 32612,
    "WGS 84 / UTM Zona 13N": 32613,
    "WGS 84 / UTM Zona 14N": 32614,
    "WGS 84 / UTM Zona 15N": 32615,
    "WGS 84 / UTM Zona 16N": 32616,
    "WGS 84 / UTM Zona 17N": 32617,
    "WGS 84 / UTM Zona 18N": 32618,
    "WGS 84 / UTM Zona 19N": 32619,
    "WGS 84 / UTM Zona 20N": 32620,
    "WGS 84 / UTM Zona 21N": 32621,
    "WGS 84 / UTM Zona 22N": 32622,
    "WGS 84 / UTM Zona 23N": 32623,
    "WGS 84 / UTM Zona 24N": 32624,
    "WGS 84 / UTM Zona 25N": 32625,
    "WGS 84 / UTM Zona 26N": 32626,
    "WGS 84 / UTM Zona 27N": 32627,
    "WGS 84 / UTM Zona 28N": 32628,
    "WGS 84 / UTM Zona 29N": 32629,
    "WGS 84 / UTM Zona 30N": 32630,
    "WGS 84 / UTM Zona 31N": 32631,
    "WGS 84 / UTM Zona 32N": 32632,
    "WGS 84 / UTM Zona 33N": 32633,
    "WGS 84 / UTM Zona 34N": 32634,
    "WGS 84 / UTM Zona 35N": 32635,
    "WGS 84 / UTM Zona 36N": 32636,
    "WGS 84 / UTM Zona 37N": 32637,
    "WGS 84 / UTM Zona 38N": 32638,
    "WGS 84 / UTM Zona 39N": 32639,
    "WGS 84 / UTM Zona 40N": 32640,
    "WGS 84 / UTM Zona 41N": 32641,
    "WGS 84 / UTM Zona 42N": 32642,
    "WGS 84 / UTM Zona 43N": 32643,
    "WGS 84 / UTM Zona 44N": 32644,
    "WGS 84 / UTM Zona 45N": 32645,
    "WGS 84 / UTM Zona 46N": 32646,
    "WGS 84 / UTM Zona 47N": 32647,
    "WGS 84 / UTM Zona 48N": 32648,
    "WGS 84 / UTM Zona 49N": 32649,
    "WGS 84 / UTM Zona 50N": 32650,
    "WGS 84 / UTM Zona 51N": 32651,
    "WGS 84 / UTM Zona 52N": 32652,
    "WGS 84 / UTM Zona 53N": 32653,
    "WGS 84 / UTM Zona 54N": 32654,
    "WGS 84 / UTM Zona 55N": 32655,
    "WGS 84 / UTM Zona 56N": 32656,
    "WGS 84 / UTM Zona 57N": 32657,
    "WGS 84 / UTM Zona 58N": 32658,
    "WGS 84 / UTM Zona 59N": 32659,
    "WGS 84 / UTM Zona 60N": 32660,
    "WGS 84 / UTM Zona 1S": 32701,
    "WGS 84 / UTM Zona 2S": 32702,
    "WGS 84 / UTM Zona 3S": 32703,
    "WGS 84 / UTM Zona 4S": 32704,
    "WGS 84 / UTM Zona 5S": 32705,
    "WGS 84 / UTM Zona 6S": 32706,
    "WGS 84 / UTM Zona 7S": 32707,
    "WGS 84 / UTM Zona 8S": 32708,
    "WGS 84 / UTM Zona 9S": 32709,
    "WGS 84 / UTM Zona 10S": 32710,
    "WGS 84 / UTM Zona 11S": 32711,
    "WGS 84 / UTM Zona 12S": 32712,
    "WGS 84 / UTM Zona 13S": 32713,
    "WGS 84 / UTM Zona 14S": 32714,
    "WGS 84 / UTM Zona 15S": 32715,
    "WGS 84 / UTM Zona 16S": 32716,
    "WGS 84 / UTM Zona 17S": 32717,
    "WGS 84 / UTM Zona 18S": 32718,
    "WGS 84 / UTM Zona 19S": 32719,
    "WGS 84 / UTM Zona 20S": 32720,
    "WGS 84 / UTM Zona 21S": 32721,
    "WGS 84 / UTM Zona 22S": 32722,
    "WGS 84 / UTM Zona 23S": 32723,
    "WGS 84 / UTM Zona 24S": 32724,
    "WGS 84 / UTM Zona 25S": 32725,
    "WGS 84 / UTM Zona 26S": 32726,
    "WGS 84 / UTM Zona 27S": 32727,
    "WGS 84 / UTM Zona 28S": 32728,
    "WGS 84 / UTM Zona 29S": 32729,
    "WGS 84 / UTM Zona 30S": 32730,
    "WGS 84 / UTM Zona 31S": 32731,
    "WGS 84 / UTM Zona 32S": 32732,
    "WGS 84 / UTM Zona 33S": 32733,
    "WGS 84 / UTM Zona 34S": 32734,
    "WGS 84 / UTM Zona 35S": 32735,
    "WGS 84 / UTM Zona 36S": 32736,
    "WGS 84 / UTM Zona 37S": 32737,
    "WGS 84 / UTM Zona 38S": 32738,
    "WGS 84 / UTM Zona 39S": 32739,
    "WGS 84 / UTM Zona 40S": 32740,
    "WGS 84 / UTM Zona 41S": 32741,
    "WGS 84 / UTM Zona 42S": 32742,
    "WGS 84 / UTM Zona 43S": 32743,
    "WGS 84 / UTM Zona 44S": 32744,
    "WGS 84 / UTM Zona 45S": 32745,
    "WGS 84 / UTM Zona 46S": 32746,
    "WGS 84 / UTM Zona 47S": 32747,
    "WGS 84 / UTM Zona 48S": 32748,
    "WGS 84 / UTM Zona 49S": 32749,
    "WGS 84 / UTM Zona 50S": 32750,
    "WGS 84 / UTM Zona 51S": 32751,
    "WGS 84 / UTM Zona 52S": 32752,
    "WGS 84 / UTM Zona 53S": 32753,
    "WGS 84 / UTM Zona 54S": 32754,
    "WGS 84 / UTM Zona 55S": 32755,
    "WGS 84 / UTM Zona 56S": 32756,
    "WGS 84 / UTM Zona 57S": 32757,
    "WGS 84 / UTM Zona 58S": 32758,
    "WGS 84 / UTM Zona 59S": 32759,
    "WGS 84 / UTM Zona 60S": 32760,
    "MAGNA-SIRGAS (EPSG:3116)": 3116,
    "MAGNA-SIRGAS / Colombia Bogota (EPSG:3117)": 3117,
    "MAGNA-SIRGAS / Colombia Este (EPSG:3118)": 3118,
    "MAGNA-SIRGAS / Colombia Central (EPSG:3119)": 3119,
    "MAGNA-SIRGAS / Colombia West (EPSG:3120)": 3120,
}


def get_crs_by_epsg(epsg_code):
    CRS = import_qgs_coordinate_reference_system()
    return CRS.fromEpsgId(epsg_code)


def get_crs_by_name(name):
    CRS = import_qgs_coordinate_reference_system()
    return CRS(name)


def get_current_project_crs():
    QgsProject = import_qgs_project()
    project = QgsProject.instance()
    return project.crs()


def utm_zone_from_lon(lon):
    return int((lon + 180) / 6) + 1


def utm_epsg_from_lon_lat(lon, lat):
    zone = utm_zone_from_lon(lon)
    if lat >= 0:
        return 32600 + zone
    else:
        return 32700 + zone


def get_crs_list():
    return list(CRS_PRESETS.keys())


def get_epsg_from_name(name):
    return CRS_PRESETS.get(name, 4326)
