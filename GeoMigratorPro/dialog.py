# -*- coding: utf-8 -*-
"""
GeoMigrator Pro - Dialogo principal v1.0
Autor: Jose Orlando Castillo Ospina - Ing. Agroecologo, Esp. SIG y Esp. Gestion Ambiental
Con apoyo de IA: Claude (Anthropic) y ChatGPT (OpenAI)
"""
import os
import re
import subprocess
import sys
import unicodedata

from qgis.PyQt.QtWidgets import (
    QDialog, QFileDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QLineEdit,
    QMessageBox, QTabWidget, QWidget, QProgressBar,
    QCheckBox, QListWidget, QListWidgetItem,
    QComboBox, QGroupBox, QAbstractItemView, QInputDialog,
    QScrollArea, QFrame, QSizePolicy, QGridLayout
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QFont, QPixmap
from qgis.core import QgsVectorLayer, QgsProject, QgsSettings, QgsDataSourceUri, QgsProviderRegistry

from .worker import OgrWorker, OgrInfoWorker
from .xtf_worker import JarDownloadWorker, XtfImportWorker
from .profiles import ProfileManager
from .ili2pg_manager import (
    get_jar_path, get_model_dir, IGAC_EPSG, IGAC_SCHEMA, ILI2PG_VERSION
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _pg_conn(host, port, db, user, pwd, ssl_mode=""):
    ssl = " sslmode=" + ssl_mode if ssl_mode else ""
    return ("PG:host=" + host + " port=" + port +
            " dbname=" + db + " user=" + user + " password=" + pwd + ssl)


def _validate(host, port, db, user):
    if not host.strip():
        return "El Host no puede estar vacio."
    if not port.strip() or not port.strip().isdigit():
        return "El Puerto debe ser un numero valido."
    port_num = int(port.strip())
    if port_num < 1 or port_num > 65535:
        return "El Puerto debe estar entre 1 y 65535."
    if not db.strip():
        return "La Base de datos no puede estar vacia."
    if not user.strip():
        return "El Usuario no puede estar vacio."
    return ""


def _ssl_mode(f):
    """Retorna 'require' si el checkbox SSL esta activo, o '' si no."""
    ssl_field = f.get("ssl") if isinstance(f, dict) else None
    if ssl_field is not None:
        if hasattr(ssl_field, "isChecked"):
            return "require" if ssl_field.isChecked() else ""
        return "require" if ssl_field else ""
    return ""


def _sanitize_table_name(name):
    name = unicodedata.normalize("NFKD", name.strip())
    name = "".join(ch for ch in name if not unicodedata.combining(ch))
    name = name.lower().replace(" ", "_").replace("-", "_")
    name = re.sub(r"[^a-z0-9_]", "", name)
    name = re.sub(r"_+", "_", name).strip("_")
    if name and name[0].isdigit():
        name = "t_" + name
    return name


def _sanitize_cmd(cmd):
    """Reemplaza la contrasena en un comando antes de mostrarlo en log."""
    result = []
    for arg in cmd:
        if "password=" in arg.lower():
            parts = arg.split("password=", 1)
            result.append(parts[0] + "password=****")
        else:
            result.append(arg)
    return " ".join(result)


def _list_gdb_layers_sync(gdb_path):
    """Retorna lista de capas en una GDB usando ogrinfo (bloqueante)."""
    try:
        r = subprocess.run(
            ["ogrinfo", "-al", "-so", gdb_path],
            capture_output=True, text=True,
            timeout=30, encoding="utf-8", errors="replace"
        )
        layers = []
        for line in r.stdout.splitlines():
            if line.startswith("Layer name:"):
                layers.append(line.split(":", 1)[1].strip())
        return layers
    except Exception:
        return []


def _find_java():
    """Busca Java en PATH y en rutas comunes de Windows, macOS y Linux."""
    import shutil
    java = shutil.which("java")
    if java:
        return java

    candidates = []

    if sys.platform == "win32":
        candidates += [
            r"C:\Program Files (x86)\Common Files\Oracle\Java\java8path\java.exe",
            r"C:\Program Files\Common Files\Oracle\Java\javapath\java.exe",
        ]
        for root in (r"C:\Program Files\Java", r"C:\Program Files\Eclipse Adoptium"):
            if os.path.isdir(root):
                for dirpath, _, filenames in os.walk(root):
                    if "java.exe" in filenames and dirpath.lower().endswith(r"\bin"):
                        candidates.append(os.path.join(dirpath, "java.exe"))
    elif sys.platform == "darwin":
        candidates += [
            "/usr/bin/java",
            "/Library/Java/JavaVirtualMachines/openjdk.jdk/Contents/Home/bin/java",
            "/Library/Internet Plug-Ins/JavaAppletPlugin.plugin/Contents/Home/bin/java",
        ]
        java_home = os.environ.get("JAVA_HOME")
        if java_home:
            candidates.append(os.path.join(java_home, "bin", "java"))
        for d in ["/Library/Java/JavaVirtualMachines",
                   "/System/Library/Java/JavaVirtualMachines",
                   os.path.expanduser("~/Library/Java/JavaVirtualMachines")]:
            if os.path.isdir(d):
                for item in os.listdir(d):
                    jdk = os.path.join(d, item, "Contents/Home/bin/java")
                    if os.path.isfile(jdk):
                        candidates.append(jdk)
        homebrew = shutil.which("brew")
        if homebrew:
            for prefix in ["/opt/homebrew/opt/openjdk",
                           "/usr/local/opt/openjdk"]:
                jdk = os.path.join(prefix, "bin", "java")
                if os.path.isfile(jdk):
                    candidates.append(jdk)
    else:
        candidates += ["/usr/bin/java"]
        java_home = os.environ.get("JAVA_HOME")
        if java_home:
            candidates.append(os.path.join(java_home, "bin", "java"))
        for d in ["/usr/lib/jvm",
                   "/usr/lib64/jvm",
                   "/usr/java",
                   "/opt/java"]:
            if os.path.isdir(d):
                for dirpath, _, filenames in os.walk(d):
                    if "java" in filenames and dirpath.endswith("bin"):
                        candidates.append(os.path.join(dirpath, "java"))
                        break

    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return "java"


def _detect_xtf_models(xtf_path):
    """Detecta modelos usados por el XTF desde HEADERSECTION y BID."""
    try:
        with open(xtf_path, "r", encoding="utf-8", errors="replace") as fh:
            chunk = fh.read(250000)
    except Exception:
        return ""

    header_names = re.findall(r'<MODEL\s+NAME="([^"]+)"', chunk)
    basket_names = re.findall(r'<([A-Za-z_][A-Za-z0-9_]*)\.[^>\s]+\s+BID=', chunk)

    names = []
    for name in basket_names + header_names:
        if name not in names and not name.startswith("ISO19107"):
            names.append(name)
    return ";".join(names)


def _ensure_uuid_extension(conn):
    """Activa uuid-ossp si no esta instalado."""
    sql = 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'
    result = subprocess.run(
        ["ogrinfo", conn, "-sql", sql],
        capture_output=True, text=True, timeout=20,
        encoding="utf-8", errors="replace"
    )
    return result.returncode == 0, result.stderr.strip() or result.stdout.strip()


def _create_pg_database(host, port, user, pwd, ssl_mode, db_name):
    """Crea una base de datos PostgreSQL y activa PostGIS + uuid-ossp."""
    safe = re.sub(r'[^a-z0-9_]', '', db_name.strip().lower())
    if not safe:
        return False, "Nombre de base de datos invalido"
    if safe[0].isdigit():
        safe = "db_" + safe

    conn_maint = _pg_conn(host, port, "postgres", user, pwd, ssl_mode)
    sql_create = 'CREATE DATABASE "' + safe + '" WITH ENCODING \'UTF8\' OWNER "' + user + '"'
    r = subprocess.run(
        ["ogrinfo", conn_maint, "-sql", sql_create],
        capture_output=True, text=True, timeout=30,
        encoding="utf-8", errors="replace"
    )
    if r.returncode != 0:
        return False, r.stderr.strip() or r.stdout.strip()

    conn_new = _pg_conn(host, port, safe, user, pwd, ssl_mode)
    for ext in [
        "CREATE EXTENSION IF NOT EXISTS postgis",
        'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'
    ]:
        r = subprocess.run(
            ["ogrinfo", conn_new, "-sql", ext],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace"
        )
        if r.returncode != 0:
            return False, "Error en " + ext + ": " + (r.stderr.strip() or r.stdout.strip())

    return True, safe


def _create_pg_schema(conn, schema):
    """Crea un esquema en PostgreSQL si no existe."""
    if not schema or schema == "public":
        return True, ""
    sql = 'CREATE SCHEMA IF NOT EXISTS "' + schema + '"'
    r = subprocess.run(
        ["ogrinfo", conn, "-sql", sql],
        capture_output=True, text=True, timeout=20,
        encoding="utf-8", errors="replace"
    )
    if r.returncode != 0:
        return False, r.stderr.strip() or r.stdout.strip()
    return True, ""


def _ensure_epsg_9377(conn):
    """Registra EPSG:9377 en spatial_ref_sys si PostGIS no lo trae."""
    srtext = (
        'PROJCS["MAGNA-SIRGAS 2018 / Origen-Nacional",'
        'GEOGCS["MAGNA-SIRGAS 2018",'
        'DATUM["Marco_Geocentrico_Nacional_de_Referencia_2018",'
        'SPHEROID["GRS 1980",6378137,298.257222101],'
        'TOWGS84[0,0,0,0,0,0,0]],'
        'PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],'
        'UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],'
        'AUTHORITY["EPSG","20046"]],'
        'PROJECTION["Transverse_Mercator"],'
        'PARAMETER["latitude_of_origin",4],'
        'PARAMETER["central_meridian",-73],'
        'PARAMETER["scale_factor",0.9992],'
        'PARAMETER["false_easting",5000000],'
        'PARAMETER["false_northing",2000000],'
        'UNIT["metre",1,AUTHORITY["EPSG","9001"]],'
        'AUTHORITY["EPSG","9377"]]'
    )
    proj4text = (
        "+proj=tmerc +lat_0=4 +lon_0=-73 +k=0.9992 "
        "+x_0=5000000 +y_0=2000000 +ellps=GRS80 "
        "+towgs84=0,0,0,0,0,0,0 +units=m +no_defs +type=crs"
    )
    sql = (
        "INSERT INTO spatial_ref_sys (srid, auth_name, auth_srid, proj4text, srtext) "
        "SELECT 9377, 'EPSG', 9377, '" + proj4text + "', '" + srtext + "' "
        "WHERE NOT EXISTS (SELECT 1 FROM spatial_ref_sys WHERE srid = 9377)"
    )
    result = subprocess.run(
        ["ogrinfo", conn, "-sql", sql],
        capture_output=True, text=True, timeout=20,
        encoding="utf-8", errors="replace"
    )
    return result.returncode == 0, result.stderr.strip() or result.stdout.strip()


BTN_GREEN  = "font-weight:bold;padding:8px;background:#1a6b3c;color:white;border-radius:4px;"
BTN_RED    = "font-weight:bold;padding:8px;background:#a01010;color:white;border-radius:4px;"
BTN_BLUE   = "font-weight:bold;padding:6px;background:#1a4a8a;color:white;border-radius:4px;"
BTN_ORANGE = "font-weight:bold;padding:7px;background:#b05a00;color:white;border-radius:4px;font-size:12px;"

SETTINGS_KEY = "GeoMigratorPro/"


# ── dialogo principal ─────────────────────────────────────────────────────────

class GeoMigratorDialog(QDialog):

    def __init__(self, plugin_dir=None, iface=None):
        super().__init__()
        self.plugin_dir      = plugin_dir or os.path.dirname(os.path.abspath(__file__))
        self.iface           = iface
        self.profiles        = ProfileManager(self.plugin_dir)
        self._worker         = None
        self._xtf_worker     = None
        self._dl_worker      = None
        self._pending_cmds   = []
        self._load_after     = False
        self._load_db        = ""
        self._load_schema    = "public"
        self._load_tables    = []
        self._load_conn_str  = ""
        self._label          = ""
        self._total          = 0
        self._done           = 0
        self._errors         = []
        self.setWindowTitle("GeoMigrator Pro  v1.0")
        self.resize(850, 750)
        self.setMinimumSize(640, 480)
        self.setSizeGripEnabled(True)
        self._build_ui()
        self._check_dependencies()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        main = QVBoxLayout()
        main.setSpacing(6)

        # cabecera
        header = QHBoxLayout()
        header.setSpacing(12)
        lbl_logo = QLabel()
        logo_path = os.path.join(self.plugin_dir, "logo.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path).scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            lbl_logo.setPixmap(pix)
        header.addWidget(lbl_logo)

        col = QVBoxLayout()
        t = QLabel("GeoMigrator Pro")
        fnt = QFont()
        fnt.setPointSize(14)
        fnt.setBold(True)
        t.setFont(fnt)
        s = QLabel("Plugin QGIS  -  Migracion hacia PostgreSQL / PostGIS  -  v1.0")
        s.setStyleSheet("color:#5a7fa8;font-size:11px;")
        col.addWidget(t)
        col.addWidget(s)
        header.addLayout(col)
        header.addStretch()
        main.addLayout(header)

        sep = QLabel()
        sep.setFixedHeight(2)
        sep.setStyleSheet("background:#dce8f0;margin:4px 0;")
        main.addWidget(sep)

        self.tabs = QTabWidget()
        self.tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tabs.addTab(self._scroll_tab(self._tab_gdb()),    "GDB")
        self.tabs.addTab(self._scroll_tab(self._tab_vector()), "SHP/GeoJSON/KML")
        self.tabs.addTab(self._scroll_tab(self._tab_excel()),  "Excel")
        self.tabs.addTab(self._scroll_tab(self._tab_csv()),    "CSV")
        self.tabs.addTab(self._scroll_tab(self._tab_xtf()),    "XTF")
        self.tabs.addTab(self._scroll_tab(self._tab_batch()),  "Lote")
        self.tabs.addTab(self._scroll_tab(self._tab_about()),  "Acerca de")
        main.addWidget(self.tabs, 3)

        prog_row = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setVisible(False)
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setStyleSheet(BTN_RED)
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self._cancel)
        prog_row.addWidget(self.progress)
        prog_row.addWidget(self.btn_cancel)
        main.addLayout(prog_row)

        main.addWidget(QLabel("Log de proceso:"))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Courier New", 9))
        self.log.setStyleSheet("background:#1e1e1e;color:#d4d4d4;border-radius:4px;")
        self.log.setMinimumHeight(90)
        self.log.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main.addWidget(self.log, 1)

        btn_row = QHBoxLayout()
        btn_clear  = QPushButton("Limpiar log")
        btn_export = QPushButton("Exportar log .txt")
        btn_clear.clicked.connect(self.log.clear)
        btn_export.clicked.connect(self._export_log)
        btn_row.addWidget(btn_clear)
        btn_row.addWidget(btn_export)
        btn_row.addStretch()
        main.addLayout(btn_row)
        self.setLayout(main)

    def _scroll_tab(self, widget):
        scroll = QScrollArea()
        scroll.setWidget(widget)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        return scroll

    # ── widget perfiles + campos PG ───────────────────────────────────────────

    def _pg_widget(self, tag):
        grp = QGroupBox("Conexion PostgreSQL")
        lay = QVBoxLayout(grp)
        lay.setSpacing(4)

        prof_row = QHBoxLayout()
        combo = QComboBox()
        combo.addItem("-- Seleccionar perfil --")
        combo.addItems(self.profiles.names())
        btn_load = QPushButton("Cargar")
        btn_save = QPushButton("Guardar")
        btn_del  = QPushButton("Eliminar")
        for b in (btn_load, btn_save, btn_del):
            b.setStyleSheet(BTN_BLUE)
            b.setFixedWidth(72)
        prof_row.addWidget(QLabel("Perfil:"))
        prof_row.addWidget(combo, 1)
        prof_row.addWidget(btn_load)
        prof_row.addWidget(btn_save)
        prof_row.addWidget(btn_del)
        lay.addLayout(prof_row)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(2)

        def field(row, col, label, ph, default="", echo=QLineEdit.Normal, tip=""):
            lbl = QLabel(label)
            txt = QLineEdit()
            txt.setPlaceholderText(ph)
            txt.setEchoMode(echo)
            txt.setMinimumHeight(24)
            if default:
                txt.setText(default)
            if tip:
                txt.setToolTip(tip)
                lbl.setToolTip(tip)
            grid.addWidget(lbl, row * 2, col)
            grid.addWidget(txt, row * 2 + 1, col)
            return txt

        f = {}
        f["host"]   = field(0, 0, "Host",         "localhost", "localhost",
                            tip="Direccion del servidor PostgreSQL (ej: localhost, 192.168.1.10)")
        f["port"]   = field(0, 1, "Puerto",        "5432",      "5432",
                            tip="Puerto de PostgreSQL (default: 5432)")
        f["db"]     = field(1, 0, "Base de datos", "mi_base",
                            tip="Nombre de la base de datos destino")
        f["user"]   = field(1, 1, "Usuario",       "postgres",  "postgres",
                            tip="Usuario de PostgreSQL")
        f["pwd"]    = field(2, 0, "Contrasena",    "........",  echo=QLineEdit.Password,
                            tip="Contrasena del usuario PostgreSQL")
        f["schema"] = field(2, 1, "Schema",         "public",   "public",
                            tip="Schema de PostgreSQL donde se crearan las tablas")
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        lay.addLayout(grid)

        ssl_row = QHBoxLayout()
        f["ssl"] = QCheckBox("Usar SSL")
        f["ssl"].setToolTip("Activar conexion SSL/TLS con PostgreSQL")
        ssl_row.addWidget(f["ssl"])
        ssl_row.addStretch()

        btn_test = QPushButton("Probar conexion")
        btn_test.setStyleSheet(BTN_BLUE)
        btn_test.clicked.connect(lambda: self._test_conn(f))
        ssl_row.addWidget(btn_test, 1)
        lay.addLayout(ssl_row)

        create_row = QHBoxLayout()
        create_row.addStretch()
        btn_create_db = QPushButton("Crear BD en PostgreSQL...")
        btn_create_db.setStyleSheet("font-weight:bold;padding:5px 10px;background:#2a6b3c;color:white;border-radius:3px;")

        def _create_db():
            err = _validate(f["host"].text(), f["port"].text(),
                            f["db"].text(), f["user"].text())
            if err:
                QMessageBox.warning(self, "Falta dato", err)
                return
            name, ok = QInputDialog.getText(
                self, "Crear base de datos",
                "Nombre de la nueva base de datos:")
            if not ok or not name.strip():
                return
            ok, result = _create_pg_database(
                f["host"].text(), f["port"].text(),
                f["user"].text(), f["pwd"].text(),
                _ssl_mode(f), name.strip()
            )
            if ok:
                f["db"].setText(result)
                QMessageBox.information(
                    self, "BD creada",
                    "Base de datos creada:\n" + result +
                    "\n\nPostGIS y uuid-ossp activados.")
            else:
                QMessageBox.critical(
                    self, "Error", "No se pudo crear la BD:\n" + result)

        btn_create_db.clicked.connect(_create_db)
        create_row.addWidget(btn_create_db)
        lay.addLayout(create_row)

        def _load():
            name = combo.currentText()
            if name.startswith("--"):
                return
            p = self.profiles.get(name)
            f["host"].setText(p.get("host", ""))
            f["port"].setText(p.get("port", "5432"))
            f["db"].setText(p.get("db", ""))
            f["user"].setText(p.get("user", ""))
            f["pwd"].setText(p.get("pwd", ""))
            f["schema"].setText(p.get("schema", "public"))
            if "ssl" in f and isinstance(f["ssl"], QCheckBox):
                f["ssl"].setChecked(p.get("ssl", False))

        def _save():
            name, ok = QInputDialog.getText(self, "Guardar perfil", "Nombre del perfil:")
            if not ok or not name.strip():
                return
            ssl_val = f["ssl"].isChecked() if "ssl" in f else False
            self.profiles.save(
                name.strip(),
                f["host"].text(), f["port"].text(), f["db"].text(),
                f["user"].text(), f["pwd"].text(), f["schema"].text(),
                ssl_val
            )
            self._refresh_combos()
            QMessageBox.information(self, "Perfil guardado", "Perfil guardado: " + name.strip())

        def _del():
            name = combo.currentText()
            if name.startswith("--"):
                return
            confirm = QMessageBox.question(
                self, "Confirmar eliminacion",
                "Eliminar perfil: " + name + "?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm != QMessageBox.Yes:
                return
            self.profiles.delete(name)
            self._refresh_combos()

        btn_load.clicked.connect(_load)
        btn_save.clicked.connect(_save)
        btn_del.clicked.connect(_del)
        grp.fields = f
        grp.combo  = combo
        return grp

    def _refresh_combos(self):
        for attr in ("pg_gdb", "pg_vector", "pg_excel", "pg_csv", "pg_xtf", "pg_batch"):
            w = getattr(self, attr, None)
            if w is None:
                continue
            combo = w.combo
            current = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("-- Seleccionar perfil --")
            combo.addItems(self.profiles.names())
            idx = combo.findText(current)
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            combo.blockSignals(False)

    def _test_conn(self, f):
        err = _validate(f["host"].text(), f["port"].text(),
                        f["db"].text(), f["user"].text())
        if err:
            QMessageBox.warning(self, "Falta dato", err)
            return
        conn = _pg_conn(f["host"].text(), f["port"].text(),
                        f["db"].text(), f["user"].text(), f["pwd"].text(),
                        _ssl_mode(f))
        try:
            r = subprocess.run(
                ["ogrinfo", "-so", conn],
                capture_output=True, text=True,
                timeout=8, encoding="utf-8", errors="replace"
            )
            if r.returncode == 0:
                QMessageBox.information(self, "Conexion exitosa",
                    "La conexion a PostgreSQL/PostGIS es correcta.")
            else:
                QMessageBox.critical(self, "Error de conexion",
                    r.stderr.strip() or "No se pudo conectar.")
        except FileNotFoundError:
            QMessageBox.critical(self, "Error",
                "ogrinfo no encontrado. Verifica que GDAL este en el PATH.")
        except subprocess.TimeoutExpired:
            QMessageBox.critical(self, "Timeout",
                "La conexion tardo demasiado. Verifica host y puerto.")

    # ── TAB GDB ───────────────────────────────────────────────────────────────

    def _tab_gdb(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.addWidget(QLabel("Carpeta Geodatabase (.gdb):"))
        row = QHBoxLayout()
        self.txt_gdb = QLineEdit()
        self.txt_gdb.setPlaceholderText("/ruta/a/datos.gdb")
        btn = QPushButton("Seleccionar GDB...")
        btn.clicked.connect(self._select_gdb)
        row.addWidget(self.txt_gdb)
        row.addWidget(btn)
        lay.addLayout(row)

        lay.addWidget(QLabel("Capas a importar (vacio = todas):"))
        cap_row = QHBoxLayout()
        self.lst_gdb_layers = QListWidget()
        self.lst_gdb_layers.setSelectionMode(QAbstractItemView.MultiSelection)
        self.lst_gdb_layers.setMaximumHeight(100)
        btn_list = QPushButton("Listar capas")
        btn_list.setStyleSheet(BTN_BLUE)
        btn_list.setFixedWidth(100)
        btn_list.clicked.connect(self._list_gdb_layers)
        cap_row.addWidget(self.lst_gdb_layers)
        cap_row.addWidget(btn_list, 0, Qt.AlignTop)
        lay.addLayout(cap_row)

        self.chk_overwrite = QCheckBox("Sobreescribir tablas existentes (-overwrite)")
        self.chk_overwrite.setChecked(True)
        self.chk_makevalid = QCheckBox("Reparar geometrias invalidas (-makevalid)")
        self.chk_makevalid.setChecked(True)
        self.chk_load_gdb  = QCheckBox("Cargar capas en QGIS al terminar")
        self.chk_load_gdb.setChecked(True)
        lay.addWidget(self.chk_overwrite)
        lay.addWidget(self.chk_makevalid)
        lay.addWidget(self.chk_load_gdb)

        self.pg_gdb = self._pg_widget("gdb")
        lay.addWidget(self.pg_gdb)
        btn_imp = QPushButton("IMPORTAR GDB")
        btn_imp.setStyleSheet(BTN_GREEN)
        btn_imp.clicked.connect(self._import_gdb)
        lay.addWidget(btn_imp)
        lay.addStretch()
        return tab

    def _select_gdb(self):
        path = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta .gdb")
        if path:
            self.txt_gdb.setText(path)
            self.lst_gdb_layers.clear()

    def _list_gdb_layers(self):
        src = self.txt_gdb.text().strip()
        if not src:
            QMessageBox.warning(self, "Falta dato", "Selecciona una GDB primero.")
            return
        self.lst_gdb_layers.clear()
        self.lst_gdb_layers.addItem("Leyendo capas...")
        self._info_worker = OgrInfoWorker(src, parent=self)
        self._info_worker.layers_ready.connect(self._on_gdb_layers)
        self._info_worker.error.connect(lambda e: self.lst_gdb_layers.addItem("Error: " + e))
        self._info_worker.start()

    def _on_gdb_layers(self, layers):
        self.lst_gdb_layers.clear()
        for lyr in layers:
            self.lst_gdb_layers.addItem(QListWidgetItem(lyr))
        if not layers:
            self.lst_gdb_layers.addItem("(no se encontraron capas)")

    def _import_gdb(self):
        gdb = self.txt_gdb.text().strip()
        if not gdb:
            QMessageBox.warning(self, "Falta dato", "Selecciona una Geodatabase.")
            return
        f = self.pg_gdb.fields
        err = _validate(f["host"].text(), f["port"].text(),
                        f["db"].text(), f["user"].text())
        if err:
            QMessageBox.warning(self, "Falta dato", err)
            return
        conn   = self._ensure_db_and_schema(f)
        schema = f["schema"].text().strip() or "public"
        sel    = [i.text() for i in self.lst_gdb_layers.selectedItems()]
        base_cmd = [
            "ogr2ogr", "-f", "PostgreSQL", conn, gdb,
            "-progress", "-skipfailures",
            "-nlt", "PROMOTE_TO_MULTI",
            "-lco", "SCHEMA=" + schema,
            "-lco", "GEOMETRY_NAME=geom",
            "--config", "PG_USE_COPY", "YES"
        ]
        if self.chk_overwrite.isChecked():
            base_cmd.append("-overwrite")
        if self.chk_makevalid.isChecked():
            base_cmd.append("-makevalid")
        if sel:
            cmds   = [base_cmd + [layer] for layer in sel]
            tables = [_sanitize_table_name(layer) for layer in sel]
        else:
            cmds   = [base_cmd]
            tables = [_sanitize_table_name(layer) for layer in _list_gdb_layers_sync(gdb)]
        self._run_queue(cmds, "GDB", self.chk_load_gdb.isChecked(),
                        f["db"].text(), schema, tables, conn)

    # ── TAB VECTOR ────────────────────────────────────────────────────────────

    def _tab_vector(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.addWidget(QLabel("Archivo vectorial (SHP, GeoJSON, KML, GPX...):"))
        row = QHBoxLayout()
        self.txt_vector = QLineEdit()
        self.txt_vector.setPlaceholderText("/ruta/a/datos.shp")
        btn = QPushButton("Seleccionar...")
        btn.clicked.connect(self._select_vector)
        row.addWidget(self.txt_vector)
        row.addWidget(btn)
        lay.addLayout(row)
        lay.addWidget(QLabel("Nombre tabla destino (vacio = nombre del archivo):"))
        self.txt_vector_table = QLineEdit()
        self.txt_vector_table.setPlaceholderText("mi_tabla")
        lay.addWidget(self.txt_vector_table)
        lay.addWidget(QLabel("EPSG destino (vacio = no reproyectar):"))
        self.txt_vector_epsg = QLineEdit()
        self.txt_vector_epsg.setPlaceholderText("4326")
        lay.addWidget(self.txt_vector_epsg)
        self.chk_load_vec = QCheckBox("Cargar capa en QGIS al terminar")
        self.chk_load_vec.setChecked(True)
        lay.addWidget(self.chk_load_vec)
        self.pg_vector = self._pg_widget("vector")
        lay.addWidget(self.pg_vector)
        btn_imp = QPushButton("IMPORTAR ARCHIVO VECTORIAL")
        btn_imp.setStyleSheet(BTN_GREEN)
        btn_imp.clicked.connect(self._import_vector)
        lay.addWidget(btn_imp)
        lay.addStretch()
        return tab

    def _select_vector(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo vectorial", "",
            "Vectoriales (*.shp *.geojson *.json *.kml *.kmz *.gpx *.gml *.tab)")
        if path:
            self.txt_vector.setText(path)

    def _import_vector(self):
        src = self.txt_vector.text().strip()
        if not src:
            QMessageBox.warning(self, "Falta dato", "Selecciona un archivo vectorial.")
            return
        f = self.pg_vector.fields
        err = _validate(f["host"].text(), f["port"].text(),
                        f["db"].text(), f["user"].text())
        if err:
            QMessageBox.warning(self, "Falta dato", err)
            return
        conn   = self._ensure_db_and_schema(f)
        table  = _sanitize_table_name(self.txt_vector_table.text().strip()) or \
                 _sanitize_table_name(os.path.splitext(os.path.basename(src))[0])
        schema = f["schema"].text().strip() or "public"
        cmd = [
            "ogr2ogr", "-f", "PostgreSQL", conn, src,
            "-nln", schema + "." + table,
            "-overwrite", "-progress", "-skipfailures",
            "-nlt", "PROMOTE_TO_MULTI",
            "-lco", "GEOMETRY_NAME=geom",
            "--config", "PG_USE_COPY", "YES"
        ]
        epsg = self.txt_vector_epsg.text().strip()
        if epsg:
            cmd += ["-t_srs", "EPSG:" + epsg]
        self._run_queue([cmd], "VECTORIAL", self.chk_load_vec.isChecked(),
                        f["db"].text(), schema, [table], conn)

    # ── TAB EXCEL ─────────────────────────────────────────────────────────────

    def _tab_excel(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.addWidget(QLabel("Archivo Excel (.xlsx / .xls):"))
        row = QHBoxLayout()
        self.txt_excel = QLineEdit()
        self.txt_excel.setPlaceholderText("/ruta/a/datos.xlsx")
        btn = QPushButton("Seleccionar Excel...")
        btn.clicked.connect(self._select_excel)
        row.addWidget(self.txt_excel)
        row.addWidget(btn)
        lay.addLayout(row)
        lay.addWidget(QLabel("Nombre tabla destino:"))
        self.txt_excel_table = QLineEdit()
        self.txt_excel_table.setPlaceholderText("mi_tabla_excel")
        lay.addWidget(self.txt_excel_table)
        self.pg_excel = self._pg_widget("excel")
        lay.addWidget(self.pg_excel)
        btn_imp = QPushButton("IMPORTAR EXCEL")
        btn_imp.setStyleSheet(BTN_GREEN)
        btn_imp.clicked.connect(self._import_excel)
        lay.addWidget(btn_imp)
        lay.addStretch()
        return tab

    def _select_excel(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Excel", "", "Excel (*.xlsx *.xls)")
        if path:
            self.txt_excel.setText(path)

    def _import_excel(self):
        xl = self.txt_excel.text().strip()
        if not xl:
            QMessageBox.warning(self, "Falta dato", "Selecciona un archivo Excel.")
            return
        f = self.pg_excel.fields
        err = _validate(f["host"].text(), f["port"].text(),
                        f["db"].text(), f["user"].text())
        if err:
            QMessageBox.warning(self, "Falta dato", err)
            return
        conn   = self._ensure_db_and_schema(f)
        table  = _sanitize_table_name(self.txt_excel_table.text().strip()) or \
                 _sanitize_table_name(os.path.splitext(os.path.basename(xl))[0])
        schema = f["schema"].text().strip() or "public"
        cmd = [
            "ogr2ogr", "-f", "PostgreSQL", conn, xl,
            "-nln", schema + "." + table,
            "-overwrite", "--config", "PG_USE_COPY", "YES"
        ]
        self._run_queue([cmd], "Excel", False, f["db"].text(), schema, [table], conn)

    # ── TAB CSV ───────────────────────────────────────────────────────────────

    def _tab_csv(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.addWidget(QLabel("Archivo CSV:"))
        row = QHBoxLayout()
        self.txt_csv = QLineEdit()
        self.txt_csv.setPlaceholderText("/ruta/a/datos.csv")
        btn = QPushButton("Seleccionar CSV...")
        btn.clicked.connect(self._select_csv)
        row.addWidget(self.txt_csv)
        row.addWidget(btn)
        lay.addLayout(row)
        lay.addWidget(QLabel("Nombre tabla destino:"))
        self.txt_csv_table = QLineEdit()
        self.txt_csv_table.setPlaceholderText("mi_tabla_csv")
        lay.addWidget(self.txt_csv_table)
        lay.addWidget(QLabel("Delimitador (vacio=auto):"))
        self.txt_csv_delim = QLineEdit(",")
        self.txt_csv_delim.setPlaceholderText("ej: ,  ;  tab  |")
        lay.addWidget(self.txt_csv_delim)
        lay.addWidget(QLabel("Columna Longitud / X  (vacio si no aplica):"))
        self.txt_csv_x = QLineEdit()
        self.txt_csv_x.setPlaceholderText("longitud")
        lay.addWidget(self.txt_csv_x)
        lay.addWidget(QLabel("Columna Latitud / Y  (vacio si no aplica):"))
        self.txt_csv_y = QLineEdit()
        self.txt_csv_y.setPlaceholderText("latitud")
        lay.addWidget(self.txt_csv_y)
        lay.addWidget(QLabel("EPSG del CSV:"))
        self.txt_csv_epsg = QLineEdit("4326")
        lay.addWidget(self.txt_csv_epsg)
        self.pg_csv = self._pg_widget("csv")
        lay.addWidget(self.pg_csv)
        btn_imp = QPushButton("IMPORTAR CSV")
        btn_imp.setStyleSheet(BTN_GREEN)
        btn_imp.clicked.connect(self._import_csv)
        lay.addWidget(btn_imp)
        lay.addStretch()
        return tab

    def _select_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar CSV", "", "CSV (*.csv *.tsv *.txt)")
        if path:
            self.txt_csv.setText(path)

    def _import_csv(self):
        csv_path = self.txt_csv.text().strip()
        if not csv_path:
            QMessageBox.warning(self, "Falta dato", "Selecciona un archivo CSV.")
            return
        f = self.pg_csv.fields
        err = _validate(f["host"].text(), f["port"].text(),
                        f["db"].text(), f["user"].text())
        if err:
            QMessageBox.warning(self, "Falta dato", err)
            return
        conn   = self._ensure_db_and_schema(f)
        table  = _sanitize_table_name(self.txt_csv_table.text().strip()) or \
                 _sanitize_table_name(os.path.splitext(os.path.basename(csv_path))[0])
        schema = f["schema"].text().strip() or "public"
        x_col  = self.txt_csv_x.text().strip()
        y_col  = self.txt_csv_y.text().strip()
        delim  = self.txt_csv_delim.text().strip() or ","
        epsg   = self.txt_csv_epsg.text().strip() or "4326"
        if x_col and y_col:
            src = ("CSV:" + csv_path + "?delimiter=" + delim + "&xField=" + x_col +
                   "&yField=" + y_col + "&a_srs=EPSG:" + epsg)
        else:
            src = csv_path
        cmd = [
            "ogr2ogr", "-f", "PostgreSQL", conn, src,
            "-nln", schema + "." + table,
            "-overwrite", "--config", "PG_USE_COPY", "YES"
        ]
        self._run_queue([cmd], "CSV", False, f["db"].text(), schema, [table], conn)

    # ── TAB XTF (simplificado - solo carga el archivo) ───────────────────────

    def _tab_xtf(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setSpacing(6)

        # ── estado de ili2pg ──────────────────────────────────────────────────
        self.lbl_jar_status = QLabel()
        self.lbl_jar_status.setWordWrap(True)
        self._update_jar_status()
        lay.addWidget(self.lbl_jar_status)

        # ── info IGAC ─────────────────────────────────────────────────────────
        info = QLabel(
            "Estandar IGAC - LADM-COL Colombia\n"
            "Modelo: LADM_COL automatico desde el XTF\n"
            "SRS: MAGNA-SIRGAS EPSG:9377  |  Schema: ladm_col"
        )
        info.setStyleSheet(
            "background:#e8f0fe;border:1px solid #4a7ab5;"
            "border-radius:6px;padding:6px;font-size:11px;color:#1a3a6b;"
        )
        info.setWordWrap(True)
        lay.addWidget(info)

        # separador
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color:#dce8f0;")
        lay.addWidget(line)

        # ── selector XTF ─────────────────────────────────────────────────────
        lbl_xtf = QLabel("Archivo XTF / ITF:")
        fnt = QFont()
        fnt.setBold(True)
        fnt.setPointSize(11)
        lbl_xtf.setFont(fnt)
        lay.addWidget(lbl_xtf)

        row_xtf = QHBoxLayout()
        self.txt_xtf = QLineEdit()
        self.txt_xtf.setPlaceholderText("/ruta/a/datos.xtf")
        self.txt_xtf.setMinimumHeight(28)
        btn_xtf = QPushButton("Seleccionar XTF...")
        btn_xtf.setMinimumHeight(28)
        btn_xtf.clicked.connect(self._select_xtf)
        row_xtf.addWidget(self.txt_xtf)
        row_xtf.addWidget(btn_xtf)
        lay.addLayout(row_xtf)

        # ── conexion PG ───────────────────────────────────────────────────────
        self.pg_xtf = self._pg_widget("xtf")
        self.pg_xtf.fields["schema"].setText(IGAC_SCHEMA)
        lay.addWidget(self.pg_xtf)

        # ── boton importar ────────────────────────────────────────────────────
        self.btn_xtf_imp = QPushButton("CARGAR XTF  →  PostgreSQL  (IGAC - LADM-COL)")
        self.btn_xtf_imp.setStyleSheet(BTN_ORANGE)
        self.btn_xtf_imp.setMinimumHeight(38)
        self.btn_xtf_imp.clicked.connect(self._import_xtf)
        lay.addWidget(self.btn_xtf_imp)

        lay.addStretch()
        return tab

    def _update_jar_status(self):
        jar = get_jar_path(self.plugin_dir)
        if jar:
            ver = os.path.basename(jar)
            self.lbl_jar_status.setText(
                "ili2pg  OK  -  " + ver
            )
            self.lbl_jar_status.setStyleSheet(
                "background:#d4edda;border:1px solid #4cae4c;"
                "border-radius:4px;padding:4px;color:#1a5c2a;font-weight:bold;"
            )
        else:
            self.lbl_jar_status.setText(
                "ili2pg " + ILI2PG_VERSION + " no esta instalado.\n"
                "Al hacer clic en CARGAR XTF se descargara automaticamente desde interlis.ch"
            )
            self.lbl_jar_status.setStyleSheet(
                "background:#fff3cd;border:1px solid #f0ad4e;"
                "border-radius:4px;padding:4px;color:#7a5c00;"
            )

    def _select_xtf(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo XTF", "",
            "INTERLIS (*.xtf *.XTF *.itf *.ITF *.xml)")
        if path:
            self.txt_xtf.setText(path)

    def _import_xtf(self):
        xtf = self.txt_xtf.text().strip()
        if not xtf:
            QMessageBox.warning(self, "Falta dato", "Selecciona un archivo XTF.")
            return
        if not os.path.isfile(xtf):
            QMessageBox.warning(self, "Archivo no encontrado",
                                "El archivo XTF seleccionado no existe.")
            return
        f = self.pg_xtf.fields
        err = _validate(f["host"].text(), f["port"].text(),
                        f["db"].text(), f["user"].text())
        if err:
            QMessageBox.warning(self, "Falta dato", err)
            return

        jar = get_jar_path(self.plugin_dir)
        if jar:
            self._run_xtf_import(jar, xtf, f)
        else:
            # Descargar ili2pg primero, luego importar
            self._log("Descargando ili2pg " + ILI2PG_VERSION + "...")
            self.progress.setVisible(True)
            self.btn_cancel.setVisible(False)
            self.btn_xtf_imp.setEnabled(False)
            self._dl_worker = JarDownloadWorker(self.plugin_dir, parent=self)
            self._dl_worker.progress.connect(self.log.append)
            self._dl_worker.finished_ok.connect(
                lambda jar_path: self._on_jar_downloaded(jar_path, xtf, f))
            self._dl_worker.finished_err.connect(self._on_jar_error)
            self._dl_worker.start()

    def _on_jar_downloaded(self, jar_path, xtf, f):
        self.progress.setVisible(False)
        self.btn_xtf_imp.setEnabled(True)
        self._update_jar_status()
        self._log("ili2pg listo: " + jar_path)
        self._run_xtf_import(jar_path, xtf, f)

    def _on_jar_error(self, msg):
        self.progress.setVisible(False)
        self.btn_xtf_imp.setEnabled(True)
        self._log("ERROR descargando ili2pg: " + msg)
        QMessageBox.critical(self, "Error al descargar ili2pg",
            "No se pudo descargar ili2pg automaticamente.\n\n"
            "Descargalo manualmente desde:\nhttps://interlis.ch/downloads\n\n"
            "Error: " + msg)

    def _run_xtf_import(self, jar, xtf, f):
        schema = f["schema"].text().strip() or IGAC_SCHEMA
        models = _detect_xtf_models(xtf)
        model_dir = get_model_dir(self.plugin_dir)
        conn = self._ensure_db_and_schema(f)

        epsg_ok, epsg_msg = _ensure_epsg_9377(conn)
        if epsg_ok:
            self._log("EPSG:9377 verificado en PostGIS")
        else:
            self._log("Aviso EPSG:9377: " + epsg_msg)

        uuid_ok, uuid_msg = _ensure_uuid_extension(conn)
        if uuid_ok:
            self._log("uuid-ossp verificado en PostGIS")
        else:
            self._log("Aviso uuid-ossp: " + uuid_msg)

        # Comando base ili2pg
        base = [
            _find_java(), "-jar", jar,
            "--dbhost",         f["host"].text(),
            "--dbport",         f["port"].text(),
            "--dbdatabase",     f["db"].text(),
            "--dbusr",          f["user"].text(),
            "--dbpwd",          f["pwd"].text(),
            "--dbschema",       schema,
            "--modeldir",       model_dir,
            "--smart1Inheritance",
            "--strokeArcs",
            "--log",            xtf + ".ili2pg.log"
        ]
        if models:
            base += ["--models", models]

        # Paso 1: crear estructura de tablas segun modelo del XTF
        cmd_schema = base + ["--defaultSrsAuth", "EPSG",
                             "--defaultSrsCode", IGAC_EPSG,
                             "--schemaimport", xtf]
        # Paso 2: cargar los datos del XTF
        cmd_import = base + ["--defaultSrsAuth", "EPSG",
                             "--defaultSrsCode", IGAC_EPSG,
                             "--import", xtf]

        self._log("=" * 60)
        self._log("XTF / INTERLIS  -  IGAC LADM-COL")
        self._log("Archivo : " + xtf)
        self._log("Schema  : " + schema)
        self._log("EPSG    : " + IGAC_EPSG + "  (MAGNA-SIRGAS)")
        self._log("ili2pg  : " + os.path.basename(jar))
        self._log("Modelos : " + (models or "No detectados"))
        self._log("Modeldir: " + model_dir)
        self._log("=" * 60)
        self._log("Paso 1: Creando estructura de tablas LADM-COL...")

        self.progress.setVisible(True)
        self.btn_cancel.setVisible(True)
        self.btn_xtf_imp.setEnabled(False)

        self._xtf_worker = XtfImportWorker([cmd_schema, cmd_import], parent=self)
        self._xtf_worker.line_ready.connect(self.log.append)
        self._xtf_worker.finished_ok.connect(self._on_xtf_ok)
        self._xtf_worker.finished_err.connect(self._on_xtf_err)
        self._xtf_worker.start()

    def _on_xtf_ok(self):
        self.progress.setVisible(False)
        self.btn_cancel.setVisible(False)
        self.btn_xtf_imp.setEnabled(True)
        self._log("=" * 60)
        self._log("XTF importado correctamente a PostgreSQL")
        self._log("=" * 60)
        QMessageBox.information(self, "Importacion XTF completada",
            "El archivo XTF fue importado correctamente a PostgreSQL.\n\n"
            "Schema: " + IGAC_SCHEMA + "\n"
            "EPSG: " + IGAC_EPSG + " (MAGNA-SIRGAS)\n\n"
            "Revisa el log para ver el detalle del proceso.")

    def _on_xtf_err(self, msg):
        self.progress.setVisible(False)
        self.btn_cancel.setVisible(False)
        self.btn_xtf_imp.setEnabled(True)
        self._log("ERROR XTF: " + msg)
        QMessageBox.critical(self, "Error en importacion XTF", msg)

    # ── TAB LOTE ──────────────────────────────────────────────────────────────

    def _tab_batch(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.addWidget(QLabel("Carpeta con archivos a importar en lote:"))
        row = QHBoxLayout()
        self.txt_batch_dir = QLineEdit()
        self.txt_batch_dir.setPlaceholderText("/ruta/a/carpeta")
        btn = QPushButton("Seleccionar carpeta...")
        btn.clicked.connect(self._select_batch)
        row.addWidget(self.txt_batch_dir)
        row.addWidget(btn)
        lay.addLayout(row)
        lay.addWidget(QLabel("Formatos a procesar:"))
        fmt_row = QHBoxLayout()
        self.chk_fmt_shp  = QCheckBox(".shp")
        self.chk_fmt_shp.setChecked(True)
        self.chk_fmt_gdb  = QCheckBox(".gdb")
        self.chk_fmt_gdb.setChecked(True)
        self.chk_fmt_json = QCheckBox(".geojson/.json")
        self.chk_fmt_kml  = QCheckBox(".kml")
        self.chk_fmt_csv  = QCheckBox(".csv")
        for c in (self.chk_fmt_shp, self.chk_fmt_gdb,
                  self.chk_fmt_json, self.chk_fmt_kml, self.chk_fmt_csv):
            fmt_row.addWidget(c)
        lay.addLayout(fmt_row)
        self.chk_batch_load = QCheckBox("Cargar capas en QGIS al terminar")
        self.chk_batch_load.setChecked(True)
        lay.addWidget(self.chk_batch_load)
        self.pg_batch = self._pg_widget("batch")
        lay.addWidget(self.pg_batch)
        btn_imp = QPushButton("PROCESAR CARPETA EN LOTE")
        btn_imp.setStyleSheet(BTN_GREEN)
        btn_imp.clicked.connect(self._import_batch)
        lay.addWidget(btn_imp)
        lay.addStretch()
        return tab

    def _select_batch(self):
        path = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta")
        if path:
            self.txt_batch_dir.setText(path)

    def _import_batch(self):
        folder = self.txt_batch_dir.text().strip()
        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(self, "Falta dato", "Selecciona una carpeta valida.")
            return
        f = self.pg_batch.fields
        err = _validate(f["host"].text(), f["port"].text(),
                        f["db"].text(), f["user"].text())
        if err:
            QMessageBox.warning(self, "Falta dato", err)
            return
        self._ensure_db_and_schema(f)
        exts = []
        if self.chk_fmt_shp.isChecked():
            exts.append(".shp")
        if self.chk_fmt_json.isChecked():
            exts += [".geojson", ".json"]
        if self.chk_fmt_kml.isChecked():
            exts.append(".kml")
        if self.chk_fmt_csv.isChecked():
            exts.append(".csv")
        include_gdb = self.chk_fmt_gdb.isChecked()
        from pathlib import Path as FPath
        p = FPath(folder)
        sources = []
        for ext in exts:
            sources += list(p.rglob("*" + ext))
        if include_gdb:
            sources += [d for d in p.rglob("*.gdb") if d.is_dir()]
        if not sources:
            QMessageBox.warning(self, "Sin archivos",
                "No se encontraron archivos con los formatos seleccionados.")
            return
        conn   = _pg_conn(f["host"].text(), f["port"].text(),
                          f["db"].text(), f["user"].text(), f["pwd"].text(),
                          _ssl_mode(f))
        schema = f["schema"].text().strip() or "public"
        tables = []
        cmds   = []
        for src in sources:
            if src.suffix.lower() == ".gdb" and src.is_dir():
                gdb_layers = _list_gdb_layers_sync(str(src))
                if not gdb_layers:
                    self._log("Aviso: no se encontraron capas en: " + str(src))
                    continue
                for layer in gdb_layers:
                    safe_table = _sanitize_table_name(layer)
                    tables.append(safe_table)
                    cmds.append([
                        "ogr2ogr", "-f", "PostgreSQL", conn, str(src),
                        "-nln", schema + "." + safe_table,
                        "-overwrite", "-progress", "-skipfailures",
                        "-nlt", "PROMOTE_TO_MULTI",
                        "-lco", "GEOMETRY_NAME=geom",
                        "--config", "PG_USE_COPY", "YES",
                        layer
                    ])
            else:
                table = _sanitize_table_name(src.stem)
                tables.append(table)
                cmds.append([
                    "ogr2ogr", "-f", "PostgreSQL", conn, str(src),
                    "-nln", schema + "." + table,
                    "-overwrite", "-progress", "-skipfailures",
                    "-nlt", "PROMOTE_TO_MULTI",
                    "-lco", "GEOMETRY_NAME=geom",
                    "--config", "PG_USE_COPY", "YES"
                ])
        self._log("Archivos encontrados: " + str(len(cmds)))
        label = "LOTE (" + str(len(cmds)) + " archivos)"
        self._run_queue(cmds, label, self.chk_batch_load.isChecked(),
                        f["db"].text(), schema, tables, conn)

    # ── TAB ACERCA DE ─────────────────────────────────────────────────────────

    def _tab_about(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setSpacing(10)

        lbl_logo = QLabel()
        logo_path = os.path.join(self.plugin_dir, "logo.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path).scaled(
                120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            lbl_logo.setPixmap(pix)
            lbl_logo.setAlignment(Qt.AlignCenter)
        lay.addWidget(lbl_logo)

        def sec(titulo, contenido, color="#1a3a6b"):
            lbl_t = QLabel(titulo)
            fnt = QFont()
            fnt.setBold(True)
            fnt.setPointSize(11)
            lbl_t.setFont(fnt)
            lbl_t.setStyleSheet("color:" + color + ";")
            lbl_c = QLabel(contenido)
            lbl_c.setWordWrap(True)
            lbl_c.setStyleSheet(
                "background:#f5f8ff;border:1px solid #c8d8f0;"
                "border-radius:4px;padding:8px;font-size:11px;")
            lay.addWidget(lbl_t)
            lay.addWidget(lbl_c)

        sec("GeoMigrator Pro  v1.0",
            "Plugin profesional para migracion de datos geoespaciales hacia "
            "PostgreSQL/PostGIS. Disenado para el contexto catastral colombiano "
            "con soporte al estandar IGAC - LADM-COL.")

        sec("Autor",
            "Jose Orlando Castillo Ospina\n"
            "  Ing. Agroecologo\n"
            "  Esp. Sistemas de Informacion Geografica\n"
            "  Esp. Gestion Ambiental\n"
            "  Cartografia y Catastro - Colombia\n\n"
            "Desarrollado con apoyo de IA:\n"
            "  Claude (Anthropic) y ChatGPT (OpenAI)")

        sec("Estandares aplicados",
            "- IGAC: Instituto Geografico Agustin Codazzi (Colombia)\n"
            "- LADM-COL: Land Administration Domain Model - Colombia\n"
            "- MAGNA-SIRGAS: Sistema de referencia oficial Colombia (EPSG:9377)\n"
            "- INTERLIS / XTF: estandar suizo adoptado por IGAC\n"
            "- ili2pg " + ILI2PG_VERSION + " (interlis.ch)\n"
            "- QGIS >= 3.22 / PostgreSQL + PostGIS / GDAL-OGR")

        sec("Licencia",
            "GNU General Public License v2.0 o posterior\n"
            "Software libre y de codigo abierto.")

        lay.addStretch()
        return tab

    def _check_dependencies(self):
        """Verifica dependencias externas al iniciar el plugin."""
        import shutil
        gdal = shutil.which("ogr2ogr") or shutil.which("ogrinfo")
        java = _find_java()
        if not gdal:
            if sys.platform == "darwin":
                tip = "Instala GDAL via Homebrew (brew install gdal) o conda."
            elif sys.platform == "win32":
                tip = "Instala OSGeo4W o GDAL desde gisinternals.com."
            else:
                tip = "Instala GDAL via tu gestor de paquetes (apt install gdal-bin, yum install gdal, etc.)."
            self._log("[AVISO] GDAL/OGR no encontrado. " + tip)
        else:
            self._log("[OK] GDAL/OGR detectado")
        if java == "java":
            if sys.platform == "darwin":
                tip = "Instala Java desde https://adoptium.net o via Homebrew (brew install openjdk)."
            elif sys.platform == "win32":
                tip = "Instala Java desde https://adoptium.net."
            else:
                tip = "Instala Java via tu gestor de paquetes (apt install default-jre, etc.)."
            self._log("[AVISO] Java no encontrado. " + tip)
        else:
            self._log("[OK] Java detectado: " + java)

    def _log(self, msg):
        """Agrega linea al log con timestamp."""
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        self.log.append("[" + ts + "] " + msg)

    # ── creacion automatica de BD / esquema ──────────────────────────────────

    def _ensure_db_and_schema(self, f):
        """Verifica que la BD y el esquema existan, creandolos si es necesario."""
        try:
            host = f["host"].text()
            port = f["port"].text()
            db   = f["db"].text()
            user = f["user"].text()
            pwd  = f["pwd"].text()
            ssl  = _ssl_mode(f)
            schema = f["schema"].text().strip() or "public"

            conn = _pg_conn(host, port, db, user, pwd, ssl)
            r = subprocess.run(
                ["ogrinfo", "-so", conn],
                capture_output=True, text=True,
                timeout=8, encoding="utf-8", errors="replace"
            )

            if r.returncode != 0:
                self._log("BD '" + db + "' no accesible. Intentando crearla...")
                ok, result = _create_pg_database(host, port, user, pwd, ssl, db)
                if ok:
                    f["db"].setText(result)
                    self._log("BD creada con exito: " + result)
                    conn = _pg_conn(host, port, result, user, pwd, ssl)
                else:
                    self._log("No se pudo crear la BD: " + result)

            if schema != "public":
                ok, msg = _create_pg_schema(conn, schema)
                if ok:
                    self._log("Esquema '" + schema + "' verificado/creado en PostgreSQL")
                else:
                    self._log("Aviso: no se pudo crear el esquema '" + schema + "': " + msg)
        except Exception as e:
            self._log("Aviso al verificar BD/esquema: " + str(e))
            conn = _pg_conn(f["host"].text(), f["port"].text(),
                            f["db"].text(), f["user"].text(), f["pwd"].text(),
                            _ssl_mode(f))

        return conn

    # ── motor de ejecucion generico ───────────────────────────────────────────

    def _run_queue(self, cmds, label, load_after, db, schema, tables, conn_str):
        if self._worker and self._worker.isRunning():
            QMessageBox.warning(self, "Proceso activo",
                                "Ya hay una importacion en curso.")
            return
        self._pending_cmds  = list(cmds)
        self._load_after    = load_after
        self._load_db       = db
        self._load_schema   = schema
        self._load_tables   = tables or []
        self._load_conn_str = conn_str
        self._label         = label
        self._total         = len(cmds)
        self._done          = 0
        self._errors        = []
        self._log("=" * 60)
        self._log("INICIANDO: " + label + "  (" + str(self._total) + " comando(s))")
        self._log("=" * 60)
        self.progress.setRange(0, max(self._total, 1))
        self.progress.setValue(0)
        if self._total > 0:
            self.progress.setFormat("  %v/%m  (%p%)")
        self.progress.setVisible(True)
        self.btn_cancel.setVisible(True)
        self._run_next()

    def _run_next(self):
        if not self._pending_cmds:
            self._finish_queue()
            return
        cmd = self._pending_cmds.pop(0)
        self._done += 1
        self.progress.setValue(self._done)
        step = "[" + str(self._done) + "/" + str(self._total) + "] "
        self._log("")
        self._log(step + _sanitize_cmd(cmd))
        self._worker = OgrWorker(cmd, parent=self)
        self._worker.line_ready.connect(self.log.append)
        self._worker.finished_ok.connect(self._on_step_ok)
        self._worker.finished_err.connect(self._on_step_err)
        self._worker.start()

    def _on_step_ok(self):
        self._log("OK - paso completado")
        self._run_next()

    def _on_step_err(self, msg):
        self._log("ERROR en paso: " + msg)
        self._errors.append(msg)
        self._run_next()

    def _finish_queue(self):
        self.progress.setVisible(False)
        self.btn_cancel.setVisible(False)
        self._log("=" * 60)
        if self._errors:
            self._log(self._label + " - COMPLETADO CON ERRORES")
            self._log("Errores: " + str(len(self._errors)))
        else:
            self._log(self._label + " - COMPLETADO")
        self._log("=" * 60)
        if self._errors:
            QMessageBox.warning(
                self, "Proceso completado con errores",
                self._label + " termino con " + str(len(self._errors)) +
                " error(es).\n\nRevisa el log para ver el detalle."
            )
            return
        self._save_pg_connection_in_qgis()
        if self._load_after and self.iface and self._load_tables:
            self._load_layers_in_qgis()
        else:
            QMessageBox.information(self, "Listo",
                                    self._label + " completado correctamente.")

    def _load_layers_in_qgis(self):
        loaded = 0
        conn_str = self._load_conn_str
        params = {}
        for part in conn_str.replace("PG:", "").split():
            if "=" in part:
                k, v = part.split("=", 1)
                params[k] = v
        for table in self._load_tables:
            uri = QgsDataSourceUri()
            uri.setParam("host", params.get("host", "localhost"))
            uri.setParam("port", params.get("port", "5432"))
            uri.setParam("dbname", params.get("dbname", ""))
            uri.setParam("user", params.get("user", ""))
            uri.setParam("password", params.get("password", ""))
            ssl = params.get("sslmode", "")
            if ssl:
                uri.setParam("sslmode", ssl)
            uri.setDataSource(self._load_schema, table, "geom")
            layer = QgsVectorLayer(uri.uri(False), table, "postgres")
            if layer.isValid():
                QgsProject.instance().addMapLayer(layer)
                loaded += 1
            else:
                self._log("Aviso: no se pudo cargar la capa: " + table)
        if loaded > 0:
            msg = (self._label + " completado.\n"
                   "Se cargaron " + str(loaded) + " capa(s) en QGIS.")
        else:
            msg = (self._label + " completado.\n"
                   "No se cargaron capas (puede que no tengan geometria).")
        QMessageBox.information(self, "Listo", msg)

    def _save_pg_connection_in_qgis(self):
        """Guarda la conexion PostgreSQL en el panel de Navegador de QGIS."""
        try:
            conn_str = self._load_conn_str
            params = {}
            for part in conn_str.replace("PG:", "").split():
                if "=" in part:
                    k, v = part.split("=", 1)
                    params[k] = v
            db = params.get("dbname", "")
            if not db:
                return
            settings = QgsSettings()
            prefix = "PostgreSQL/connections/" + db
            settings.beginGroup(prefix)
            settings.setValue("host", params.get("host", "localhost"))
            settings.setValue("port", params.get("port", "5432"))
            settings.setValue("database", db)
            settings.setValue("username", params.get("user", ""))
            settings.setValue("password", params.get("password", ""))
            settings.setValue("sslmode", params.get("sslmode", "disable"))
            settings.setValue("publicOnly", False)
            settings.setValue("geometryColumnsOnly", False)
            settings.setValue("dontResolveType", False)
            settings.setValue("estimatedMetadata", False)
            settings.setValue("savePassword", True)
            settings.setValue("allowGeometrylessTables", True)
            settings.setValue("service", "")
            settings.endGroup()
            self._log("Conexion guardada en QGIS: " + db)
        except Exception as e:
            self._log("Aviso al guardar conexion en QGIS: " + str(e))

    def _cancel(self):
        if self._xtf_worker and self._xtf_worker.isRunning():
            self._xtf_worker.cancel()
        if self._worker and self._worker.isRunning():
            self._pending_cmds = []
            self._worker.cancel()
        self._log("Cancelando proceso...")

    def _export_log(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar log", "geomigrator_log.txt", "Texto (*.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self.log.toPlainText())
            QMessageBox.information(self, "Log exportado",
                                    "Log guardado en:\n" + path)
