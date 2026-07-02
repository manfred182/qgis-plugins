# -*- coding: utf-8 -*-
"""
Worker para descarga de ili2pg y ejecucion de importacion XTF.
"""
import subprocess
from qgis.PyQt.QtCore import QThread, pyqtSignal
from .ili2pg_manager import download_jar, get_jar_path


class JarDownloadWorker(QThread):
    """Descarga ili2pg.jar en segundo plano."""
    progress    = pyqtSignal(str)
    finished_ok = pyqtSignal(str)   # ruta al JAR
    finished_err = pyqtSignal(str)

    def __init__(self, plugin_dir, parent=None):
        super().__init__(parent)
        self.plugin_dir = plugin_dir

    def run(self):
        try:
            jar = download_jar(self.plugin_dir, self.progress.emit)
            self.finished_ok.emit(jar)
        except Exception as e:
            self.finished_err.emit(str(e))


class XtfImportWorker(QThread):
    """Ejecuta ili2pg (schemaimport + import) en segundo plano."""
    line_ready   = pyqtSignal(str)
    finished_ok  = pyqtSignal()
    finished_err = pyqtSignal(str)

    def __init__(self, cmds, parent=None):
        super().__init__(parent)
        self.cmds       = cmds   # lista de comandos a ejecutar en orden
        self._proc      = None
        self._cancelled = False

    def run(self):
        for cmd in self.cmds:
            if self._cancelled:
                self.finished_err.emit("Cancelado por el usuario.")
                return
            try:
                self._proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace"
                )
                for line in self._proc.stdout:
                    if self._cancelled:
                        self._proc.terminate()
                        self.finished_err.emit("Cancelado por el usuario.")
                        return
                    self.line_ready.emit(line.rstrip())
                self._proc.wait()
                if self._proc.returncode != 0:
                    self.finished_err.emit(
                        "ili2pg termino con codigo " + str(self._proc.returncode)
                    )
                    return
            except FileNotFoundError:
                self.finished_err.emit(
                    "Java no encontrado. Instala Java y asegurate que este en el PATH."
                )
                return
            except Exception as e:
                self.finished_err.emit(str(e))
                return
        self.finished_ok.emit()

    def cancel(self):
        self._cancelled = True
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
