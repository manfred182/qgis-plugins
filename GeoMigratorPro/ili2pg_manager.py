# -*- coding: utf-8 -*-
"""
Gestor automatico de ili2pg.jar
Descarga y mantiene ili2pg en el directorio del plugin.
"""
import os
import json
import urllib.request
import zipfile
import shutil

# Version compatible con el modelo IGAC incluido.
ILI2PG_VERSION  = "4.4.3"
ILI2PG_IGAC_VERSION = "4.4.3"
ILI2PG_RELEASE_URL = "https://downloads.interlis.ch/ili2pg/ili2pg-release.json"
ILI2PG_ZIP_URL  = "https://downloads.interlis.ch/ili2pg/ili2pg-" + ILI2PG_IGAC_VERSION + ".zip"
ILI2PG_JAR_NAME = "ili2pg-" + ILI2PG_VERSION + ".jar"
ILI2PG_IGAC_JAR_NAME = "ili2pg-" + ILI2PG_IGAC_VERSION + ".jar"

# Repositorio de modelos IGAC - LADM-COL Colombia
# Los modelos IGAC se incluyen localmente en models/igac_ladm_col_v1_0_1/
# Los remotos son solo respaldo para modelos base INTERLIS
IGAC_MODEL_DIR = (
    "http://models.interlis.ch/;"
    "https://models.geo.admin.ch"
)
IGAC_LOCAL_MODEL_SUBDIR = os.path.join("models", "igac_ladm_col_v1_0_1")

# EPSG oficial Colombia MAGNA-SIRGAS origen unico nacional
IGAC_EPSG = "9377"

# Schema por defecto LADM-COL
IGAC_SCHEMA = "ladm_col"


def get_model_dir(plugin_dir):
    """Retorna modeldir priorizando los modelos IGAC incluidos con el plugin."""
    local_dir = os.path.join(plugin_dir, IGAC_LOCAL_MODEL_SUBDIR)
    if os.path.isdir(local_dir):
        return local_dir + ";" + IGAC_MODEL_DIR
    return IGAC_MODEL_DIR


def get_release_info():
    """Retorna URL y version vigente de ili2pg, con respaldo local si falla internet."""
    try:
        with urllib.request.urlopen(ILI2PG_RELEASE_URL, timeout=15) as response:
            raw = response.read().decode("utf-8")
        info = json.loads(raw)
        url = info.get("filename") or ILI2PG_ZIP_URL
        version = info.get("version") or ILI2PG_VERSION
        return url, version
    except Exception:
        return ILI2PG_ZIP_URL, ILI2PG_VERSION


def get_jar_path(plugin_dir):
    """Retorna la ruta al JAR si existe, o None."""
    igac_jar_path = os.path.join(plugin_dir, "ili2pg", ILI2PG_IGAC_JAR_NAME)
    if os.path.isfile(igac_jar_path):
        return igac_jar_path

    jar_path = os.path.join(plugin_dir, "ili2pg", ILI2PG_JAR_NAME)
    if os.path.isfile(jar_path):
        return jar_path
    # Buscar cualquier version disponible
    ili_dir = os.path.join(plugin_dir, "ili2pg")
    if os.path.isdir(ili_dir):
        for f in os.listdir(ili_dir):
            if f.startswith("ili2pg") and f.endswith(".jar"):
                return os.path.join(ili_dir, f)
    return None


def download_jar(plugin_dir, progress_callback=None):
    """
    Descarga ili2pg desde interlis.ch, lo descomprime y retorna la ruta al JAR.
    progress_callback(msg: str) se llama con mensajes de estado.
    """
    ili_dir = os.path.join(plugin_dir, "ili2pg")
    os.makedirs(ili_dir, exist_ok=True)

    zip_path = os.path.join(ili_dir, "ili2pg.zip")

    zip_url, version = get_release_info()

    if progress_callback:
        progress_callback("Descargando ili2pg " + version + " desde downloads.interlis.ch...")

    try:
        urllib.request.urlretrieve(zip_url, zip_path)
    except Exception as e:
        raise RuntimeError("No se pudo descargar ili2pg: " + str(e))

    if progress_callback:
        progress_callback("Descomprimiendo ili2pg...")

    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(ili_dir)
    os.remove(zip_path)

    jar = get_jar_path(plugin_dir)
    if jar:
        if progress_callback:
            progress_callback("ili2pg instalado en: " + jar)
        return jar

    raise RuntimeError("No se encontro el JAR despues de descomprimir.")
