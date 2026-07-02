# -*- coding: utf-8 -*-
import os
import re
import subprocess
import sys

from qgis.PyQt.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QCheckBox, QMessageBox, QInputDialog
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QFont

from .profiles import ProfileManager


BTN_BLUE = "font-weight:bold;padding:6px;background:#1a4a8a;color:white;border-radius:4px;"


def _sanitize_cmd_password(cmd):
    """Reemplaza la contrasena en un comando antes de mostrarlo en log."""
    result = []
    for arg in cmd:
        if "password=" in arg.lower():
            parts = arg.split("password=", 1)
            result.append(parts[0] + "password=****")
        else:
            result.append(arg)
    return " ".join(result)


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


def pg_conn_string(host, port, db, user, pwd, ssl_mode=""):
    ssl = " sslmode=" + ssl_mode if ssl_mode else ""
    return ("PG:host=" + host + " port=" + port +
            " dbname=" + db + " user=" + user + " password=" + pwd + ssl)


def ogr_conn_string(host, port, db, user, pwd, ssl_mode=""):
    ssl = " sslmode=" + ssl_mode if ssl_mode else ""
    return ("host=" + host + " port=" + port +
            " dbname=" + db + " user=" + user + " password=" + pwd + ssl)


def _find_java():
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


class PgConnectionWidget(QGroupBox):

    def __init__(self, plugin_dir, parent=None):
        super().__init__("Conexion PostgreSQL", parent)
        self.plugin_dir = plugin_dir
        self.profiles = ProfileManager(plugin_dir)
        self.fields = {}
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(4)

        prof_row = QHBoxLayout()
        self.combo = QComboBox()
        self.combo.addItem("-- Seleccionar perfil --")
        self.combo.addItems(self.profiles.names())
        btn_load = QPushButton("Cargar")
        btn_save = QPushButton("Guardar")
        btn_del = QPushButton("Eliminar")
        for b in (btn_load, btn_save, btn_del):
            b.setStyleSheet(BTN_BLUE)
            b.setFixedWidth(72)
        prof_row.addWidget(QLabel("Perfil:"))
        prof_row.addWidget(self.combo, 1)
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

        self.fields["host"] = field(0, 0, "Host", "localhost", "localhost",
                                    tip="Direccion del servidor PostgreSQL (ej: localhost, 192.168.1.10)")
        self.fields["port"] = field(0, 1, "Puerto", "5432", "5432",
                                    tip="Puerto de PostgreSQL (default: 5432)")
        self.fields["db"] = field(1, 0, "Base de datos", "mi_base",
                                  tip="Nombre de la base de datos destino")
        self.fields["user"] = field(1, 1, "Usuario", "postgres", "postgres",
                                    tip="Usuario de PostgreSQL")
        self.fields["pwd"] = field(2, 0, "Contrasena", "........", echo=QLineEdit.Password,
                                   tip="Contrasena del usuario PostgreSQL")
        self.fields["schema"] = field(2, 1, "Schema", "public", "public",
                                      tip="Schema de PostgreSQL donde se crearan las tablas")
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        lay.addLayout(grid)

        ssl_row = QHBoxLayout()
        self.fields["ssl"] = QCheckBox("Usar SSL")
        self.fields["ssl"].setToolTip("Activar conexion SSL/TLS con PostgreSQL")
        ssl_row.addWidget(self.fields["ssl"])
        ssl_row.addStretch()
        btn_test = QPushButton("Probar conexion")
        btn_test.setStyleSheet(BTN_BLUE)
        btn_test.clicked.connect(self._test_conn)
        ssl_row.addWidget(btn_test, 1)
        lay.addLayout(ssl_row)

        create_row = QHBoxLayout()
        create_row.addStretch()
        btn_create_db = QPushButton("Crear BD en PostgreSQL...")
        btn_create_db.setStyleSheet("font-weight:bold;padding:5px 10px;background:#2a6b3c;color:white;border-radius:3px;")
        btn_create_db.clicked.connect(self._create_db_dialog)
        create_row.addWidget(btn_create_db)
        lay.addLayout(create_row)

        btn_load.clicked.connect(self._load_profile)
        btn_save.clicked.connect(self._save_profile)
        btn_del.clicked.connect(self._delete_profile)

    def refresh_profiles(self):
        current = self.combo.currentText()
        self.combo.blockSignals(True)
        self.combo.clear()
        self.combo.addItem("-- Seleccionar perfil --")
        self.combo.addItems(self.profiles.names())
        idx = self.combo.findText(current)
        self.combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.combo.blockSignals(False)

    def ssl_mode(self):
        cb = self.fields.get("ssl")
        if cb and hasattr(cb, "isChecked"):
            return "require" if cb.isChecked() else ""
        return ""

    def pg_conn(self):
        return pg_conn_string(
            self.fields["host"].text(),
            self.fields["port"].text(),
            self.fields["db"].text(),
            self.fields["user"].text(),
            self.fields["pwd"].text(),
            self.ssl_mode()
        )

    def ogr_conn(self):
        return ogr_conn_string(
            self.fields["host"].text(),
            self.fields["port"].text(),
            self.fields["db"].text(),
            self.fields["user"].text(),
            self.fields["pwd"].text(),
            self.ssl_mode()
        )

    def validate(self):
        return _validate(
            self.fields["host"].text(),
            self.fields["port"].text(),
            self.fields["db"].text(),
            self.fields["user"].text()
        )

    def get_values(self):
        return {
            "host": self.fields["host"].text(),
            "port": self.fields["port"].text(),
            "db": self.fields["db"].text(),
            "user": self.fields["user"].text(),
            "pwd": self.fields["pwd"].text(),
            "schema": self.fields["schema"].text().strip() or "public",
            "ssl": self.ssl_mode()
        }

    def _load_profile(self):
        name = self.combo.currentText()
        if name.startswith("--"):
            return
        p = self.profiles.get(name)
        self.fields["host"].setText(p.get("host", ""))
        self.fields["port"].setText(p.get("port", "5432"))
        self.fields["db"].setText(p.get("db", ""))
        self.fields["user"].setText(p.get("user", ""))
        self.fields["pwd"].setText(p.get("pwd", ""))
        self.fields["schema"].setText(p.get("schema", "public"))
        cb = self.fields.get("ssl")
        if cb and hasattr(cb, "setChecked"):
            cb.setChecked(p.get("ssl", False))

    def _save_profile(self):
        name, ok = QInputDialog.getText(self, "Guardar perfil", "Nombre del perfil:")
        if not ok or not name.strip():
            return
        ssl_val = self.fields["ssl"].isChecked() if "ssl" in self.fields else False
        self.profiles.save(
            name.strip(),
            self.fields["host"].text(),
            self.fields["port"].text(),
            self.fields["db"].text(),
            self.fields["user"].text(),
            self.fields["pwd"].text(),
            self.fields["schema"].text(),
            ssl_val
        )
        self.refresh_profiles()
        QMessageBox.information(self, "Perfil guardado", "Perfil guardado: " + name.strip())

    def _delete_profile(self):
        name = self.combo.currentText()
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
        self.refresh_profiles()

    def _test_conn(self):
        err = self.validate()
        if err:
            QMessageBox.warning(self, "Falta dato", err)
            return
        conn = self.pg_conn()
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

    def _create_db_dialog(self):
        err = self.validate()
        if err:
            QMessageBox.warning(self, "Falta dato", err)
            return
        name, ok = QInputDialog.getText(
            self, "Crear base de datos",
            "Nombre de la nueva base de datos:")
        if not ok or not name.strip():
            return
        ok_result, result = self._create_pg_database(name.strip())
        if ok_result:
            self.fields["db"].setText(result)
            QMessageBox.information(
                self, "BD creada",
                "Base de datos creada:\n" + result +
                "\n\nPostGIS y uuid-ossp activados.")
        else:
            QMessageBox.critical(
                self, "Error", "No se pudo crear la BD:\n" + result)

    def _create_pg_database(self, db_name):
        safe = re.sub(r'[^a-z0-9_]', '', db_name.strip().lower())
        if not safe:
            return False, "Nombre de base de datos invalido"
        if safe[0].isdigit():
            safe = "db_" + safe

        vals = self.get_values()
        conn_maint = pg_conn_string(vals["host"], vals["port"], "postgres",
                                    vals["user"], vals["pwd"], vals["ssl"])
        sql_create = 'CREATE DATABASE "' + safe + '" WITH ENCODING \'UTF8\' OWNER "' + vals["user"] + '"'
        r = subprocess.run(
            ["ogrinfo", conn_maint, "-sql", sql_create],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace"
        )
        if r.returncode != 0:
            return False, r.stderr.strip() or r.stdout.strip()

        conn_new = pg_conn_string(vals["host"], vals["port"], safe,
                                  vals["user"], vals["pwd"], vals["ssl"])
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

    def _create_pg_schema(self, schema):
        """Crea un esquema en PostgreSQL si no existe."""
        if not schema or schema == "public":
            return True, ""
        sql = 'CREATE SCHEMA IF NOT EXISTS "' + schema + '"'
        conn = self.pg_conn()
        r = subprocess.run(
            ["ogrinfo", conn, "-sql", sql],
            capture_output=True, text=True, timeout=20,
            encoding="utf-8", errors="replace"
        )
        if r.returncode != 0:
            return False, r.stderr.strip() or r.stdout.strip()
        return True, ""

    def ensure_db_and_schema(self):
        """Verifica que la BD y el esquema existan, creandolos si es necesario."""
        vals = self.get_values()

        conn = self.pg_conn()
        r = subprocess.run(
            ["ogrinfo", "-so", conn],
            capture_output=True, text=True,
            timeout=8, encoding="utf-8", errors="replace"
        )

        if r.returncode != 0:
            db = vals["db"]
            ok_result, result = self._create_pg_database(db)
            if ok_result:
                self.fields["db"].setText(result)

        schema = vals["schema"]
        if schema != "public":
            self._create_pg_schema(schema)
