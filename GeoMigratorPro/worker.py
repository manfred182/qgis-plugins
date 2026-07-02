# -*- coding: utf-8 -*-
import subprocess
from qgis.PyQt.QtCore import QThread, pyqtSignal


class OgrWorker(QThread):
    line_ready   = pyqtSignal(str)
    finished_ok  = pyqtSignal()
    finished_err = pyqtSignal(str)

    def __init__(self, cmd, parent=None):
        super().__init__(parent)
        self.cmd        = cmd
        self._proc      = None
        self._cancelled = False

    def run(self):
        try:
            self._proc = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            for line in self._proc.stdout:
                if self._cancelled:
                    break
                self.line_ready.emit(line.rstrip())
            self._proc.wait()
            if self._cancelled:
                self.finished_err.emit("Proceso cancelado por el usuario.")
            elif self._proc.returncode == 0:
                self.finished_ok.emit()
            else:
                self.finished_err.emit(
                    "ogr2ogr termino con codigo " + str(self._proc.returncode)
                )
        except FileNotFoundError:
            self.finished_err.emit(
                "ogr2ogr no encontrado. Verifica que GDAL este instalado y en el PATH."
            )
        except Exception as e:
            self.finished_err.emit(str(e))

    def cancel(self):
        self._cancelled = True
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()


class OgrInfoWorker(QThread):
    layers_ready = pyqtSignal(list)
    error        = pyqtSignal(str)

    def __init__(self, source, parent=None):
        super().__init__(parent)
        self.source = source

    def run(self):
        try:
            result = subprocess.run(
                ["ogrinfo", "-al", "-so", self.source],
                capture_output=True, text=True,
                encoding="utf-8", errors="replace"
            )
            layers = []
            for line in result.stdout.splitlines():
                if line.startswith("Layer name:"):
                    layers.append(line.split(":", 1)[1].strip())
            self.layers_ready.emit(layers)
        except Exception as e:
            self.error.emit(str(e))


