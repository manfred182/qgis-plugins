"""
merge_dialog.py  –  Consolidación / Merge catastral
Herramienta Catastral IGAC

Combina en UNA sola capa (memoria) los Terrenos urbanos + rurales, unifica los
codigos de manzana y vereda, materializa el NOMBRE de la vereda y adjunta R1 y R2
(tablas alfanumericas) como joins virtuales de QGIS por el codigo predial.

  • Terreno Urbano + Terreno Rural  → capa consolidada con campo ORIGEN (URBANO/RURAL)
  • Manzanas + Veredas              → MANZANA_VEREDA_CODIGO y NOMBRE_VEREDA
  • R1 / R2                         → joins virtuales por código predial (prefijos R1_ / R2_)

El código territorial (MANZANA_VEREDA_CODIGO) se toma del campo propio del
terreno (MANZANA_CODIGO / VEREDA_CODIGO) cuando existe —terrenos formales—; si
el predio no lo trae —terrenos informales—, se asigna por UBICACIÓN ESPACIAL:
se busca la manzana (urbano) o vereda (rural) que contiene al terreno y se copia
su código. En veredas también se materializa el NOMBRE.

La capa resultante conserva los nombres reales de los campos, de modo que el resto
del plugin (detección de prefijos de join, filtros, Excel) funciona sobre ella igual
que sobre las capas originales con joins.
"""

import os
from datetime import date

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox,
    QPushButton, QLineEdit, QFrame, QMessageBox, QPlainTextEdit, QProgressBar,
    QWidget, QScrollArea, QApplication, QFileDialog,
)
from qgis.PyQt.QtCore import Qt, QVariant
from qgis.PyQt.QtGui import QColor
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsField, QgsFeature, QgsGeometry, QgsWkbTypes,
    QgsVectorLayerJoinInfo, QgsCoordinateTransform, QgsSpatialIndex,
    QgsRectangle, QgsFillSymbol, QgsRendererCategory, QgsCategorizedSymbolRenderer,
    QgsLinePatternFillSymbolLayer, QgsSimpleLineSymbolLayer,
)

from .consultas_dialog import (
    C, _OMISSIONS_COUNT_PROPERTY, _OMISSIONS_LAYER_PROPERTY,
    _OMISSIONS_TABLE_PROPERTY, _QUERY_RESULT_PROPERTY,
    _btn, _cbo, _inp, _sec, _lbl,
)


# ─────────────────────────────────────────────────────────────────────────────
#  Utilidades de detección de campos
# ─────────────────────────────────────────────────────────────────────────────

# Candidatos por rol. El primero que aparezca en la capa gana. Se prueba
# coincidencia exacta (sin mayúsculas) y luego terminación (join con prefijo).
_PREDIAL_CANDS = [
    'CODIGO', 'codigo', 'COD_PRED', 'CODIGO_PREDIAL', 'CODIGO PREDIAL',
    'NoPredial', 'NUMERO_PREDIAL', 'NUMERO PREDIAL', 'NUMEROPREDIAL',
    'NUMERO_PREDIAL_NACIONAL', 'NUM_PREDIAL', 'NUPRE', 'PREDIAL',
]
_RECORD_PREDIAL_CANDS = [
    'NUMERO PREDIAL', 'NÚMERO PREDIAL', 'NUMERO_PREDIAL', 'NUMEROPREDIAL',
    'NUMERO_PREDIAL_NACIONAL', 'NoPredial', 'NUM_PREDIAL', 'NUPRE',
    'CODIGO_PREDIAL', 'CODIGO PREDIAL', 'COD_PRED', 'PREDIAL', 'CODIGO',
]
_VEREDA_COD_CANDS = ['VEREDA_CODIGO', 'vereda_codigo', 'COD_VEREDA', 'CODIGO_VEREDA',
                     'VER_COD', 'COD_VER', 'VEREDA']
_MANZANA_COD_CANDS = ['MANZANA_CODIGO', 'manzana_codigo', 'COD_MANZANA',
                      'CODIGO_MANZANA', 'MAN_COD', 'COD_MAN', 'MANZANA']
_TERRITORIAL_COD_CANDS = _MANZANA_COD_CANDS + _VEREDA_COD_CANDS
_VEREDA_NOM_CANDS = ['NOMBRE_VEREDA', 'NOM_VEREDA', 'NOMBRE', 'nombre',
                     'NOM_VERED', 'VEREDA_NOMBRE', 'NOMVEREDA']
_JOIN_KEY = 'GC_PREDIAL_KEY'


def _simple_name(value):
    """Normaliza nombres de capas/campos para detección tolerante."""
    text = str(value or '').lower()
    replacements = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'ü': 'u', 'ñ': 'n',
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return ''.join(ch for ch in text if ch.isalnum())


def _pick_layer_name(layer_names, role):
    """Elige dentro de una GDB la capa que mejor corresponde a un rol IGAC."""
    exact = {
        'urban': ('uterreno', 'terrenourbano', 'urbanoterreno'),
        'rural': ('rterreno', 'terrenorural', 'ruralterreno'),
        'urban_informal': ('uterrenoinformal', 'terrenourbanoinformal'),
        'rural_informal': ('rterrenoinformal', 'terrenoruralinformal'),
        'urban_construction': ('uconstruccion', 'construccionurbana', 'urbanoconstruccion'),
        'rural_construction': ('rconstruccion', 'construccionrural', 'ruralconstruccion'),
        'urban_construction_informal': (
            'uconstruccioninformal', 'construccionurbanoinformal'),
        'rural_construction_informal': (
            'rconstruccioninformal', 'construccionruralinformal'),
        'vereda': ('rvereda', 'vereda', 'veredas'),
        'manzana': ('umanzana', 'manzana', 'manzanas'),
    }
    best = None
    best_score = 0
    for layer_name in layer_names:
        normalized = _simple_name(layer_name)
        score = 0
        if normalized in exact.get(role, ()):
            score = 100
        elif role == 'urban':
            if 'informal' in normalized:
                score = 0
            elif 'terreno' in normalized and ('urbano' in normalized or normalized.endswith('uterreno')):
                score = 80
            elif 'terreno' in normalized and normalized.startswith('u') and 'rural' not in normalized:
                score = 60
        elif role == 'rural':
            if 'informal' in normalized:
                score = 0
            elif 'terreno' in normalized and ('rural' in normalized or normalized.endswith('rterreno')):
                score = 80
            elif 'terreno' in normalized and normalized.startswith('r') and 'urbano' not in normalized:
                score = 60
        elif role == 'urban_informal':
            if ('terreno' in normalized and 'informal' in normalized
                    and ('urbano' in normalized or 'uterreno' in normalized)):
                score = 90
        elif role == 'rural_informal':
            if ('terreno' in normalized and 'informal' in normalized
                    and ('rural' in normalized or 'rterreno' in normalized)):
                score = 90
        elif role == 'urban_construction':
            if 'informal' in normalized:
                score = 0
            elif 'construccion' in normalized and ('urbano' in normalized or normalized.endswith('uconstruccion')):
                score = 80
            elif 'construccion' in normalized and normalized.startswith('u') and 'rural' not in normalized:
                score = 60
        elif role == 'rural_construction':
            if 'informal' in normalized:
                score = 0
            elif 'construccion' in normalized and ('rural' in normalized or normalized.endswith('rconstruccion')):
                score = 80
            elif 'construccion' in normalized and normalized.startswith('r') and 'urbano' not in normalized:
                score = 60
        elif role == 'urban_construction_informal':
            if ('construccion' in normalized and 'informal' in normalized
                    and ('urbano' in normalized or 'uconstruccion' in normalized)):
                score = 90
        elif role == 'rural_construction_informal':
            if ('construccion' in normalized and 'informal' in normalized
                    and ('rural' in normalized or 'rconstruccion' in normalized)):
                score = 90
        elif role == 'vereda' and 'vereda' in normalized:
            score = 90 if normalized.endswith('rvereda') else 70
        elif role == 'manzana' and 'manzana' in normalized:
            score = 90 if normalized.endswith('umanzana') else 70
        if score > best_score:
            best = layer_name
            best_score = score
    return best


def _ogr_sublayer_names(path):
    """Lista las capas/tablas de una fuente OGR sin cargarlas al proyecto."""
    try:
        from osgeo import ogr
        dataset = ogr.Open(path, 0)
        if dataset is not None:
            names = []
            for index in range(dataset.GetLayerCount()):
                layer = dataset.GetLayer(index)
                if layer is not None:
                    names.append(layer.GetName())
            dataset = None
            if names:
                return names
    except Exception:
        pass

    # Compatibilidad con instalaciones donde osgeo no está expuesto a Python.
    try:
        probe = QgsVectorLayer(path, '_geocatastro_probe_', 'ogr')
        provider = probe.dataProvider()
        names = []
        for descriptor in provider.subLayers() if provider is not None else []:
            parts = descriptor.split('!!::!!')
            if len(parts) > 1 and parts[1]:
                names.append(parts[1])
        return names
    except Exception:
        return []


def _resolve(layer, candidates):
    """Nombre real del campo en la capa para la lista de candidatos, o None."""
    if layer is None:
        return None
    names = [f.name() for f in layer.fields()]
    low = {n.lower(): n for n in names}
    # 1. exacto (con o sin mayúsculas)
    for c in candidates:
        if c in names:
            return c
        if c.lower() in low:
            return low[c.lower()]
    # 2. terminación (campo con prefijo de join, p.ej. "..._VEREDA_CODIGO")
    for c in candidates:
        cl = c.lower()
        for n in names:
            nl = n.lower()
            if nl.endswith(cl) and len(nl) > len(cl):
                return n
    # 3. comparación sin espacios, guiones, tildes ni signos.
    simplified = {_simple_name(n): n for n in names}
    for candidate in candidates:
        key = _simple_name(candidate)
        if key in simplified:
            return simplified[key]
    for candidate in candidates:
        key = _simple_name(candidate)
        for name in names:
            normalized = _simple_name(name)
            if normalized.endswith(key) and len(normalized) > len(key):
                return name
    return None


def _norm_code(value):
    """Normaliza un código para comparar (str, sin espacios, sin .0 flotante)."""
    if value is None:
        return ''
    try:
        # 5.0 -> "5"  ;  evita que enteros leídos como float no casen
        if isinstance(value, float) and value.is_integer():
            value = int(value)
    except (TypeError, ValueError, AttributeError):
        pass
    return str(value).strip()


def _norm_predial_code(value):
    """Genera una llave comparable entre GDB, R1 y R2 aunque cambie el formato."""
    text = _norm_code(value)
    if not text:
        return ''
    if text.endswith('.0') and text[:-2].isdigit():
        text = text[:-2]
    return ''.join(ch for ch in text.upper() if ch.isalnum())


def _representative_point(geom):
    """Punto garantizado dentro del polígono (o su centroide como respaldo)."""
    if geom is None or geom.isNull():
        return None
    point = geom.pointOnSurface()
    if point is None or point.isNull():
        point = geom.centroid()
    if point is None or point.isNull():
        return None
    return point


class _TerritorialLocator:
    """Índice espacial de una capa de manzanas o veredas.

    Permite asignar el CÓDIGO (y, en veredas, el NOMBRE) de la unidad
    territorial al terreno que cae dentro de cada polígono. Se usa para los
    predios que no traen el código en su tabla —típicamente los terrenos
    informales (U_TERRENO_INFORMAL / R_TERRENO_INFORMAL)—.
    """

    def __init__(self, layer, code_field, name_field=None):
        self.crs = layer.crs()
        self.index = QgsSpatialIndex()
        self.data = {}   # fid -> (codigo, nombre, geometría)
        for feat in layer.getFeatures():
            geom = feat.geometry()
            if geom is None or geom.isNull():
                continue
            try:
                self.index.addFeature(feat)
            except AttributeError:   # QGIS antiguo
                self.index.insertFeature(feat)
            codigo = _norm_code(feat[code_field]) if code_field else ''
            nombre = _norm_code(feat[name_field]) if name_field else ''
            self.data[feat.id()] = (codigo, nombre, QgsGeometry(geom))

    def locate(self, geom, transform=None):
        """(codigo, nombre) del polígono que contiene a geom; ('', '') si ninguno."""
        point = _representative_point(geom)
        if point is None:
            return ('', '')
        if transform is not None:
            point = QgsGeometry(point)
            try:
                point.transform(transform)
            except Exception:   # noqa: BLE001 – geometría fuera de dominio
                return ('', '')
        p = point.asPoint()
        rect = QgsRectangle(p.x(), p.y(), p.x(), p.y())
        for fid in self.index.intersects(rect):
            codigo, nombre, poly = self.data.get(fid, ('', '', None))
            if poly is not None and poly.contains(point):
                return (codigo, nombre)
        # Sin contención exacta (predio en el borde o con holgura): el más cercano.
        nearest = self.index.nearestNeighbor(p, 1)
        if nearest:
            codigo, nombre, _poly = self.data.get(nearest[0], ('', '', None))
            return (codigo, nombre)
        return ('', '')


# ─────────────────────────────────────────────────────────────────────────────
#  Diálogo
# ─────────────────────────────────────────────────────────────────────────────

class MergeConsolidacionDialog(QDialog):
    """Consolida Terrenos + Manzana/Vereda + R1/R2 en una capa de memoria."""

    _NONE_DATA = '__none__'

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self._direct_paths = {'gdb': '', 'r1': '', 'r2': ''}
        self._direct_processing = False
        self.setWindowTitle('Consolidar / Merge catastral')
        self.setMinimumWidth(560)
        self.setStyleSheet(f'background:{C["bg"]};color:{C["text"]};')
        self._build_ui()
        self._reload_layers()

    # ── Construcción de UI ──────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # Cabecera
        head = QFrame()
        head.setStyleSheet(
            f"QFrame{{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {C['primary']},stop:1 #8e44ad);border-radius:8px;}}")
        head.setFixedHeight(44)
        hl = QHBoxLayout(head); hl.setContentsMargins(14, 0, 14, 0)
        ic = QLabel('🔗'); ic.setStyleSheet('font-size:20px;background:transparent;')
        hl.addWidget(ic)
        tc = QVBoxLayout(); tc.setSpacing(0)
        tc.addWidget(QLabel('Consolidar / Merge',
                            styleSheet='color:white;font-size:13px;font-weight:bold;background:transparent;'))
        tc.addWidget(QLabel('Terrenos + Construcciones + Manzana/Vereda + R1/R2',
                            styleSheet='color:rgba(255,255,255,0.85);font-size:9px;background:transparent;'))
        hl.addLayout(tc, 1)
        root.addWidget(head)

        # Cuerpo con scroll
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f'background:{C["bg"]};border:none;')
        inner = QWidget(); inner.setStyleSheet(f'background:{C["bg"]};')
        body = QVBoxLayout(inner); body.setContentsMargins(2, 2, 2, 2); body.setSpacing(6)

        # ── Flujo directo (no altera el flujo manual existente) ──
        direct = QFrame()
        direct.setStyleSheet(
            f"QFrame{{background:{C['info_bg']};border:1px solid {C['secondary']};"
            f"border-radius:5px;}}")
        direct_lo = QVBoxLayout(direct)
        direct_lo.setContentsMargins(8, 7, 8, 7)
        direct_lo.setSpacing(5)
        direct_text = QLabel(
            'Carga directa: selecciona la geodatabase (.gdb), R1 y R2. '
            'La herramienta detecta terrenos, construcciones, U_MANZANA y '
            'R_VEREDA, crea una sola capa categorizada y la deja activa para consultar.')
        direct_text.setWordWrap(True)
        direct_text.setStyleSheet(
            f'font-size:10px;color:{C["primary"]};background:transparent;border:none;')
        direct_lo.addWidget(direct_text)

        direct_grid = QGridLayout()
        direct_grid.setHorizontalSpacing(6)
        direct_grid.setVerticalSpacing(4)
        self.inp_direct_gdb = _inp('Ninguna geodatabase seleccionada')
        self.inp_direct_r1 = _inp('Ningún archivo R1 seleccionado')
        self.inp_direct_r2 = _inp('Ningún archivo R2 seleccionado')
        self.btn_pick_gdb = _btn('📂 Seleccionar', primary=False, small=True)
        self.btn_pick_r1 = _btn('📄 Seleccionar', primary=False, small=True)
        self.btn_pick_r2 = _btn('📄 Seleccionar', primary=False, small=True)
        direct_rows = (
            ('Geodatabase', self.inp_direct_gdb, self.btn_pick_gdb),
            ('Registro R1', self.inp_direct_r1, self.btn_pick_r1),
            ('Registro R2', self.inp_direct_r2, self.btn_pick_r2),
        )
        for row, (label, line_edit, button) in enumerate(direct_rows):
            line_edit.setReadOnly(True)
            direct_grid.addWidget(_lbl(label), row, 0)
            direct_grid.addWidget(line_edit, row, 1)
            direct_grid.addWidget(button, row, 2)
        direct_grid.setColumnStretch(1, 1)
        direct_lo.addLayout(direct_grid)

        self.lbl_direct_status = QLabel('Selecciona los tres insumos en el orden que prefieras.')
        self.lbl_direct_status.setStyleSheet(
            f'font-size:9px;color:{C["primary"]};background:transparent;border:none;')
        direct_lo.addWidget(self.lbl_direct_status)
        self.btn_direct = _btn('⚡  Crear capa unificada y consultar', color='#8e44ad')
        self.btn_direct.setEnabled(False)
        direct_lo.addWidget(self.btn_direct)
        body.addWidget(direct)

        # ── Capas de entrada ──
        body.addWidget(_sec('Configuración manual (opcional)'))
        grid = QGridLayout(); grid.setHorizontalSpacing(8); grid.setVerticalSpacing(4)
        self.cbo_urb  = _cbo()
        self.cbo_rur  = _cbo()
        self.cbo_urb_inf = _cbo()
        self.cbo_rur_inf = _cbo()
        self.cbo_constr_urb = _cbo()
        self.cbo_constr_rur = _cbo()
        self.cbo_constr_urb_inf = _cbo()
        self.cbo_constr_rur_inf = _cbo()
        self.cbo_manz = _cbo()
        self.cbo_ver  = _cbo()
        self.cbo_r1   = _cbo()
        self.cbo_r2   = _cbo()
        rows = [
            ('Terreno Urbano',  self.cbo_urb),
            ('Terreno Rural',   self.cbo_rur),
            ('Terreno Urbano Informal', self.cbo_urb_inf),
            ('Terreno Rural Informal', self.cbo_rur_inf),
            ('Construcción Urbana', self.cbo_constr_urb),
            ('Construcción Rural', self.cbo_constr_rur),
            ('Construcción Urbana Informal', self.cbo_constr_urb_inf),
            ('Construcción Rural Informal', self.cbo_constr_rur_inf),
            ('Manzanas',        self.cbo_manz),
            ('Veredas',         self.cbo_ver),
            ('R1 (alfanumérica)', self.cbo_r1),
            ('R2 (alfanumérica)', self.cbo_r2),
        ]
        for i, (label, cbo) in enumerate(rows):
            grid.addWidget(_lbl(label), i, 0)
            grid.addWidget(cbo, i, 1)
        grid.setColumnStretch(1, 1)
        body.addLayout(grid)

        rr = QHBoxLayout()
        self.btn_reload = _btn('↻ Recargar capas', primary=False, small=True)
        self.btn_detect = _btn('🔍 Detectar campos clave', primary=False, small=True)
        rr.addWidget(self.btn_reload); rr.addWidget(self.btn_detect); rr.addStretch(1)
        body.addLayout(rr)

        # ── Campos clave ──
        body.addWidget(_sec('Campos clave (auto-detectados, editables)'))
        g2 = QGridLayout(); g2.setHorizontalSpacing(8); g2.setVerticalSpacing(4)
        self.cbo_predial   = _cbo()   # campo código predial en terrenos
        self.cbo_ver_cod_t = _cbo()   # campo manzana/vereda en terrenos
        self.cbo_manz_cod_m = _cbo()  # campo codigo en capa manzanas
        self.cbo_ver_cod_v = _cbo()   # campo código vereda en capa veredas
        self.cbo_ver_nom_v = _cbo()   # campo nombre vereda en capa veredas
        self.cbo_r1_key    = _cbo()   # campo predial en R1
        self.cbo_r2_key    = _cbo()   # campo predial en R2
        key_rows = [
            ('Código predial (terrenos)', self.cbo_predial),
            ('Código manzana/vereda (terrenos)', self.cbo_ver_cod_t),
            ('Código manzana (capa manzanas)', self.cbo_manz_cod_m),
            ('Código vereda (capa veredas)', self.cbo_ver_cod_v),
            ('Nombre vereda (capa veredas)', self.cbo_ver_nom_v),
            ('Predial en R1', self.cbo_r1_key),
            ('Predial en R2', self.cbo_r2_key),
        ]
        for i, (label, cbo) in enumerate(key_rows):
            g2.addWidget(_lbl(label), i, 0)
            g2.addWidget(cbo, i, 1)
        g2.setColumnStretch(1, 1)
        body.addLayout(g2)

        pr = QHBoxLayout()
        pr.addWidget(_lbl('Prefijo join R1'))
        self.inp_pre_r1 = _inp('R1_'); self.inp_pre_r1.setText('R1_'); self.inp_pre_r1.setFixedWidth(80)
        pr.addWidget(self.inp_pre_r1)
        pr.addSpacing(10)
        pr.addWidget(_lbl('Prefijo join R2'))
        self.inp_pre_r2 = _inp('R2_'); self.inp_pre_r2.setText('R2_'); self.inp_pre_r2.setFixedWidth(80)
        pr.addWidget(self.inp_pre_r2)
        pr.addStretch(1)
        body.addLayout(pr)

        # ── Salida ──
        body.addWidget(_sec('Salida'))
        outr = QHBoxLayout()
        outr.addWidget(_lbl('Nombre capa'))
        self.inp_out = _inp('Catastro_Consolidado')
        self.inp_out.setText('Catastro_Consolidado')
        outr.addWidget(self.inp_out, 1)
        body.addLayout(outr)

        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        # Progreso + log
        self.progress = QProgressBar()
        self.progress.setStyleSheet(
            f"QProgressBar{{border:1px solid {C['border']};border-radius:3px;"
            f"background:{C['white']};height:16px;font-size:9px;text-align:center;}}"
            f"QProgressBar::chunk{{background:{C['secondary']};border-radius:2px;}}")
        self.progress.setValue(0)
        root.addWidget(self.progress)

        self.log = QPlainTextEdit(); self.log.setReadOnly(True)
        self.log.setFixedHeight(110)
        self.log.setStyleSheet(
            f"QPlainTextEdit{{border:1px solid {C['border']};border-radius:4px;"
            f"background:{C['white']};font-family:Consolas,monospace;font-size:10px;"
            f"color:{C['text']};}}")
        root.addWidget(self.log)

        # Botones finales
        br = QHBoxLayout()
        self.btn_close = _btn('Cerrar', primary=False)
        br.addStretch(1); br.addWidget(self.btn_close)
        root.addLayout(br)

        # Señales
        self.btn_reload.clicked.connect(self._reload_layers)
        self.btn_detect.clicked.connect(self._detect_fields)
        self.btn_pick_gdb.clicked.connect(self._choose_direct_gdb)
        self.btn_pick_r1.clicked.connect(lambda: self._choose_direct_record('r1'))
        self.btn_pick_r2.clicked.connect(lambda: self._choose_direct_record('r2'))
        self.btn_direct.clicked.connect(self._process_direct_selection)
        self.btn_close.clicked.connect(self.close)
        for cbo in (self.cbo_urb, self.cbo_rur, self.cbo_urb_inf,
                    self.cbo_rur_inf, self.cbo_manz, self.cbo_ver,
                    self.cbo_r1, self.cbo_r2):
            cbo.currentIndexChanged.connect(self._detect_fields)

    # ── Carga de capas en los combos ────────────────────────────────────────
    def _vector_layers(self):
        out = []
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr, QgsVectorLayer) and lyr.isValid():
                out.append(lyr)
        out.sort(key=lambda l: l.name().lower())
        return out

    def _reload_layers(self):
        layers = self._vector_layers()
        prev = {cbo: cbo.currentData() for cbo in
                (self.cbo_urb, self.cbo_rur, self.cbo_urb_inf, self.cbo_rur_inf,
                 self.cbo_constr_urb, self.cbo_constr_rur,
                 self.cbo_constr_urb_inf, self.cbo_constr_rur_inf,
                 self.cbo_manz, self.cbo_ver, self.cbo_r1, self.cbo_r2)}
        for cbo in (self.cbo_urb, self.cbo_rur, self.cbo_urb_inf,
                    self.cbo_rur_inf, self.cbo_constr_urb, self.cbo_constr_rur,
                    self.cbo_constr_urb_inf, self.cbo_constr_rur_inf,
                    self.cbo_manz, self.cbo_ver,
                    self.cbo_r1, self.cbo_r2):
            cbo.blockSignals(True)
            cbo.clear()
            cbo.addItem('— ninguna —', self._NONE_DATA)
            for lyr in layers:
                geom = ''
                try:
                    if lyr.isSpatial():
                        geom = ' [' + QgsWkbTypes.geometryDisplayString(lyr.geometryType()) + ']'
                    else:
                        geom = ' [tabla]'
                except Exception:
                    pass
                cbo.addItem(lyr.name() + geom, lyr.id())
            cbo.blockSignals(False)

        # Reponer selección previa o pre-seleccionar por nombre
        def _preselect(cbo, keywords, exclude=None):
            if prev.get(cbo) and prev[cbo] != self._NONE_DATA:
                idx = cbo.findData(prev[cbo])
                if idx >= 0:
                    cbo.setCurrentIndex(idx); return
            exclude = exclude or []
            for i in range(1, cbo.count()):
                name = cbo.itemText(i).lower()
                if any(k in name for k in keywords) and not any(x in name for x in exclude):
                    cbo.setCurrentIndex(i); return

        _preselect(self.cbo_urb, ['urban', 'u_terreno', 'terreno_u'],
                   exclude=['rural', 'informal'])
        _preselect(self.cbo_rur, ['rural', 'r_terreno', 'terreno_r'],
                   exclude=['urban', 'informal'])
        _preselect(self.cbo_urb_inf, ['u_terreno_informal', 'terreno_urbano_informal'],
                   exclude=['rural'])
        _preselect(self.cbo_rur_inf, ['r_terreno_informal', 'terreno_rural_informal'],
                   exclude=['urban'])
        _preselect(self.cbo_constr_urb, ['u_construccion', 'construccion_u', 'urban'],
                   exclude=['rural', 'informal'])
        _preselect(self.cbo_constr_rur, ['r_construccion', 'construccion_r', 'rural'],
                   exclude=['urban', 'informal'])
        _preselect(self.cbo_constr_urb_inf,
                   ['u_construccion_informal', 'construccion_urbano_informal'],
                   exclude=['rural'])
        _preselect(self.cbo_constr_rur_inf,
                   ['r_construccion_informal', 'construccion_rural_informal'],
                   exclude=['urban'])
        _preselect(self.cbo_manz, ['manzan', 'u_manzana'])
        _preselect(self.cbo_ver, ['vered'])
        _preselect(self.cbo_r1,  ['r1'], exclude=['normalizado'])
        _preselect(self.cbo_r2,  ['r2'], exclude=['normalizado'])
        self._detect_fields()
        self._info(f'{len(layers)} capa(s) vectorial(es) disponibles.')

    def _layer(self, cbo):
        data = cbo.currentData()
        if not data or data == self._NONE_DATA:
            return None
        return QgsProject.instance().mapLayer(data)

    def _load_named_ogr_layer(self, path, layer_name, display_name=None):
        """Carga una subcapa OGR concreta y devuelve una QgsVectorLayer válida."""
        uri = '{}|layername={}'.format(path, layer_name)
        layer = QgsVectorLayer(uri, display_name or layer_name, 'ogr')
        return layer if layer.isValid() else None

    def _load_table_file(self, path, role):
        """Carga R1/R2 desde Excel, CSV, DBF, GeoPackage u otra fuente OGR."""
        names = _ogr_sublayer_names(path)
        selected = None
        role_key = _simple_name(role)
        for name in names:
            if role_key in _simple_name(name):
                selected = name
                break
        if selected is None and len(names) == 1:
            selected = names[0]
        if selected is None and names:
            selected = names[0]

        if selected:
            layer = self._load_named_ogr_layer(path, selected, role)
        else:
            layer = QgsVectorLayer(path, role, 'ogr')
            if not layer.isValid():
                layer = None
        return layer, selected

    def _add_source_layer(self, layer, group):
        """Mantiene viva una capa fuente dentro de un grupo oculto del proyecto."""
        QgsProject.instance().addMapLayer(layer, False)
        group.addLayer(layer)

    def _add_layer_at_root(self, layer, index=0):
        """Inserta la capa al tope de la raíz del árbol de capas.

        QgsProject.addMapLayer(layer) por sí solo delega la posición al
        "punto de inserción" activo de QGIS, que normalmente coincide con la
        capa o grupo seleccionado en el panel de Capas: eso puede meter la
        capa consolidada dentro de un grupo, o justo encima/debajo de
        cualquier capa que el usuario tenga activa en ese momento. Aquí se
        agrega sin tocar el árbol (addToLegend=False) y se inserta a mano en
        la raíz, para que siempre quede en una posición fija y predecible.
        """
        QgsProject.instance().addMapLayer(layer, False)
        QgsProject.instance().layerTreeRoot().insertLayer(index, layer)

    def _source_group(self):
        root = QgsProject.instance().layerTreeRoot()
        group = root.findGroup('Fuentes GeoCatastro')
        if group is None:
            group = root.addGroup('Fuentes GeoCatastro')
        try:
            group.setItemVisibilityChecked(False)
        except Exception:
            pass
        return group

    def _select_combo_layer(self, combo, layer):
        index = combo.findData(layer.id()) if layer is not None else -1
        if index >= 0:
            combo.setCurrentIndex(index)

    def _set_direct_path(self, role, path):
        self._direct_paths[role] = path
        line_edit = {
            'gdb': self.inp_direct_gdb,
            'r1': self.inp_direct_r1,
            'r2': self.inp_direct_r2,
        }[role]
        line_edit.setText(os.path.basename(os.path.normpath(path)))
        line_edit.setToolTip(path)
        self._update_direct_state()

    def _update_direct_state(self):
        ready = all(self._direct_paths.values())
        self.btn_direct.setEnabled(ready)
        loaded = []
        for role, label in (('gdb', 'GDB'), ('r1', 'R1'), ('r2', 'R2')):
            if self._direct_paths[role]:
                loaded.append('✓ {}'.format(label))
            else:
                loaded.append('○ {}'.format(label))
        if ready:
            loaded.append('Listo para crear la capa')
        else:
            loaded.append('Puedes seleccionarlos en cualquier orden')
        self.lbl_direct_status.setText('   '.join(loaded))

    def _initial_direct_folder(self, role):
        current = self._direct_paths.get(role, '')
        if current:
            return os.path.dirname(current)
        for candidate in ('r1', 'r2', 'gdb'):
            path = self._direct_paths.get(candidate, '')
            if path:
                return os.path.dirname(path)
        return ''

    def _choose_direct_gdb(self):
        path = QFileDialog.getExistingDirectory(
            self, 'Seleccionar geodatabase de Catastro (.gdb)',
            self._initial_direct_folder('gdb'))
        if not path:
            return
        if not path.lower().endswith('.gdb'):
            self._warn_box('La carpeta seleccionada no es una geodatabase con extensión .gdb.')
            return
        self._set_direct_path('gdb', path)

    def _choose_direct_record(self, role):
        label = role.upper()
        table_filter = (
            'Tablas R1/R2 (*.xlsx *.xls *.csv *.txt *.dbf *.gpkg *.ods);;'
            'Todos los archivos (*.*)')
        path, _ = QFileDialog.getOpenFileName(
            self, 'Seleccionar archivo {}'.format(label),
            self._initial_direct_folder(role), table_filter)
        if path:
            self._set_direct_path(role, path)

    def _process_direct_selection(self):
        missing = [
            label for role, label in (('gdb', 'GDB'), ('r1', 'R1'), ('r2', 'R2'))
            if not self._direct_paths[role]
        ]
        if missing:
            self._warn_box('Falta seleccionar: {}.'.format(', '.join(missing)))
            return None
        if self._direct_processing:
            return None
        self._direct_processing = True
        try:
            return self._run_direct(
                self._direct_paths['gdb'],
                self._direct_paths['r1'],
                self._direct_paths['r2'])
        finally:
            self._direct_processing = False

    def run_direct_wizard(self):
        """Compatibilidad: procesa las tres rutas visibles ya seleccionadas."""
        return self._process_direct_selection()

    def _run_direct(self, gdb_path, r1_path, r2_path):
        """Implementa la carga automática; se separa para poder verificarla."""
        self.log.clear()
        self.progress.setValue(0)
        self._info('▶ Revisando la geodatabase…')

        layer_names = _ogr_sublayer_names(gdb_path)
        if not layer_names:
            self._warn_box('No fue posible leer capas dentro de la geodatabase seleccionada.')
            self._info('✖ La GDB no contiene subcapas OGR legibles.')
            return None

        selected_names = {
            'urban': _pick_layer_name(layer_names, 'urban'),
            'rural': _pick_layer_name(layer_names, 'rural'),
            'urban_informal': _pick_layer_name(layer_names, 'urban_informal'),
            'rural_informal': _pick_layer_name(layer_names, 'rural_informal'),
            'urban_construction': _pick_layer_name(layer_names, 'urban_construction'),
            'rural_construction': _pick_layer_name(layer_names, 'rural_construction'),
            'urban_construction_informal': _pick_layer_name(
                layer_names, 'urban_construction_informal'),
            'rural_construction_informal': _pick_layer_name(
                layer_names, 'rural_construction_informal'),
            'manzana': _pick_layer_name(layer_names, 'manzana'),
            'vereda': _pick_layer_name(layer_names, 'vereda'),
        }
        terrain_roles = ('urban', 'rural', 'urban_informal', 'rural_informal')
        if not any(selected_names[role] for role in terrain_roles):
            available = ', '.join(layer_names[:20])
            self._warn_box(
                'No se encontró ninguna capa de terreno formal o informal en la GDB. '
                'Puedes usar la configuración manual.\n\nCapas detectadas: {}'.format(available))
            self._info('✖ No se detectaron capas de terreno urbano, rural o informal.')
            return None

        loaded = {}
        labels = {
            'urban': 'Terreno Urbano',
            'rural': 'Terreno Rural',
            'urban_informal': 'Terreno Urbano Informal',
            'rural_informal': 'Terreno Rural Informal',
            'urban_construction': 'Construcción Urbana',
            'rural_construction': 'Construcción Rural',
            'urban_construction_informal': 'Construcción Urbana Informal',
            'rural_construction_informal': 'Construcción Rural Informal',
            'manzana': 'Manzanas',
            'vereda': 'Veredas',
        }
        all_roles = (
            'urban', 'rural', 'urban_informal', 'rural_informal',
            'urban_construction', 'rural_construction',
            'urban_construction_informal', 'rural_construction_informal',
            'manzana', 'vereda')
        for role in all_roles:
            name = selected_names[role]
            if name:
                loaded[role] = self._load_named_ogr_layer(
                    gdb_path, name, '{} · {}'.format(labels[role], name))
                if loaded[role] is None:
                    self._info('  · No se pudo cargar {}: {}'.format(labels[role], name))
            else:
                loaded[role] = None

        if not any(loaded.get(role) is not None for role in terrain_roles):
            self._warn_box('Las capas de terreno detectadas no pudieron abrirse.')
            return None

        r1, r1_sublayer = self._load_table_file(r1_path, 'R1')
        r2, r2_sublayer = self._load_table_file(r2_path, 'R2')
        if r1 is None or r2 is None:
            missing = []
            if r1 is None:
                missing.append('R1')
            if r2 is None:
                missing.append('R2')
            self._warn_box('No fue posible abrir: {}.'.format(', '.join(missing)))
            self._info('✖ Revisa el formato de los archivos R1/R2.')
            return None

        source_group = self._source_group()
        for role in all_roles:
            layer = loaded.get(role)
            if layer is not None:
                self._add_source_layer(layer, source_group)
        for layer in (r1, r2):
            if layer is not None:
                self._add_source_layer(layer, source_group)

        self._reload_layers()
        self._select_combo_layer(self.cbo_urb, loaded.get('urban'))
        self._select_combo_layer(self.cbo_rur, loaded.get('rural'))
        self._select_combo_layer(self.cbo_urb_inf, loaded.get('urban_informal'))
        self._select_combo_layer(self.cbo_rur_inf, loaded.get('rural_informal'))
        self._select_combo_layer(self.cbo_constr_urb, loaded.get('urban_construction'))
        self._select_combo_layer(self.cbo_constr_rur, loaded.get('rural_construction'))
        self._select_combo_layer(
            self.cbo_constr_urb_inf, loaded.get('urban_construction_informal'))
        self._select_combo_layer(
            self.cbo_constr_rur_inf, loaded.get('rural_construction_informal'))
        self._select_combo_layer(self.cbo_manz, loaded.get('manzana'))
        self._select_combo_layer(self.cbo_ver, loaded.get('vereda'))
        self._select_combo_layer(self.cbo_r1, r1)
        self._select_combo_layer(self.cbo_r2, r2)
        self._detect_fields()

        self._info('✔ GDB: {}'.format(os.path.basename(gdb_path)))
        for role in all_roles:
            if selected_names[role]:
                self._info('  · {}: {}'.format(labels[role], selected_names[role]))
        self._info('  · R1: {}'.format(r1_sublayer or os.path.basename(r1_path)))
        self._info('  · R2: {}'.format(r2_sublayer or os.path.basename(r2_path)))

        missing_keys = []
        if not self.cbo_predial.currentData():
            missing_keys.append('código predial de Terreno')
        if not self.cbo_r1_key.currentData():
            missing_keys.append('código predial de R1')
        if not self.cbo_r2_key.currentData():
            missing_keys.append('código predial de R2')
        if missing_keys:
            message = (
                'Se cargaron los archivos, pero no se detectó {}. '
                'Selecciona ese campo en la configuración manual y vuelve a pulsar '
                '"Crear capa unificada y consultar".'
            ).format(', '.join(missing_keys))
            self._warn_box(message)
            self._info('⚠ {}'.format(message))
            return None

        if loaded.get('vereda') is None:
            self._info('  · Aviso: no se detectó R_VEREDA; la capa se creará sin su nombre.')
        if loaded.get('manzana') is None:
            self._info('  · Aviso: no se detectó U_MANZANA; se conservará el código del terreno urbano.')

        return self._run()

    # ── Detección de campos clave ───────────────────────────────────────────
    def _fill_fields(self, cbo, layer, selected=None):
        cbo.blockSignals(True)
        cbo.clear()
        cbo.addItem('—', None)
        if layer is not None:
            for f in layer.fields():
                cbo.addItem(f.name(), f.name())
        if selected:
            idx = cbo.findData(selected)
            if idx >= 0:
                cbo.setCurrentIndex(idx)
        cbo.blockSignals(False)

    def _detect_fields(self, *_):
        urb = self._layer(self.cbo_urb)
        rur = self._layer(self.cbo_rur)
        urb_inf = self._layer(self.cbo_urb_inf)
        rur_inf = self._layer(self.cbo_rur_inf)
        manz = self._layer(self.cbo_manz)
        ver = self._layer(self.cbo_ver)
        r1  = self._layer(self.cbo_r1)
        r2  = self._layer(self.cbo_r2)
        terreno = urb or rur or urb_inf or rur_inf

        self._fill_fields(self.cbo_predial,   terreno, _resolve(terreno, _PREDIAL_CANDS))
        self._fill_fields(self.cbo_ver_cod_t, terreno, _resolve(terreno, _TERRITORIAL_COD_CANDS))
        self._fill_fields(self.cbo_manz_cod_m, manz, _resolve(manz, _MANZANA_COD_CANDS + _PREDIAL_CANDS))
        self._fill_fields(self.cbo_ver_cod_v, ver,     _resolve(ver, _VEREDA_COD_CANDS + _PREDIAL_CANDS))
        self._fill_fields(self.cbo_ver_nom_v, ver,     _resolve(ver, _VEREDA_NOM_CANDS))
        self._fill_fields(self.cbo_r1_key,    r1,      _resolve(r1, _RECORD_PREDIAL_CANDS))
        self._fill_fields(self.cbo_r2_key,    r2,      _resolve(r2, _RECORD_PREDIAL_CANDS))

    # ── Log helpers ─────────────────────────────────────────────────────────
    def _info(self, msg):
        self.log.appendPlainText(msg)
        QApplication.processEvents()

    def _warn_box(self, msg):
        QMessageBox.warning(self, 'Consolidar / Merge', msg)

    def _build_normalized_join_table(self, join_layer, join_field, tag):
        """Copia R1/R2 a memoria con una llave textual normalizada para el join."""
        if join_layer is None or not join_field:
            return None, set()

        memory = QgsVectorLayer('None', '_GeoCatastro_{}_normalizado'.format(tag), 'memory')
        provider = memory.dataProvider()
        source_fields = [
            QgsField(field) for field in join_layer.fields()
            if field.name().lower() != _JOIN_KEY.lower()
        ]
        provider.addAttributes(source_fields + [QgsField(_JOIN_KEY, QVariant.String, len=80)])
        memory.updateFields()

        keys = set()
        empty = 0
        duplicates = 0
        buffer = []
        for feature in join_layer.getFeatures():
            key = _norm_predial_code(feature[join_field])
            if not key:
                empty += 1
            elif key in keys:
                duplicates += 1
            else:
                keys.add(key)

            normalized = QgsFeature(memory.fields())
            attributes = []
            for field in source_fields:
                attributes.append(feature[field.name()])
            attributes.append(key)
            normalized.setAttributes(attributes)
            buffer.append(normalized)
            if len(buffer) >= 1000:
                provider.addFeatures(buffer)
                buffer = []
        if buffer:
            provider.addFeatures(buffer)

        self._info(
            '  · {} normalizado: {} registro(s), {} clave(s) prediales.'.format(
                tag, memory.featureCount(), len(keys)))
        if empty:
            self._info('  · Aviso {}: {} registro(s) sin número predial.'.format(tag, empty))
        if duplicates:
            self._info(
                '  · Aviso {}: {} registro(s) repiten número predial; '
                'QGIS mostrará la primera coincidencia.'.format(tag, duplicates))
        return memory, keys

    def _build_graphic_omissions(self, consolidated, r1, r2, r1_key, r2_key):
        """Crea una tabla con predios alfanuméricos que no tienen geometría."""
        spatial_keys = set()
        for feature in consolidated.getFeatures():
            key = _norm_predial_code(feature[_JOIN_KEY])
            if key:
                spatial_keys.add(key)

        omissions = {}

        def _entry(key, numero_predial=''):
            if key not in omissions:
                omissions[key] = {
                    'NUMERO_PREDIAL': _norm_code(numero_predial) or key,
                    'NO_PREDIAL': [],
                    'NOMBRE': [],
                    'TIPO_DOCUMENTO': [],
                    'NUMERO_DOCUMENTO': [],
                    'DIRECCION': [],
                    'PRESENTE_R1': False,
                    'PRESENTE_R2': False,
                }
            return omissions[key]

        def _append(record, field_name, value):
            text = _norm_code(value)
            if text and text not in record[field_name]:
                record[field_name].append(text)

        if r1 is not None and r1_key:
            r1_fields = {
                'NO_PREDIAL': _resolve(r1, ['NoPredial', 'NO_PREDIAL']),
                'NOMBRE': _resolve(r1, ['Nombre', 'NOMBRE']),
                'TIPO_DOCUMENTO': _resolve(
                    r1, ['TipoDocumento', 'Tipo Documento', 'TIPO_DOCUMENTO']),
                'NUMERO_DOCUMENTO': _resolve(
                    r1, ['NoDocumento', 'No Documento', 'NUMERO_DOCUMENTO']),
                'DIRECCION': _resolve(r1, ['Direccion', 'Dirección', 'DIRECCION']),
            }
            for feature in r1.getFeatures():
                key = _norm_predial_code(feature[r1_key])
                if not key or key in spatial_keys:
                    continue
                record = _entry(key, feature[r1_key])
                record['PRESENTE_R1'] = True
                for output_name, source_name in r1_fields.items():
                    if source_name:
                        _append(record, output_name, feature[source_name])

        if r2 is not None and r2_key:
            r2_no_predial = _resolve(r2, ['NoPredial', 'NO_PREDIAL'])
            for feature in r2.getFeatures():
                key = _norm_predial_code(feature[r2_key])
                if not key or key in spatial_keys:
                    continue
                record = _entry(key, feature[r2_key])
                record['PRESENTE_R2'] = True
                if r2_no_predial:
                    _append(record, 'NO_PREDIAL', feature[r2_no_predial])

        fields = [
            QgsField('NUMERO_PREDIAL', QVariant.String, len=80),
            QgsField('NO_PREDIAL', QVariant.String, len=80),
            QgsField('NOMBRE', QVariant.String, len=1000),
            QgsField('TIPO_DOCUMENTO', QVariant.String, len=120),
            QgsField('NUMERO_DOCUMENTO', QVariant.String, len=500),
            QgsField('DIRECCION', QVariant.String, len=1000),
            QgsField('PRESENTE_R1', QVariant.String, len=2),
            QgsField('PRESENTE_R2', QVariant.String, len=2),
            QgsField('ORIGEN_REGISTRO', QVariant.String, len=20),
            QgsField('MOTIVO', QVariant.String, len=120),
        ]
        table = QgsVectorLayer('None', '_GeoCatastro_Omisiones_Graficas', 'memory')
        table.setCustomProperty(_OMISSIONS_TABLE_PROPERTY, True)
        provider = table.dataProvider()
        provider.addAttributes(fields)
        table.updateFields()

        output = []
        for key in sorted(omissions):
            record = omissions[key]
            present_r1 = record['PRESENTE_R1']
            present_r2 = record['PRESENTE_R2']
            if present_r1 and present_r2:
                origin = 'R1 y R2'
            elif present_r1:
                origin = 'R1'
            else:
                origin = 'R2'
            feature = QgsFeature(table.fields())
            feature.setAttributes([
                record['NUMERO_PREDIAL'],
                '; '.join(record['NO_PREDIAL']),
                '; '.join(record['NOMBRE']),
                '; '.join(record['TIPO_DOCUMENTO']),
                '; '.join(record['NUMERO_DOCUMENTO']),
                '; '.join(record['DIRECCION']),
                'Sí' if present_r1 else 'No',
                'Sí' if present_r2 else 'No',
                origin,
                'OMISIÓN GRÁFICA: registro alfanumérico sin geometría',
            ])
            output.append(feature)
        if output:
            provider.addFeatures(output)
        return table

    # Amarillo usado para TODAS las construcciones informales (urbana y
    # rural), en vez del color propio de cada categoria, como senal visual
    # uniforme de "informal" (decision del usuario, 2026-10-12).
    _AMARILLO_INFORMAL = '255,221,0'

    @staticmethod
    def _line_fill_symbol(rgb, outline_width_mm, alpha=255):
        """
        Símbolo de relleno de líneas (hachurado), con el contorno del
        polígono punteado en el mismo color (decisión del usuario,
        2026-10-12, para distinguir a simple vista los elementos
        informales). ``alpha`` (0-255) permite igualar la transparencia que
        ya usan las construcciones formales (160/255) cuando aplica.
        """
        r, g, b = (int(c) for c in rgb.split(','))
        color = QColor(r, g, b, alpha)
        hatch = QgsLinePatternFillSymbolLayer()
        hatch.setColor(color)
        hatch.setLineWidth(0.3)
        hatch.setLineAngle(45)
        hatch.setDistance(1.5)
        symbol = QgsFillSymbol()
        symbol.changeSymbolLayer(0, hatch)
        outline = QgsSimpleLineSymbolLayer(color)
        outline.setWidth(outline_width_mm)
        outline.setPenStyle(Qt.DashLine)
        symbol.appendSymbolLayer(outline)
        return symbol

    def _build_catastro_renderer(self):
        """Renderer categorizado por CLASE (TIPO_UNIDAD + ORIGEN):

        Cada una de las 8 clases usa un color distinto (paleta cualitativa,
        máxima distinción entre categorías), salvo las informales de
        Construcción que usan amarillo uniforme. Construcción formal =
        relleno sólido semitransparente; Predio formal = sin relleno (se ve
        el mapa base); informal (Predio o Construcción) = relleno de líneas
        (hachurado) con contorno punteado, como señal visual adicional a la
        del color. Construcción aparece primero en la lista de categorías,
        luego Predio (decisión del usuario, 2026-10-12).
        """
        # value, etiqueta, color base 'r,g,b'
        # Orden: Construcción antes que Predio; dentro de cada grupo,
        # informal primero y formal debajo, por cada par Urbano/Rural
        # (decision del usuario, 2026-10-12 — misma prioridad que el orden de
        # escritura de features en _run/_build_consolidated).
        palette = [
            ('CONSTRUCCION_URBANO_INFORMAL', 'Construcción Urbana Informal', '140,86,75'),
            ('CONSTRUCCION_URBANO', 'Construcción Urbana', '148,103,189'),
            ('CONSTRUCCION_RURAL_INFORMAL', 'Construcción Rural Informal', '188,189,34'),
            ('CONSTRUCCION_RURAL', 'Construcción Rural', '227,119,194'),
            ('PREDIO_URBANO_INFORMAL', 'Predio Urbano Informal', '255,127,14'),
            ('PREDIO_URBANO', 'Predio Urbano', '31,119,180'),
            ('PREDIO_RURAL_INFORMAL', 'Predio Rural Informal', '214,39,40'),
            # Negro en vez del verde original (decision del usuario,
            # 2026-10-12): el verde se confundia con la ortofoto y con otras
            # capas de ordenamiento territorial al cruzarlas.
            ('PREDIO_RURAL', 'Predio Rural', '0,0,0'),
        ]
        categories = []
        for value, label, rgb in palette:
            es_construccion = value.startswith('CONSTRUCCION')
            es_informal = value.endswith('INFORMAL')
            if es_informal and es_construccion:
                # Construccion informal: hachurado amarillo con la misma
                # transparencia (alpha 160/255) que el resto de construcciones.
                symbol = self._line_fill_symbol(
                    self._AMARILLO_INFORMAL, outline_width_mm=0.3, alpha=160)
            elif es_informal:
                # Predio informal: hachurado con su propio color de categoria.
                symbol = self._line_fill_symbol(rgb, outline_width_mm=0.6)
            else:
                props = {
                    'style': 'solid' if es_construccion else 'no',
                    'color': f'{rgb},160' if es_construccion else f'{rgb},0',
                    'outline_style': 'solid',
                    'outline_color': f'{rgb},255',
                    'outline_width': '0.3' if es_construccion else '0.6',
                    'outline_width_unit': 'MM',
                }
                symbol = QgsFillSymbol.createSimple(props)
            categories.append(QgsRendererCategory(value, symbol, label))
        return QgsCategorizedSymbolRenderer('CLASE', categories)

    # ── Ejecución ───────────────────────────────────────────────────────────
    def _run(self):
        urb = self._layer(self.cbo_urb)
        rur = self._layer(self.cbo_rur)
        urb_inf = self._layer(self.cbo_urb_inf)
        rur_inf = self._layer(self.cbo_rur_inf)
        constr_urb = self._layer(self.cbo_constr_urb)
        constr_rur = self._layer(self.cbo_constr_rur)
        constr_urb_inf = self._layer(self.cbo_constr_urb_inf)
        constr_rur_inf = self._layer(self.cbo_constr_rur_inf)
        manz = self._layer(self.cbo_manz)
        ver = self._layer(self.cbo_ver)
        r1  = self._layer(self.cbo_r1)
        r2  = self._layer(self.cbo_r2)

        # Las capas informales van primero: son predios especificos que
        # requieren manejo prioritario de informacion (decision del usuario,
        # 2026-10-12).
        terreno_layers = []
        if urb_inf is not None:
            terreno_layers.append((urb_inf, 'URBANO_INFORMAL'))
        if rur_inf is not None:
            terreno_layers.append((rur_inf, 'RURAL_INFORMAL'))
        if urb is not None:
            terreno_layers.append((urb, 'URBANO'))
        if rur is not None:
            terreno_layers.append((rur, 'RURAL'))
        if not terreno_layers:
            # Si el usuario ya selecciono GDB, R1 y R2, el boton inferior debe
            # ejecutar el mismo flujo automatico que el boton del panel azul.
            # Esto evita enviar por error los combos manuales vacios a la
            # consolidacion.
            if (not self._direct_processing
                    and all(self._direct_paths.values())):
                return self._process_direct_selection()
            self._warn_box('Selecciona al menos una capa de terreno (urbano o rural).')
            return

        construccion_layers = []
        if constr_urb_inf is not None:
            construccion_layers.append((constr_urb_inf, 'URBANO_INFORMAL'))
        if constr_rur_inf is not None:
            construccion_layers.append((constr_rur_inf, 'RURAL_INFORMAL'))
        if constr_urb is not None:
            construccion_layers.append((constr_urb, 'URBANO'))
        if constr_rur is not None:
            construccion_layers.append((constr_rur, 'RURAL'))

        # Validar geometría poligonal
        for lyr, _ in terreno_layers:
            if not lyr.isSpatial() or lyr.geometryType() != QgsWkbTypes.PolygonGeometry:
                self._warn_box(f'La capa de terreno «{lyr.name()}» no es poligonal.')
                return
        for lyr, _ in construccion_layers:
            if not lyr.isSpatial() or lyr.geometryType() != QgsWkbTypes.PolygonGeometry:
                self._warn_box(f'La capa de construcción «{lyr.name()}» no es poligonal.')
                return

        # Una sola lista combinada: Terrenos primero (define el CRS/tipo de
        # geometría de referencia) y luego Construcciones, cada una marcada
        # con TIPO_UNIDAD para poder categorizar la capa resultante.
        combined_layers = (
            [(lyr, origen, 'PREDIO') for lyr, origen in terreno_layers]
            + [(lyr, origen, 'CONSTRUCCION') for lyr, origen in construccion_layers])

        out_name = (self.inp_out.text() or 'Catastro_Consolidado').strip()
        predial_field = self.cbo_predial.currentData()

        self.log.clear()
        self.progress.setValue(0)
        self._info('▶ Iniciando consolidación…')
        self._info(
            '  · Llaves: Terreno «{}» ↔ R1 «{}» ↔ R2 «{}».'.format(
                predial_field or 'sin detectar',
                self.cbo_r1_key.currentData() or 'sin detectar',
                self.cbo_r2_key.currentData() or 'sin detectar'))

        try:
            consolidated = self._build_consolidated(
                combined_layers, manz, ver, out_name, predial_field)
        except Exception as exc:  # noqa: BLE001
            self._warn_box(f'Error al consolidar: {exc}')
            self._info(f'✖ Error: {exc}')
            return

        if consolidated is None:
            return

        consolidated.setRenderer(self._build_catastro_renderer())

        self._add_layer_at_root(consolidated)
        total_predios = sum(lyr.featureCount() for lyr, _ in terreno_layers)
        total_construcciones = sum(lyr.featureCount() for lyr, _ in construccion_layers)
        self._info(f'✔ Capa «{consolidated.name()}» creada con '
                   f'{total_predios} predio(s) y {total_construcciones} construcción(es).')

        # Adjuntar R1/R2 mediante una llave textual común. Esto evita que el join
        # falle cuando CODIGO viene como texto en la GDB y NUMERO PREDIAL como
        # número, o cuando alguno incluye espacios, puntos o guiones.
        r1_normalized, r1_keys = self._build_normalized_join_table(
            r1, self.cbo_r1_key.currentData(), 'R1')
        r2_normalized, r2_keys = self._build_normalized_join_table(
            r2, self.cbo_r2_key.currentData(), 'R2')
        source_group = self._source_group()
        for normalized in (r1_normalized, r2_normalized):
            if normalized is not None:
                self._add_source_layer(normalized, source_group)

        self._attach_join(consolidated, r1_normalized, _JOIN_KEY, _JOIN_KEY,
                          self.inp_pre_r1.text().strip() or 'R1_', 'R1', r1_keys)
        self._attach_join(consolidated, r2_normalized, _JOIN_KEY, _JOIN_KEY,
                          self.inp_pre_r2.text().strip() or 'R2_', 'R2', r2_keys)

        try:
            omissions = self._build_graphic_omissions(
                consolidated, r1, r2,
                self.cbo_r1_key.currentData(), self.cbo_r2_key.currentData())
            self._add_source_layer(omissions, source_group)
            omission_count = omissions.featureCount()
            consolidated.setCustomProperty(
                _OMISSIONS_LAYER_PROPERTY, omissions.id())
            consolidated.setCustomProperty(
                _OMISSIONS_COUNT_PROPERTY, omission_count)
            self._info(
                '  · Omisiones gráficas detectadas: {:,}.'.format(omission_count))
        except Exception as error:
            self._info(
                '  · Aviso: no fue posible generar el reporte de omisiones: {}'.format(error))

        self.progress.setValue(100)
        self._info('✔ Consolidación finalizada.')
        consolidated = self._offer_save_consolidated(
            consolidated, default_filename=out_name + '.shp')

        try:
            self.iface.setActiveLayer(consolidated)
        except Exception:
            pass
        try:
            parent = self.parent()
            if parent is not None and hasattr(parent, '_select_created_layer'):
                parent._select_created_layer(consolidated)
        except (AttributeError, RuntimeError):
            pass
        return consolidated

    @staticmethod
    def _dated_filename(filename):
        """
        Inserta la fecha del dia en que se ejecuta el proceso antes de la
        extension, conservando el nombre que el usuario ya haya puesto
        (decision del usuario, 2026-10-12): 'Catastro_Consolidado.shp' ->
        'Catastro_Consolidado_2026-10-12.shp'.
        """
        name, ext = os.path.splitext(filename)
        return '{}_{}{}'.format(name, date.today().isoformat(), ext or '.shp')

    def _offer_save_consolidated(self, consolidated, default_filename='Catastro_Consolidado.shp'):
        """Guardar antes de seleccionar el resultado elimina dependencias temporales."""
        project = QgsProject.instance()
        default_filename = self._dated_filename(default_filename)
        QMessageBox.information(
            self, 'Guardar resultado de la consolidación',
            'Elige dónde guardar el shapefile con los datos R1/R2 incorporados. '
            'El proyecto usará ese archivo al volver a abrirlo. Las omisiones '
            'se guardarán en una tabla DBF junto al shapefile.\n\n'
            'Si cancelas, la capa seguirá siendo temporal.')
        while True:
            path, _ = QFileDialog.getSaveFileName(
                self, 'Guardar shapefile del merge',
                os.path.join(project.homePath() or os.path.expanduser('~'),
                             default_filename), 'Shapefile (*.shp)')
            if not path:
                self._info('  · Guardado cancelado: la capa sigue siendo temporal y no se conserva al cerrar QGIS.')
                return consolidated
            omission_id = consolidated.customProperty(_OMISSIONS_LAYER_PROPERTY, '')
            omissions = project.mapLayer(omission_id) if omission_id else None
            try:
                from .merge_persistence import save_consolidated
                saved, saved_omissions, shp_path = save_consolidated(
                    consolidated, path, omissions)
            except Exception as error:
                QMessageBox.warning(self, 'No se pudo completar el guardado',
                                    '{}\n\nLa capa temporal se conserva. Elige otro nombre o cancela.'.format(error))
                continue
            self._add_layer_at_root(saved)
            if saved_omissions is not None:
                self._add_source_layer(saved_omissions, self._source_group())
                saved.setCustomProperty(_OMISSIONS_LAYER_PROPERTY, saved_omissions.id())
                project.removeMapLayer(omissions.id())
            joined_ids = [join.joinLayerId() for join in consolidated.vectorJoins()]
            project.removeMapLayer(consolidated.id())
            for layer_id in joined_ids:
                joined = project.mapLayer(layer_id)
                if joined is not None and joined.name().startswith('_GeoCatastro_'):
                    project.removeMapLayer(layer_id)
            self._info('✔ Shapefile guardado: {}'.format(shp_path))
            for output in (saved, saved_omissions):
                if output is not None:
                    style_path = os.path.splitext(output.source())[0] + '.qml'
                    message, ok = output.saveNamedStyle(style_path)
                    if not ok:
                        self._info('  · No se pudo guardar el estilo auxiliar: {}'.format(message))
            self._info('  · Guarda el proyecto QGIS (.qgz) para conservar esta capa y su configuración.')
            return saved

    def _build_consolidated(self, layers_with_origin, manz, ver, out_name,
                            predial_field=None):
        """layers_with_origin: lista de (capa, ORIGEN, TIPO_UNIDAD).

        TIPO_UNIDAD distingue PREDIO (terreno) de CONSTRUCCION; junto con
        ORIGEN (URBANO/RURAL/*_INFORMAL) forma el campo CLASE que categoriza
        la capa resultante.
        """
        # CRS y tipo de geometría de referencia (primera capa)
        ref_layer = layers_with_origin[0][0]
        crs = ref_layer.crs()
        base_wkb = QgsWkbTypes.multiType(QgsWkbTypes.flatType(ref_layer.wkbType()))
        geom_str = QgsWkbTypes.displayString(base_wkb)

        # Esquema unión de campos (por nombre; primer tipo visto gana)
        seen = set()
        fields_spec = []   # (name, QgsField)
        for lyr, _origen, _tipo in layers_with_origin:
            for f in lyr.fields():
                key = f.name().lower()
                if key in seen:
                    continue
                seen.add(key)
                fields_spec.append(QgsField(f))
        # Campos agregados
        if 'origen' not in seen:
            fields_spec.append(QgsField('ORIGEN', QVariant.String, len=20))
            seen.add('origen')
        if 'tipo_unidad' not in seen:
            fields_spec.append(QgsField('TIPO_UNIDAD', QVariant.String, len=20))
            seen.add('tipo_unidad')
        if 'clase' not in seen:
            fields_spec.append(QgsField('CLASE', QVariant.String, len=40))
            seen.add('clase')
        if 'nombre_vereda' not in seen:
            fields_spec.append(QgsField('NOMBRE_VEREDA', QVariant.String, len=120))
            seen.add('nombre_vereda')
        if 'manzana_vereda_codigo' not in seen:
            fields_spec.append(QgsField(
                'MANZANA_VEREDA_CODIGO', QVariant.String, len=80))
            seen.add('manzana_vereda_codigo')
        if _JOIN_KEY.lower() not in seen:
            fields_spec.append(QgsField(_JOIN_KEY, QVariant.String, len=80))
            seen.add(_JOIN_KEY.lower())

        uri = f'{geom_str}?crs={crs.authid()}'
        mem = QgsVectorLayer(uri, out_name, 'memory')
        mem.setCustomProperty(_QUERY_RESULT_PROPERTY, True)
        dp = mem.dataProvider()
        dp.addAttributes(fields_spec)
        mem.updateFields()

        out_fields = mem.fields()
        idx_origen = out_fields.indexFromName('ORIGEN')
        idx_tipo = out_fields.indexFromName('TIPO_UNIDAD')
        idx_clase = out_fields.indexFromName('CLASE')
        idx_vernom = out_fields.indexFromName('NOMBRE_VEREDA')
        idx_territorial = out_fields.indexFromName('MANZANA_VEREDA_CODIGO')
        idx_join_key = out_fields.indexFromName(_JOIN_KEY)

        # Lookup de veredas: {codigo_normalizado: nombre} y localizador espacial
        # para asignar la vereda a los predios rurales que no traen su código
        # (p. ej. R_TERRENO_INFORMAL).
        vereda_lookup = {}
        ver_locator = None
        if ver is not None:
            vcod = self.cbo_ver_cod_v.currentData()
            vnom = self.cbo_ver_nom_v.currentData()
            if vcod and vnom:
                for f in ver.getFeatures():
                    vereda_lookup[_norm_code(f[vcod])] = f[vnom]
                self._info(f'  · {len(vereda_lookup)} veredas cargadas para lookup.')
            else:
                self._info('  · Aviso: capa de veredas sin campos código/nombre; '
                           'NOMBRE_VEREDA quedará vacío.')
            if vcod:
                try:
                    ver_locator = _TerritorialLocator(ver, vcod, vnom or None)
                    self._info('  · Índice espacial de veredas construido para '
                               'predios rurales sin código.')
                except Exception as error:   # noqa: BLE001
                    self._info('  · Aviso: no se pudo indexar veredas para '
                               f'asignación espacial: {error}')

        # Codigos validos de manzana + localizador espacial para asignar la
        # manzana a los predios urbanos que no traen su código (p. ej.
        # U_TERRENO_INFORMAL). La salida conserva el codigo aun cuando la capa
        # auxiliar no este disponible; el set sirve para diagnostico.
        manzana_codes = set()
        manz_locator = None
        if manz is not None:
            mcod = self.cbo_manz_cod_m.currentData()
            if mcod:
                for feature in manz.getFeatures():
                    code = _norm_code(feature[mcod])
                    if code:
                        manzana_codes.add(code)
                self._info(f'  · {len(manzana_codes)} manzanas cargadas para validación.')
                try:
                    manz_locator = _TerritorialLocator(manz, mcod)
                    self._info('  · Índice espacial de manzanas construido para '
                               'predios urbanos sin código.')
                except Exception as error:   # noqa: BLE001
                    self._info('  · Aviso: no se pudo indexar manzanas para '
                               f'asignación espacial: {error}')
            else:
                self._info('  · Aviso: capa de manzanas sin campo código detectable.')

        # Unión por CÓDIGO: el código de manzana/vereda es el prefijo del código
        # predial de 30 dígitos (los primeros 17). Para los predios que no traen
        # el campo (informales) se toma ese prefijo y se valida contra los
        # códigos reales de las capas de manzana y vereda. Conecta TODAS las
        # capas de terreno con manzana/vereda por el código que comparten.
        vereda_codes = set(vereda_lookup.keys())
        territorial_code_lengths = sorted(
            {len(c) for c in manzana_codes if c}
            | {len(c) for c in vereda_codes if c},
            reverse=True)
        if territorial_code_lengths:
            self._info('  · Unión por código habilitada (longitudes de código '
                       'territorial: {}).'.format(
                           ', '.join(str(n) for n in territorial_code_lengths)))

        total = sum(l.featureCount() for l, _origen, _tipo in layers_with_origin) or 1
        done = 0
        unmatched_ver = 0
        unmatched_manz = 0
        prefix_ver = 0
        prefix_manz = 0
        spatial_ver = 0
        spatial_manz = 0
        buffer = []

        for lyr, origen, tipo_unidad in layers_with_origin:
            # Mapeo target_idx -> source field name
            src_names = {f.name().lower(): f.name() for f in lyr.fields()}
            name_map = []  # (target_idx, source_name)
            for ti in range(out_fields.count()):
                tname = out_fields.at(ti).name()
                if ti in (idx_origen, idx_tipo, idx_clase, idx_vernom, idx_territorial):
                    continue
                sn = src_names.get(tname.lower())
                if sn is not None:
                    name_map.append((ti, sn))

            # Campos clave EN esta capa. Si urbano y rural usan nombres distintos,
            # se resuelve cada uno de forma independiente.
            source_predial_field = predial_field
            if source_predial_field not in src_names.values():
                source_predial_field = _resolve(lyr, _PREDIAL_CANDS)
            is_urban = origen.startswith('URBANO')
            territorial_candidates = (
                _MANZANA_COD_CANDS if is_urban else _VEREDA_COD_CANDS)
            territorial_field = _resolve(lyr, territorial_candidates)
            if territorial_field is None:
                territorial_field = _resolve(lyr, _TERRITORIAL_COD_CANDS)

            # Transformación de CRS si difiere
            transform = None
            if lyr.crs() != crs:
                transform = QgsCoordinateTransform(
                    lyr.crs(), crs, QgsProject.instance())

            # Transformaciones hacia el CRS de los índices espaciales (para
            # localizar manzana/vereda de los predios sin código).
            manz_tr = None
            if manz_locator is not None and lyr.crs() != manz_locator.crs:
                manz_tr = QgsCoordinateTransform(
                    lyr.crs(), manz_locator.crs, QgsProject.instance())
            ver_tr = None
            if ver_locator is not None and lyr.crs() != ver_locator.crs:
                ver_tr = QgsCoordinateTransform(
                    lyr.crs(), ver_locator.crs, QgsProject.instance())

            for feat in lyr.getFeatures():
                nf = QgsFeature(out_fields)
                # geometría
                g = feat.geometry()
                if g is not None and not g.isNull():
                    if transform is not None:
                        g = QgsGeometry(g)
                        g.transform(transform)
                    if QgsWkbTypes.isMultiType(base_wkb) and not g.isMultipart():
                        g.convertToMultiType()
                    nf.setGeometry(g)
                # atributos por nombre
                for ti, sn in name_map:
                    nf.setAttribute(ti, feat[sn])
                # ORIGEN / TIPO_UNIDAD / CLASE
                if idx_origen >= 0:
                    nf.setAttribute(idx_origen, origen)
                if idx_tipo >= 0:
                    nf.setAttribute(idx_tipo, tipo_unidad)
                if idx_clase >= 0:
                    nf.setAttribute(idx_clase, f'{tipo_unidad}_{origen}')
                territorial_code = ''
                normalized_territorial = ''
                if territorial_field:
                    territorial_code = _norm_code(feat[territorial_field])
                # Unión por CÓDIGO para los predios sin campo (informales):
                # el prefijo del código predial (primeros 17) es el código de
                # manzana/vereda. Se valida contra los códigos reales de la capa.
                known_codes = manzana_codes if is_urban else vereda_codes
                if (not territorial_code and source_predial_field
                        and known_codes and territorial_code_lengths):
                    predial = _norm_code(feat[source_predial_field])
                    for code_len in territorial_code_lengths:
                        if len(predial) > code_len and predial[:code_len] in known_codes:
                            territorial_code = predial[:code_len]
                            if is_urban:
                                prefix_manz += 1
                            else:
                                prefix_ver += 1
                            break
                # Último recurso: ubicación espacial (predio dentro del polígono
                # de manzana/vereda), por si el código predial no resuelve.
                if not territorial_code:
                    locator = manz_locator if is_urban else ver_locator
                    if locator is not None:
                        loc_tr = manz_tr if is_urban else ver_tr
                        territorial_code, _sp_nombre = locator.locate(
                            feat.geometry(), loc_tr)
                        if territorial_code:
                            if is_urban:
                                spatial_manz += 1
                            else:
                                spatial_ver += 1
                normalized_territorial = territorial_code
                if idx_territorial >= 0:
                    nf.setAttribute(idx_territorial, territorial_code)
                # NOMBRE_VEREDA
                if idx_vernom >= 0:
                    nombre = ''
                    if not is_urban and normalized_territorial and vereda_lookup:
                        nombre = vereda_lookup.get(normalized_territorial, '')
                        if not nombre:
                            unmatched_ver += 1
                    nf.setAttribute(idx_vernom, nombre)
                if (is_urban and normalized_territorial and manzana_codes
                        and normalized_territorial not in manzana_codes):
                    unmatched_manz += 1
                if idx_join_key >= 0 and source_predial_field:
                    nf.setAttribute(
                        idx_join_key,
                        _norm_predial_code(feat[source_predial_field]))
                buffer.append(nf)

                done += 1
                if len(buffer) >= 500:
                    dp.addFeatures(buffer)
                    buffer = []
                    self.progress.setValue(int(done * 100 / total))
                    QApplication.processEvents()

        if buffer:
            dp.addFeatures(buffer)
        mem.updateExtents()
        self.progress.setValue(95)

        if prefix_manz:
            self._info(f'  · {prefix_manz} registro(s) urbano(s) sin campo '
                       f'recibieron su MANZANA por código (prefijo del predial).')
        if prefix_ver:
            self._info(f'  · {prefix_ver} registro(s) rural(es) sin campo '
                       f'recibieron su VEREDA por código (prefijo del predial).')
        if spatial_manz:
            self._info(f'  · {spatial_manz} registro(s) urbano(s) sin código '
                       f'recibieron su MANZANA por ubicación espacial.')
        if spatial_ver:
            self._info(f'  · {spatial_ver} registro(s) rural(es) sin código '
                       f'recibieron su VEREDA por ubicación espacial.')
        if unmatched_ver:
            self._info(f'  · Aviso: {unmatched_ver} registro(s) con código de vereda '
                       f'sin coincidencia en la capa de veredas.')
        if unmatched_manz:
            self._info(f'  · Aviso: {unmatched_manz} registro(s) con código de manzana '
                       f'sin coincidencia en la capa de manzanas.')
        return mem

    def _attach_join(self, target, join_layer, target_field, join_field, prefix, tag,
                     join_keys=None):
        if join_layer is None:
            return
        if not target_field:
            self._info(f'  · {tag}: sin campo predial en terrenos; join omitido.')
            return
        if not join_field:
            self._info(f'  · {tag}: sin campo predial en la tabla; join omitido.')
            return
        ji = QgsVectorLayerJoinInfo()
        # setJoinLayer registra internamente el id; NO llamar setJoinLayerId
        # después, porque deja el puntero de capa en None y el join no genera
        # columnas al hacer updateFields().
        ji.setJoinLayer(join_layer)
        ji.setJoinFieldName(join_field)
        ji.setTargetFieldName(target_field)
        ji.setUsingMemoryCache(True)
        ji.setPrefix(prefix)
        ok = target.addJoin(ji)
        target.updateFields()
        if ok:
            self._info(f'  · {tag} unido como join virtual (prefijo «{prefix}», '
                       f'{target_field} = {join_field}).')
            if join_keys is not None:
                matched = 0
                total_with_key = 0
                for feature in target.getFeatures():
                    key = _norm_predial_code(feature[target_field])
                    if key:
                        total_with_key += 1
                        if key in join_keys:
                            matched += 1
                self._info(
                    '  · {}: {} de {} predio(s) encontraron coincidencia.'.format(
                        tag, matched, total_with_key))
        else:
            self._info(f'  · {tag}: QGIS rechazó el join.')
