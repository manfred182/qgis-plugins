# -*- coding: utf-8 -*-
import re
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
        output_lines = []
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
                clean_line = line.rstrip()
                output_lines.append(clean_line)
                if self._cancelled:
                    break
                self.line_ready.emit(clean_line)
            self._proc.wait()
            ogr_errors = [
                line for line in output_lines
                if re.search(r"(?i)\b(error|failure|failed)\b", line)
            ]
            if self._cancelled:
                self.finished_err.emit("Proceso cancelado por el usuario.")
            elif self._proc.returncode == 0 and ogr_errors:
                self.finished_err.emit(
                    "ogr2ogr finalizo, pero reporto entidades omitidas o errores:\n" +
                    "\n".join(ogr_errors[-20:])
                )
            elif self._proc.returncode == 0:
                self.finished_ok.emit()
            else:
                detail = "\n".join(output_lines[-20:]).strip()
                suffix = ("\nDetalle de ogr2ogr:\n" + detail) if detail else ""
                self.finished_err.emit(
                    "ogr2ogr termino con codigo " + str(self._proc.returncode) + suffix
                )
        except FileNotFoundError:
            self.finished_err.emit(
                "ogr2ogr no encontrado. Verifica que GDAL este instalado y en el PATH."
            )
        except Exception as exc:
            self.finished_err.emit(str(exc))
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
                ["ogrinfo", "-ro", self.source],
                capture_output=True, text=True,
                encoding="utf-8", errors="replace"
            )
            if result.returncode != 0:
                self.error.emit(
                    result.stderr.strip() or result.stdout.strip() or
                    "ogrinfo termino con codigo " + str(result.returncode)
                )
                return
            layers = []
            for line in result.stdout.splitlines():
                if line.startswith("Layer name:"):
                    layers.append(line.split(":", 1)[1].strip())
                    continue
                match = re.match(
                    r"^\s*\d+:\s+(.+?)(?:\s+\([^()]*(?:\([^()]*\)[^()]*)*\))?\s*$",
                    line
                )
                if match:
                    layers.append(match.group(1).strip())
            self.layers_ready.emit(list(dict.fromkeys(layers)))
        except FileNotFoundError:
            self.error.emit("ogrinfo no encontrado. Verifica GDAL/OGR en el PATH.")
        except Exception as exc:
            self.error.emit(str(exc))
