"""
consultas_dialog.py  –  V3.2
Herramienta Catastral IGAC – Morelia 18479

ARQUITECTURA:
  Las capas en QGIS tienen joins con R1 y R2.
  Los campos del join se nombran: <prefijo_join>_<Campo>
  Ej: "18479-Morelia_R1_SIG_Nombre", "18479-Morelia_R2_SIG_Matricula Inmobiliaria"

  El plugin detecta automáticamente ese prefijo inspeccionando los campos de la
  capa activa. Todos los filtros se construyen como expresiones QGIS estándar
  (ILIKE) sobre los campos reales de la capa — sin cachés externos, sin xlsx.

CAMPOS CONOCIDOS POR GRUPO:
  GDB base:
    CODIGO, CODIGO_ANTERIOR, VEREDA_CODIGO (rural) / MANZANA_CODIGO (urbano),
    NUMERO_SUBTERRANEOS, SHAPE_Area, SHAPE_Length,
    TIPO_CONSTRUCCION, NUMERO_PISOS (R_CONSTRUCCION / U_CONSTRUCCION)

  R1 (join):
    Nombre, Tipo Documento, No Documento, Direccion,
    Destino Economico, Area Terreno(m2), Area Construida (m2),
    Avaluo Catastral, Vigencia

  R2 (join):
    Matricula Inmobiliaria, Zona Fisica, Zona Economica,
    Area Terreno m2, Habitaciones, Baños, Locales, Pisos,
    Estrato, Uso, Puntaje, Area Construida m2, Vigencia

  Nomenclatura (join o capa separada):
    TEXTO (campo de dirección desde R_NOMENCLATURA_DOMICILIARIA)

  Vereda (join o capa separada):
    NOMBRE (campo de vereda desde R_VEREDA)
"""

import re
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox,
    QAbstractItemView, QScrollArea, QFrame, QSizePolicy,
    QMessageBox, QStackedWidget, QShortcut,
    QListWidget, QListWidgetItem, QDialog, QDialogButtonBox,
    QSplitter,
)
from qgis.PyQt.QtCore import Qt, QVariant, QSettings, QSize, QPoint, QDate
from qgis.PyQt.QtGui import QKeySequence, QColor, QBrush
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFeatureRequest,
    QgsExpression, QgsWkbTypes, QgsField,
)

from .igac_dominios import DESTINO_ECONOMICO, TIPO_DOCUMENTO, ESTRATO, detect_layer_type

# ── Paleta ────────────────────────────────────────────────────────────────────
C = {
    'primary':  '#1a4b8c', 'secondary': '#2e86de',
    'bg':       '#f0f3f7', 'white':     '#ffffff',
    'border':   '#cdd4dc', 'text':      '#2c3e50',
    'header':   '#dde3ea', 'alt':       '#f8f9fa',
    'hover':    '#d5e8f9', 'success':   '#27ae60',
    'error':    '#c0392b', 'info_bg':   '#e3f2fd',
    'warn_bg':  '#fff8e1', 'tag_blue':  '#e3f2fd',
    'filled':   '#fffde7',
}
INT_T   = {QVariant.Int, QVariant.LongLong, QVariant.UInt, QVariant.ULongLong}
FLOAT_T = {QVariant.Double}
STR_T   = {QVariant.String}
NUM_T   = INT_T | FLOAT_T

# ─────────────────────────────────────────────────────────────────────────────
#  DETECCIÓN AUTOMÁTICA DE CAMPOS EN LA CAPA ACTIVA
# ─────────────────────────────────────────────────────────────────────────────

# Candidatos para cada campo semántico — el primero que se encuentre en la capa gana
# Incluye nombre exacto GDB, variantes con prefijo join y abreviaciones shapefile
_FIELD_CANDIDATES = {
    # ── GDB base ──────────────────────────────────────────────────────────────
    'CODIGO':              ['CODIGO', 'codigo', 'COD_PRED', 'NoPredial'],
    'CODIGO_ANTERIOR':     ['CODIGO_ANTERIOR', 'codigo_anterior', 'COD_ANT', 'CODANT'],
    'VEREDA_CODIGO':       ['VEREDA_CODIGO', 'vereda_codigo', 'VER_COD', 'MANZANA_CODIGO', 'manzana_codigo', 'MAN_COD'],
    'NUMERO_SUBTERRANEOS': ['NUMERO_SUBTERRANEOS', 'numero_subterraneos', 'NUM_SUBT', 'NSUBTERR'],
    'SHAPE_Area':          ['SHAPE_Area', 'shape_area', 'SHAPE_AREA', 'Shape_Area'],
    'SHAPE_Length':        ['SHAPE_Length', 'shape_length', 'SHAPE_LENGTH', 'Shape_Length'],
    'TIPO_CONSTRUCCION':   ['TIPO_CONSTRUCCION', 'tipo_construccion', 'TIPO_CONS'],
    'NUMERO_PISOS':        ['NUMERO_PISOS', 'numero_pisos', 'NUM_PISOS'],
    # ── R1 ────────────────────────────────────────────────────────────────────
    'Nombre':              ['Nombre', 'NOMBRE', 'nombre'],
    'Tipo Documento':      ['Tipo Documento', 'TIPO_DOC', 'TipoDocumento', 'tipo_doc'],
    'No Documento':        ['No Documento', 'NO_DOC', 'NoDocumento', 'no_doc', 'NUM_DOC'],
    'Direccion':           ['Direccion', 'DIRECCION', 'direccion', 'DIR', 'TEXTO', 'texto'],
    'Destino Economico':   ['Destino Economico', 'DESTINO_EC', 'DestinoEc', 'destino_ec', 'DEST_ECON'],
    'Area Terreno(m2)':    ['Area Terreno(m2)', 'AREA_TERR', 'AreaTerren', 'area_terr', 'AREAT'],
    'Area Construida (m2)':['Area Construida (m2)', 'AREA_CONS', 'AreaConstr', 'area_cons', 'AREAC'],
    'Avaluo Catastral':    [
        'R_Avaluo ($)', 'r_avaluo ($)', 'R_Avaluo', 'r_avaluo',
        'Avaluo ($)', 'avaluo ($)', 'Avaluo_Catastral', 'AvaluoCatastral',
        'Avaluo Catastral', 'AVALUO_CAT', 'AvaluoCat', 'avaluo_cat',
        'AVALUO_CATASTRAL', 'AVALUO', 'Avaluo', 'avaluo',
    ],
    'Vigencia':            ['Vigencia', 'VIGENCIA', 'vigencia', 'VIG'],
    # ── R2 ────────────────────────────────────────────────────────────────────
    'Matricula Inmobiliaria': ['Matricula Inmobiliaria', 'MATRICULA', 'matricula', 'MAT_INM', 'MatriInmob'],
    'Zona Fisica':          ['Zona Fisica', 'ZONA_FIS', 'ZonaFisica', 'zona_fis', 'ZF'],
    'Zona Economica':       ['Zona Economica', 'ZONA_ECO', 'ZonaEconom', 'zona_eco', 'ZE'],
    'Habitaciones':         ['Habitaciones', 'HABITAC', 'habitaciones', 'HAB'],
    'Baños':                ['Baños', 'BANOS', 'banos', 'NUM_BAN'],
    'Locales':              ['Locales', 'LOCALES', 'locales', 'LOC'],
    'Pisos':                ['Pisos', 'PISOS', 'pisos', 'NUM_PIS'],
    'Estrato':              ['Estrato', 'ESTRATO', 'estrato', 'EST'],
    'Uso':                  ['Uso', 'USO', 'uso', 'USO_CONS'],
    'Puntaje':              ['Puntaje', 'PUNTAJE', 'puntaje', 'PUNT'],
    'Area Construida m2':   ['Area Construida m2', 'AREAC_M2', 'AreaConsM2', 'area_c_m2'],
    # ── Nomenclatura / Vereda ─────────────────────────────────────────────────
    'TEXTO':               ['TEXTO', 'texto', 'DIRECCION', 'DIR_NOM'],
    'NOMBRE_VEREDA':       ['NOMBRE', 'nombre_vereda', 'NOM_VERED', 'NOM_BARRI'],
}


def _detect_join_prefix(layer, known_bare: str) -> str:
    """
    Dado un nombre de campo sin prefijo (ej. 'Nombre'),
    busca en la capa un campo que termine en '_Nombre' o 'Nombre'
    y devuelve el prefijo del join (puede ser '').
    """
    bare_low = known_bare.lower().replace(' ', '').replace('(', '').replace(')', '').replace('/', '')
    for fld in layer.fields():
        fn = fld.name()
        fn_low = fn.lower().replace(' ', '').replace('(', '').replace(')', '').replace('/', '')
        # coincidencia exacta sin prefijo
        if fn_low == bare_low:
            return ''
        # con prefijo: el campo termina en _BareNombre
        if fn_low.endswith('_' + bare_low):
            prefix = fn[:len(fn) - len(bare_low) - 1]
            return prefix
    return None   # no encontrado


def resolve_field(layer, semantic: str) -> str | None:
    """
    Devuelve el nombre REAL del campo en la capa para el identificador semántico dado.
    Primero prueba candidatos exactos, luego busca por sufijo (join con prefijo variable).
    Maneja campos con espacios en el nombre (ej. 'Avaluo Catastral' → '18479-R1_Avaluo Catastral').
    """
    candidates = _FIELD_CANDIDATES.get(semantic, [semantic])
    fields_real = {f.name(): f.name() for f in layer.fields()}
    fields_low  = {f.name().lower(): f.name() for f in layer.fields()}

    # 1. Coincidencia exacta (con o sin mayúsculas)
    for c in candidates:
        if c in fields_real:
            return c
        if c.lower() in fields_low:
            return fields_low[c.lower()]

    # 2. Sufijo / coincidencia parcial con prefijo join
    for c in candidates:
        c_low  = c.lower()
        c_bare = c_low.replace(' ', '').replace('(', '').replace(')', '').replace('$', '').replace('_', '')

        for fn_real in fields_real:
            fl      = fn_real.lower()
            fl_bare = fl.replace(' ', '').replace('(', '').replace(')', '').replace('$', '').replace('_', '')

            # a) Terminación exacta (con o sin separador)
            if fl.endswith(c_low) and len(fl) > len(c_low):
                return fn_real

            # b) Terminación en versión bare (sin espacios/paréntesis/$)
            if fl_bare.endswith(c_bare) and len(c_bare) >= 4 and len(fl_bare) > len(c_bare):
                return fn_real

            # c) Coincidencia exacta bare
            if fl_bare == c_bare and len(c_bare) >= 4:
                return fn_real

    return None


def build_like(layer, semantic: str, value: str, exact=False) -> str | None:
    """
    Construye una cláusula ILIKE para el campo semántico dado.
    Devuelve None si el campo no existe en la capa.
    """
    real = resolve_field(layer, semantic)
    if not real:
        return None
    fld  = layer.fields().field(real)
    safe = value.strip().replace("'", "''")
    fn   = f'"{real}"'
    if exact:
        if fld.type() in NUM_T:
            try:
                return f'{fn} = {int(safe)}'
            except ValueError:
                try:
                    return f'{fn} = {float(safe)}'
                except ValueError:
                    pass
        return f'{fn} = \'{safe}\''
    # parcial
    if fld.type() in NUM_T:
        return f'to_string({fn}) ILIKE \'%{safe}%\''
    return f'{fn} ILIKE \'%{safe}%\''


def get_value(feat, layer, semantic: str):
    """Lee el valor de un campo semántico en un feature."""
    real = resolve_field(layer, semantic)
    if not real:
        return None
    try:
        return feat[real]
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS UI
# ─────────────────────────────────────────────────────────────────────────────

def _btn(text, primary=True, color=None, small=False):
    b = QPushButton(text)
    pad = '2px 7px' if small else '4px 10px'
    fs  = '10px'    if small else '11px'
    if color:
        b.setStyleSheet(f"QPushButton{{background:{color};color:white;border:none;border-radius:4px;padding:{pad};font-weight:bold;font-size:{fs};}}QPushButton:hover{{background:{color}cc;}}QPushButton:disabled{{background:#aaa;}}")
    elif primary:
        b.setStyleSheet(f"QPushButton{{background:{C['primary']};color:white;border:none;border-radius:4px;padding:{pad};font-weight:bold;font-size:{fs};}}QPushButton:hover{{background:{C['secondary']};}}QPushButton:disabled{{background:#aaa;}}")
    else:
        b.setStyleSheet(f"QPushButton{{background:{C['white']};color:{C['primary']};border:2px solid {C['primary']};border-radius:4px;padding:{pad};font-weight:bold;font-size:{fs};}}QPushButton:hover{{background:{C['hover']};}}")
    return b

def _inp(ph=''):
    w = QLineEdit(); w.setPlaceholderText(ph)
    w.setStyleSheet(f"QLineEdit{{border:1px solid {C['border']};border-radius:3px;padding:2px 5px;background:{C['white']};font-size:11px;color:{C['text']};min-height:18px;}}QLineEdit:focus{{border:2px solid {C['secondary']};}}")
    return w

def _cbo(d=None):
    w = QComboBox()
    w.setStyleSheet(f"QComboBox{{border:1px solid {C['border']};border-radius:3px;padding:2px 5px;background:{C['white']};font-size:11px;color:{C['text']};min-height:18px;}}QComboBox:focus{{border:2px solid {C['secondary']};}}QComboBox::drop-down{{border:none;width:18px;}}QComboBox QAbstractItemView{{font-size:11px;}}")
    if d:
        for k, v in d.items(): w.addItem(v, k)
    return w

def _sec(text):
    w = QLabel(f'▸ {text}')
    w.setStyleSheet(f'font-size:10px;font-weight:bold;color:{C["primary"]};border-bottom:1px solid {C["border"]};margin-top:3px;padding:1px 0;')
    return w

def _lbl(text):
    l = QLabel(text); l.setStyleSheet(f'font-size:9px;font-weight:bold;color:{C["text"]};')
    return l

def _fmt_area(val):
    """Formatea área: separador miles=punto, decimal=coma, máx 4 decimales."""
    if val is None or str(val).strip() == '': return ''
    try:
        f = float(str(val).replace(',', '.'))
        s = f'{f:,.4f}'                                   # 1,234.5678
        s = s.replace(',','X').replace('.', ',').replace('X', '.')   # 1.234,5678
        p = s.split(',')
        if len(p) == 2:
            dec = p[1].rstrip('0').ljust(2, '0')
            s = p[0] + ',' + dec
        return s
    except Exception:
        return str(val)

def _fmt_tipo_doc(code):
    return TIPO_DOCUMENTO.get(str(code or '').strip(), str(code or ''))


# ─────────────────────────────────────────────────────────────────────────────
#  FORMULARIO UNIFICADO
# ─────────────────────────────────────────────────────────────────────────────

class FormTerreno(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f'background:{C["white"]};')
        g = QGridLayout(self)
        g.setContentsMargins(6, 4, 6, 4)
        g.setHorizontalSpacing(6)
        g.setVerticalSpacing(3)
        row = 0
        self.f = {}

        def add(label, widget, r, col=0):
            g.addWidget(_lbl(label), r, col * 2)
            g.addWidget(widget,      r, col * 2 + 1)

        # ── Identificación (campos GDB) ────────────────────────────────────
        g.addWidget(_sec('Identificación predial'), row, 0, 1, 4); row += 1

        self.f['CODIGO']          = _inp('Código predial 30 dígitos')
        self.f['CODIGO_ANTERIOR'] = _inp('Código anterior del predio')
        add('No. Predial:',    self.f['CODIGO'],          row, 0)
        add('Cód. anterior:',  self.f['CODIGO_ANTERIOR'], row, 1); row += 1

        self.f['VEREDA_CODIGO'] = _inp('Código vereda/manzana (17 dígitos)')
        add('Cód. Vereda/Manz.:', self.f['VEREDA_CODIGO'], row, 0)

        # Vereda/Barrio: campo de solo lectura
        self.lbl_vereda = QLabel('')
        self.lbl_vereda.setStyleSheet(
            f'font-size:10px;color:{C["primary"]};font-style:italic;'
            f'background:{C["info_bg"]};border-radius:3px;padding:1px 5px;')
        g.addWidget(_lbl('Vereda / Barrio:'), row, 2)
        g.addWidget(self.lbl_vereda, row, 3); row += 1

        # ── Propietario (campos R1) ────────────────────────────────────────
        g.addWidget(_sec('Propietario (R1)'), row, 0, 1, 4); row += 1

        self.f['Nombre']       = _inp('Nombre del propietario')
        self.f['TipoDoc_cbo']  = _cbo(TIPO_DOCUMENTO)
        add('Nombre:',    self.f['Nombre'],      row, 0)
        add('Tipo Doc.:', self.f['TipoDoc_cbo'], row, 1); row += 1

        self.f['No Documento'] = _inp('Número de documento')
        self.f['Direccion']    = _inp('Dirección / nombre del predio')
        add('No. Documento:', self.f['No Documento'], row, 0)
        add('Dirección:',     self.f['Direccion'],    row, 1); row += 1

        self.f['DestinoEc_cbo']     = _cbo(DESTINO_ECONOMICO)
        self.f['Avaluo Catastral']  = _inp('Valor en pesos')
        add('Destino económico:', self.f['DestinoEc_cbo'],    row, 0)
        add('Avalúo Catastral:',  self.f['Avaluo Catastral'], row, 1); row += 1

        self.f['Vigencia'] = _inp('Ej. 01012026')
        add('Vigencia:', self.f['Vigencia'], row, 0); row += 1

        # ── Áreas R1 ───────────────────────────────────────────────────────
        g.addWidget(_sec('Áreas (R1)'), row, 0, 1, 4); row += 1

        self.f['Area Terreno(m2)']     = _inp('m²')
        self.f['Area Construida (m2)'] = _inp('m²')
        add('Área Terreno (m²):',    self.f['Area Terreno(m2)'],     row, 0)
        add('Área Construida (m²):', self.f['Area Construida (m2)'], row, 1); row += 1

        # ── Áreas geométricas GDB ─────────────────────────────────────────
        self.f['SHAPE_Area']   = _inp('m²')
        self.f['SHAPE_Length'] = _inp('m')
        add('Área Geográfica (m²):', self.f['SHAPE_Area'],   row, 0)
        add('Perímetro (m):',        self.f['SHAPE_Length'], row, 1); row += 1

        # ── Registro 2 ────────────────────────────────────────────────────
        g.addWidget(_sec('Registro 2 (R2)'), row, 0, 1, 4); row += 1

        self.f['Matricula Inmobiliaria'] = _inp('Ej: 420-54596')
        self.f['Zona Fisica']            = _inp('Código zona física')
        add('Matr. Inmobiliaria:', self.f['Matricula Inmobiliaria'], row, 0)
        add('Zona Física:',        self.f['Zona Fisica'],            row, 1); row += 1

        self.f['Zona Economica'] = _inp('Código zona económica')
        self.f['Estrato_cbo']    = _cbo(ESTRATO)
        add('Zona Económica:', self.f['Zona Economica'], row, 0)
        add('Estrato:',        self.f['Estrato_cbo'],   row, 1); row += 1

        self.f['Uso']    = _inp('Código uso construcción')
        self.f['Pisos']  = _inp('Cantidad de pisos')
        add('Uso:',   self.f['Uso'],   row, 0)
        add('Pisos:', self.f['Pisos'], row, 1); row += 1

        self.f['Baños']   = _inp('Cantidad de baños')
        self.f['Locales'] = _inp('Cantidad de locales')
        add('Baños:',   self.f['Baños'],   row, 0)
        add('Locales:', self.f['Locales'], row, 1); row += 1

        self.f['Puntaje'] = _inp('Puntaje construcción')
        add('Puntaje:', self.f['Puntaje'], row, 0); row += 1

        g.setColumnStretch(1, 1)
        g.setColumnStretch(3, 1)

    # ── Helpers internos ──────────────────────────────────────────────────────
    def _txt(self, k):
        w = self.f.get(k)
        return w.text().strip() if isinstance(w, QLineEdit) else ''

    def _cbo_val(self, k):
        w = self.f.get(k)
        return (w.currentData() or '') if isinstance(w, QComboBox) else ''

    # ── Construcción de expresión de filtro ───────────────────────────────────
    def build_expression(self, layer) -> tuple[str, list[str]]:
        """
        Construye la expresión QGIS de filtro basándose en los campos
        REALMENTE presentes en la capa activa (detecta join automáticamente).
        Devuelve (expr_str, campos_no_encontrados).
        """
        clauses  = []
        not_found = []

        # Mapa: clave_semantica → valor_ingresado
        filtros = {}

        # GDB directos
        if self._txt('CODIGO'):
            filtros['CODIGO'] = self._txt('CODIGO')
        if self._txt('CODIGO_ANTERIOR'):
            filtros['CODIGO_ANTERIOR'] = self._txt('CODIGO_ANTERIOR')
        if self._txt('VEREDA_CODIGO'):
            filtros['VEREDA_CODIGO'] = self._txt('VEREDA_CODIGO')

        # R1
        if self._txt('Nombre'):
            filtros['Nombre'] = self._txt('Nombre')
        if self._txt('No Documento'):
            filtros['No Documento'] = self._txt('No Documento')
        if self._cbo_val('TipoDoc_cbo'):
            filtros['Tipo Documento'] = self._cbo_val('TipoDoc_cbo')
        if self._cbo_val('DestinoEc_cbo'):
            filtros['Destino Economico'] = self._cbo_val('DestinoEc_cbo')
        if self._txt('Avaluo Catastral'):
            filtros['Avaluo Catastral'] = self._txt('Avaluo Catastral')
        if self._txt('Vigencia'):
            filtros['Vigencia'] = self._txt('Vigencia')
        if self._txt('Area Terreno(m2)'):
            filtros['Area Terreno(m2)'] = self._txt('Area Terreno(m2)')
        if self._txt('Area Construida (m2)'):
            filtros['Area Construida (m2)'] = self._txt('Area Construida (m2)')
        if self._txt('Direccion'):
            filtros['Direccion'] = self._txt('Direccion')

        # R2
        if self._txt('Matricula Inmobiliaria'):
            filtros['Matricula Inmobiliaria'] = self._txt('Matricula Inmobiliaria')
        if self._txt('Zona Fisica'):
            filtros['Zona Fisica'] = self._txt('Zona Fisica')
        if self._txt('Zona Economica'):
            filtros['Zona Economica'] = self._txt('Zona Economica')
        if self._cbo_val('Estrato_cbo'):
            filtros['Estrato'] = self._cbo_val('Estrato_cbo')
        if self._txt('Uso'):
            filtros['Uso'] = self._txt('Uso')
        if self._txt('Pisos'):
            filtros['Pisos'] = self._txt('Pisos')
        if self._txt('Baños'):
            filtros['Baños'] = self._txt('Baños')
        if self._txt('Locales'):
            filtros['Locales'] = self._txt('Locales')
        if self._txt('Puntaje'):
            filtros['Puntaje'] = self._txt('Puntaje')

        # Construir cláusulas
        for sem, val in filtros.items():
            clause = build_like(layer, sem, str(val))
            if clause:
                clauses.append(clause)
            else:
                not_found.append(sem)

        expr = ' AND '.join(f'({c})' for c in clauses)
        return expr, not_found

    # ── Relleno desde feature ─────────────────────────────────────────────────
    def fill_from_feature(self, feat, layer):
        ds_filled = (
            f"QLineEdit{{border:1px solid {C['secondary']};border-radius:3px;"
            f"padding:2px 5px;background:{C['filled']};font-size:11px;"
            f"color:{C['text']};min-height:18px;}}"
        )
        ds_empty = (
            f"QLineEdit{{border:1px solid {C['border']};border-radius:3px;"
            f"padding:2px 5px;background:{C['white']};font-size:11px;"
            f"color:{C['text']};min-height:18px;}}"
        )

        def _s(key, semantic):
            w = self.f.get(key)
            if not isinstance(w, QLineEdit): return
            v = get_value(feat, layer, semantic)
            txt = str(v) if v is not None else ''
            w.blockSignals(True)
            w.setText(txt)
            w.setStyleSheet(ds_filled if txt else ds_empty)
            w.blockSignals(False)

        def _sc(key, semantic):
            w = self.f.get(key)
            if not isinstance(w, QComboBox): return
            v = get_value(feat, layer, semantic)
            vs = str(v or '').strip()
            idx = w.findData(vs)
            if idx < 0: idx = w.findText(vs, Qt.MatchContains)
            if idx >= 0:
                w.blockSignals(True)
                w.setCurrentIndex(idx)
                w.blockSignals(False)

        # GDB
        _s('CODIGO',          'CODIGO')
        _s('CODIGO_ANTERIOR', 'CODIGO_ANTERIOR')
        _s('VEREDA_CODIGO',   'VEREDA_CODIGO')

        # Áreas geométricas
        ag = get_value(feat, layer, 'SHAPE_Area')
        al = get_value(feat, layer, 'SHAPE_Length')
        w_ag = self.f.get('SHAPE_Area')
        w_al = self.f.get('SHAPE_Length')
        if isinstance(w_ag, QLineEdit):
            txt = _fmt_area(ag)
            w_ag.setText(txt); w_ag.setStyleSheet(ds_filled if txt else ds_empty)
        if isinstance(w_al, QLineEdit):
            txt = _fmt_area(al)
            w_al.setText(txt); w_al.setStyleSheet(ds_filled if txt else ds_empty)

        # R1
        _s('Nombre',              'Nombre')
        _s('No Documento',        'No Documento')
        _sc('TipoDoc_cbo',        'Tipo Documento')
        _sc('DestinoEc_cbo',      'Destino Economico')
        _s('Vigencia',            'Vigencia')
        # Dirección: campo TEXTO de nomenclatura_domiciliaria (join) o Direccion de R1
        dir_v = get_value(feat, layer, 'Direccion') or get_value(feat, layer, 'TEXTO')
        w_dir = self.f.get('Direccion')
        if isinstance(w_dir, QLineEdit):
            txt = str(dir_v or '')
            w_dir.setText(txt); w_dir.setStyleSheet(ds_filled if txt else ds_empty)

        # Buscar avalúo: primero por resolve_field, luego buscar manualmente cualquier
        # campo que contenga 'avaluo' o 'R_Avaluo' en la capa
        avaluo = get_value(feat, layer, 'Avaluo Catastral')
        if avaluo is None:
            for fld in layer.fields():
                fl = fld.name().lower().replace(' ', '').replace('(', '').replace(')', '').replace('$', '')
                if 'avaluo' in fl or fl.startswith('r_avaluo'):
                    try:
                        v = feat[fld.name()]
                        if v is not None and str(v).strip() not in ('', 'None', 'NULL'):
                            avaluo = v
                            break
                    except Exception:
                        pass
        w_av = self.f.get('Avaluo Catastral')
        if isinstance(w_av, QLineEdit):
            if avaluo is not None and str(avaluo).strip() not in ('', 'None', 'NULL'):
                try:
                    # El valor viene como entero (ej. 164566000)
                    num = int(float(str(avaluo).strip()))
                    txt = '$ ' + f'{num:,}'.replace(',', '.')
                except Exception:
                    txt = str(avaluo)
            else:
                txt = ''
            w_av.setText(txt); w_av.setStyleSheet(ds_filled if txt else ds_empty)

        at = get_value(feat, layer, 'Area Terreno(m2)')
        ac = get_value(feat, layer, 'Area Construida (m2)')
        w_at = self.f.get('Area Terreno(m2)')
        w_ac = self.f.get('Area Construida (m2)')
        if isinstance(w_at, QLineEdit):
            txt = _fmt_area(at); w_at.setText(txt); w_at.setStyleSheet(ds_filled if txt else ds_empty)
        if isinstance(w_ac, QLineEdit):
            txt = _fmt_area(ac); w_ac.setText(txt); w_ac.setStyleSheet(ds_filled if txt else ds_empty)

        # Vereda / Barrio
        ver_cod = str(get_value(feat, layer, 'VEREDA_CODIGO') or '').strip()
        ver_nom = _buscar_nombre_vereda(ver_cod)
        self.lbl_vereda.setText(ver_nom or (f'(cód: {ver_cod})' if ver_cod else ''))

        # R2
        _s('Matricula Inmobiliaria', 'Matricula Inmobiliaria')
        _s('Zona Fisica',            'Zona Fisica')
        _s('Zona Economica',         'Zona Economica')
        _sc('Estrato_cbo',           'Estrato')
        _s('Uso',                    'Uso')
        _s('Pisos',                  'Pisos')
        _s('Baños',                  'Baños')
        _s('Locales',                'Locales')
        _s('Puntaje',                'Puntaje')

    def clear(self):
        ss = (f"QLineEdit{{border:1px solid {C['border']};border-radius:3px;"
              f"padding:2px 5px;background:{C['white']};font-size:11px;"
              f"color:{C['text']};min-height:18px;}}")
        for w in self.f.values():
            if isinstance(w, QLineEdit):
                w.clear(); w.setStyleSheet(ss)
            elif isinstance(w, QComboBox):
                w.setCurrentIndex(0)
        self.lbl_vereda.setText('')


# ─────────────────────────────────────────────────────────────────────────────
#  CACHÉ VEREDA (solo lectura, se carga una vez del proyecto)
# ─────────────────────────────────────────────────────────────────────────────

_VEREDA_CACHE = {}
_VEREDA_LOADED = [False]


def _cargar_vereda():
    if _VEREDA_LOADED[0]:
        return
    _VEREDA_CACHE.clear()
    for lyr in QgsProject.instance().mapLayers().values():
        if not isinstance(lyr, QgsVectorLayer): continue
        nm = lyr.name().lower()
        if 'r_vereda' not in nm and 'vereda' not in nm: continue
        cod_f = nom_f = None
        for f in lyr.fields():
            fl = f.name().lower()
            if fl == 'codigo': cod_f = f.name()
            if fl == 'nombre': nom_f = f.name()
        if cod_f and nom_f:
            for feat in lyr.getFeatures():
                c = str(feat[cod_f] or '').strip()
                n = str(feat[nom_f] or '').strip()
                if c and n:
                    _VEREDA_CACHE[c] = n
    _VEREDA_LOADED[0] = True


def _buscar_nombre_vereda(codigo):
    _cargar_vereda()
    return _VEREDA_CACHE.get(codigo, '')


def _reset_vereda_cache():
    _VEREDA_LOADED[0] = False
    _VEREDA_CACHE.clear()


# ─────────────────────────────────────────────────────────────────────────────
#  DIÁLOGO PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

class ConsultasPredialesDialog(QWidget):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface            = iface
        self.current_features = []
        self._all_field_names = []
        self._nav_index       = 0
        self._active_form     = None
        self._build_ui()
        self._connect_signals()
        self._refresh_layers()
        self._restore_geometry()

    def _restore_geometry(self):
        s = QSettings('HerramientaCatastral', 'v32')
        self.resize(s.value('size', QSize(700, 820)))
        pos = s.value('pos', None)
        if pos and isinstance(pos, QPoint):
            self.move(pos)

    def closeEvent(self, event):
        s = QSettings('HerramientaCatastral', 'v32')
        s.setValue('size', self.size()); s.setValue('pos', self.pos())
        try:
            QgsProject.instance().layersAdded.disconnect(self._refresh_layers)
            QgsProject.instance().layersRemoved.disconnect(self._refresh_layers)
        except Exception:
            pass
        super().closeEvent(event)

    # ── Build UI ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.setStyleSheet(f'background:{C["bg"]};color:{C["text"]};')
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10); root.setSpacing(8)
        self._build_header(root)
        scroll, tl = self._build_scroll_area()
        self._build_layer_panel(tl)
        self._build_fields_badge(tl)
        self._build_quick_search(tl)
        self._build_form_panel(tl)
        self._build_action_btns(tl)
        self._build_nav(tl)
        self._build_status(tl)
        scroll.setWidget(scroll._inner)
        self._build_table(root, scroll)

    def _build_header(self, root):
        h = QFrame()
        h.setStyleSheet(f"QFrame{{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {C['primary']},stop:1 {C['secondary']});border-radius:8px;}}")
        h.setFixedHeight(46)
        lo = QHBoxLayout(h); lo.setContentsMargins(14,0,14,0); lo.setSpacing(10)
        ico = QLabel('🗺'); ico.setStyleSheet('font-size:22px;background:transparent;'); ico.setFixedWidth(30)
        lo.addWidget(ico)
        tc = QVBoxLayout(); tc.setSpacing(0)
        tc.addWidget(QLabel('Consultas Catastrales', styleSheet='color:white;font-size:13px;font-weight:bold;background:transparent;'))
        tc.addWidget(QLabel('IGAC Colombia – LADM-COL  |  v3.2', styleSheet='color:rgba(255,255,255,0.82);font-size:9px;background:transparent;'))
        lo.addLayout(tc, 1)
        root.addWidget(h)

    def _build_scroll_area(self):
        s = QScrollArea(); s.setWidgetResizable(True); s.setFrameShape(QFrame.NoFrame)
        s.setStyleSheet(f'background:{C["bg"]};border:none;')
        inner = QWidget(); inner.setStyleSheet(f'background:{C["bg"]};')
        lo = QVBoxLayout(inner); lo.setContentsMargins(0,0,0,4); lo.setSpacing(8)
        s._inner = inner
        return s, lo

    def _build_layer_panel(self, tl):
        box = QGroupBox('Capa activa')
        box.setStyleSheet(f"QGroupBox{{font-weight:bold;font-size:11px;color:{C['primary']};border:1px solid {C['border']};border-radius:6px;margin-top:8px;padding-top:6px;background:{C['white']};}}QGroupBox::title{{subcontrol-origin:margin;left:10px;padding:0 4px;}}")
        lo = QVBoxLayout(box); lo.setContentsMargins(8,10,8,8); lo.setSpacing(4)
        r = QHBoxLayout()
        self.cbo_layer = _cbo()
        self.cbo_layer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_refresh = QPushButton('↺')
        self.btn_refresh.setFixedSize(30,30)
        self.btn_refresh.setStyleSheet(f"QPushButton{{background:{C['white']};color:{C['primary']};border:1px solid {C['border']};border-radius:4px;font-size:14px;}}QPushButton:hover{{background:{C['hover']};}}")
        self.btn_diag = QPushButton('🔍 Campos')
        self.btn_diag.setFixedHeight(30)
        self.btn_diag.setStyleSheet(f"QPushButton{{background:{C['info_bg']};color:{C['primary']};border:1px solid {C['secondary']};border-radius:4px;padding:2px 8px;font-size:11px;font-weight:bold;}}QPushButton:hover{{background:{C['hover']};}}")
        r.addWidget(self.cbo_layer, 1); r.addWidget(self.btn_refresh); r.addWidget(self.btn_diag)
        lo.addLayout(r)
        self.lbl_layer_meta = QLabel('—')
        self.lbl_layer_meta.setStyleSheet('font-size:10px;color:#555;')
        self.lbl_layer_meta.setWordWrap(True)
        lo.addWidget(self.lbl_layer_meta)
        tl.addWidget(box)

    def _build_fields_badge(self, tl):
        """Muestra qué campos del join se detectaron en la capa activa."""
        self.lbl_fields_badge = QLabel('Selecciona una capa para detectar campos de join.')
        self.lbl_fields_badge.setWordWrap(True)
        self.lbl_fields_badge.setStyleSheet(
            f'font-size:10px;color:{C["primary"]};background:{C["info_bg"]};'
            f'border:1px solid {C["secondary"]};border-radius:4px;padding:4px 8px;')
        tl.addWidget(self.lbl_fields_badge)

    def _build_quick_search(self, tl):
        box = QFrame()
        box.setStyleSheet(f"QFrame{{background:{C['info_bg']};border:1px solid {C['secondary']};border-radius:5px;}}")
        lo = QHBoxLayout(box); lo.setContentsMargins(6,4,6,4); lo.setSpacing(5)
        self.inp_quick = QLineEdit()
        self.inp_quick.setPlaceholderText('Búsqueda rápida por código predial, nombre, documento o matrícula…')
        self.inp_quick.setStyleSheet(f"QLineEdit{{background:white;border:1px solid {C['border']};border-radius:4px;padding:4px 8px;font-size:12px;}}QLineEdit:focus{{border-color:{C['secondary']};}}")
        self.inp_quick.returnPressed.connect(self._quick_search)
        self.cbo_history = QComboBox()
        self.cbo_history.setFixedWidth(28); self.cbo_history.setFixedHeight(30)
        self.cbo_history.setStyleSheet(f"QComboBox{{background:{C['white']};border:1px solid {C['border']};border-radius:4px;font-size:11px;padding:0 4px;}}QComboBox::drop-down{{border:none;width:20px;}}")
        self.cbo_history.addItem('🕑')
        self.cbo_history.currentTextChanged.connect(lambda t: self.inp_quick.setText(t) if t and t != '🕑' else None)
        self._search_history = []
        btn = QPushButton('🔍 Buscar'); btn.setFixedHeight(30)
        btn.setStyleSheet(f"QPushButton{{background:{C['secondary']};color:white;border:none;border-radius:4px;padding:0 12px;font-weight:bold;font-size:11px;}}QPushButton:hover{{background:{C['primary']};}}")
        btn.clicked.connect(self._quick_search)
        lo.addWidget(self.inp_quick, 1); lo.addWidget(self.cbo_history); lo.addWidget(btn)
        tl.addWidget(box)

    def _build_form_panel(self, tl):
        fh = QFrame()
        fh.setStyleSheet(f"QFrame{{background:{C['header']};border:1px solid {C['border']};border-radius:4px;}}")
        fl = QHBoxLayout(fh); fl.setContentsMargins(8,4,8,4)
        fl.addWidget(QLabel('🔎  Filtros avanzados', styleSheet=f'font-weight:bold;font-size:11px;color:{C["primary"]};background:transparent;'))
        self.lbl_form_mode = QLabel('')
        self.lbl_form_mode.setStyleSheet(f'font-size:10px;color:{C["success"]};background:transparent;font-style:italic;')
        fl.addWidget(self.lbl_form_mode, 1)
        self.btn_collapse = QPushButton('▼')
        self.btn_collapse.setFixedSize(24,22); self.btn_collapse.setCheckable(True); self.btn_collapse.setChecked(True)
        self.btn_collapse.setStyleSheet(f"QPushButton{{background:transparent;color:{C['primary']};border:none;font-size:11px;font-weight:bold;}}QPushButton:hover{{color:{C['secondary']};}}")
        self.btn_collapse.toggled.connect(lambda e: (self.stack.setVisible(e), self.btn_collapse.setText('▼' if e else '▶')))
        fl.addWidget(self.btn_collapse)
        tl.addWidget(fh)
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f'background:{C["white"]};border:1px solid {C["border"]};border-radius:4px;')
        self.form_terreno = FormTerreno()
        self.stack.addWidget(self.form_terreno)
        self._active_form = self.form_terreno
        tl.addWidget(self.stack)

    def _build_action_btns(self, tl):
        r = QHBoxLayout(); r.setSpacing(6)
        self.btn_search = _btn('🔎  Buscar')
        self.btn_clear  = _btn('✖  Limpiar',    primary=False)
        self.btn_select = _btn('✔  Seleccionar', primary=False)
        self.btn_zoom   = _btn('⌖  Zoom',        primary=False)
        self.btn_export = _btn('📊  Excel',       color=C['success'])
        for b in [self.btn_search, self.btn_clear, self.btn_select, self.btn_zoom, self.btn_export]:
            r.addWidget(b)
        tl.addLayout(r)

    def _build_nav(self, tl):
        nf = QFrame()
        nf.setStyleSheet(f"QFrame{{background:{C['header']};border:1px solid {C['border']};border-radius:4px;}}")
        nl = QHBoxLayout(nf); nl.setContentsMargins(6,3,6,3); nl.setSpacing(6)
        ss = f"QPushButton{{background:{C['white']};color:{C['primary']};border:1px solid {C['border']};border-radius:3px;font-weight:bold;font-size:10px;padding:0 10px;}}QPushButton:hover{{background:{C['hover']};}}QPushButton:disabled{{color:#bbb;background:{C['header']};border-color:#ddd;}}"
        self.btn_nav_prev = QPushButton('◀  Anterior'); self.btn_nav_prev.setFixedHeight(26); self.btn_nav_prev.setStyleSheet(ss)
        self.btn_nav_next = QPushButton('Siguiente  ▶'); self.btn_nav_next.setFixedHeight(26); self.btn_nav_next.setStyleSheet(ss)
        self.lbl_count = QLabel('Sin resultados')
        self.lbl_count.setStyleSheet(f'font-weight:bold;font-size:11px;color:{C["primary"]};background:transparent;')
        self.lbl_count.setAlignment(Qt.AlignCenter)
        nl.addWidget(self.btn_nav_prev); nl.addWidget(self.lbl_count,1); nl.addWidget(self.btn_nav_next)
        tl.addWidget(nf)

    def _build_status(self, tl):
        # Barra inferior compacta: solo estado + botón Excel directo
        bar = QFrame()
        bar.setStyleSheet(
            f'QFrame{{background:{C["header"]};border:1px solid {C["border"]};border-radius:4px;}}')
        bar_lo = QHBoxLayout(bar)
        bar_lo.setContentsMargins(8, 3, 6, 3)
        bar_lo.setSpacing(8)

        self.lbl_status = QLabel('Listo.')
        self.lbl_status.setStyleSheet(
            f'font-size:10px;color:{C["text"]};background:transparent;')
        self.lbl_status.setWordWrap(False)

        self.btn_export_bar = QPushButton('📊  Exportar Excel')
        self.btn_export_bar.setFixedHeight(24)
        self.btn_export_bar.setStyleSheet(
            f'QPushButton{{background:{C["success"]};color:white;border:none;'
            f'border-radius:3px;padding:0 12px;font-size:10px;font-weight:bold;}}'
            f'QPushButton:hover{{background:#1e8449;}}'
            f'QPushButton:disabled{{background:#aaa;}}')

        bar_lo.addWidget(self.lbl_status, 1)
        bar_lo.addWidget(self.btn_export_bar)
        tl.addWidget(bar)

        # Labels ocultos para compatibilidad interna (no se agregan al layout)
        self.lbl_expr = QLabel()
        self.lbl_warn = QLabel()

    def _build_table(self, root, scroll):
        # La tabla principal ya no se muestra en el panel inferior.
        # Solo se agrega el scroll con el formulario al root.
        # El reporte de resultados se muestra en la ventana flotante.
        self.table = QTableWidget()   # widget interno para compatibilidad de señales
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        self.table.setVisible(False)  # nunca se muestra en el panel
        root.addWidget(scroll, 1)

    # ── Señales ───────────────────────────────────────────────────────────────
    def _connect_signals(self):
        self.btn_refresh.clicked.connect(self._refresh_layers)
        self.btn_search.clicked.connect(self._run_search)
        self.btn_clear.clicked.connect(self._clear_all)
        self.btn_select.clicked.connect(self._select_on_map)
        self.btn_zoom.clicked.connect(self._zoom_to_selection)
        self.btn_export.clicked.connect(self._export_excel)
        self.btn_export_bar.clicked.connect(self._export_excel)
        self.cbo_layer.currentIndexChanged.connect(self._on_layer_changed)
        self.btn_nav_prev.clicked.connect(self._nav_prev)
        self.btn_nav_next.clicked.connect(self._nav_next)
        self.btn_diag.clicked.connect(self._show_diagnostics)
        QgsProject.instance().layersAdded.connect(self._refresh_layers)
        QgsProject.instance().layersRemoved.connect(self._refresh_layers)
        QShortcut(QKeySequence('F5'),     self, self._run_search)
        QShortcut(QKeySequence('Escape'), self, self._clear_all)
        QShortcut(QKeySequence('Ctrl+E'), self, self._export_excel)
        QShortcut(QKeySequence('Ctrl+Z'), self, self._zoom_to_selection)

    # ── Capas ─────────────────────────────────────────────────────────────────
    def _refresh_layers(self, *_):
        self.cbo_layer.blockSignals(True)
        prev = self.cbo_layer.currentData()
        self.cbo_layer.clear()
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr, QgsVectorLayer):
                self.cbo_layer.addItem(lyr.name(), lyr.id())
        idx = self.cbo_layer.findData(prev)
        if idx >= 0: self.cbo_layer.setCurrentIndex(idx)
        self.cbo_layer.blockSignals(False)
        self._on_layer_changed()

    def _active_layer(self):
        lid = self.cbo_layer.currentData()
        return QgsProject.instance().mapLayer(lid) if lid else None

    def _on_layer_changed(self):
        _reset_vereda_cache()
        layer = self._active_layer()
        if not layer:
            self.lbl_layer_meta.setText('—')
            self.lbl_fields_badge.setText('Sin capa seleccionada.')
            return
        nf = layer.featureCount()
        nc = len(layer.fields())
        gt = QgsWkbTypes.displayString(layer.wkbType())
        cr = layer.crs().authid()
        self.lbl_layer_meta.setText(f'{nf:,} registros · {nc} campos · {gt} · {cr}')
        self._update_fields_badge(layer)

    def _update_fields_badge(self, layer):
        """Detecta qué campos del join están disponibles y muestra un resumen."""
        semantics = [
            'CODIGO','Nombre','Tipo Documento','No Documento','Direccion',
            'Matricula Inmobiliaria','Estrato','Uso','Pisos','Baños',
            'Locales','Puntaje','Zona Fisica','Zona Economica',
            'Avaluo Catastral','Destino Economico','Area Terreno(m2)',
            'Area Construida (m2)', 'VEREDA_CODIGO',
        ]
        ok, missing = [], []
        for s in semantics:
            real = resolve_field(layer, s)
            if real:
                ok.append(s)
            else:
                missing.append(s)

        color_ok   = C['success']
        color_miss = C['error']
        texto = (
            f'<b>Campos detectados ({len(ok)}):</b> '
            f'<span style="color:{color_ok}">{", ".join(ok[:8])}{"…" if len(ok)>8 else ""}</span>'
        )
        if missing:
            texto += (
                f'<br><b>No encontrados ({len(missing)}) — campos no unidos aún:</b> '
                f'<span style="color:{color_miss}">{", ".join(missing[:6])}{"…" if len(missing)>6 else ""}</span>'
            )
        self.lbl_fields_badge.setText(texto)

    # ── Diagnóstico ───────────────────────────────────────────────────────────
    def _show_diagnostics(self):
        layer = self._active_layer()
        if not layer:
            QMessageBox.information(self, 'Sin capa', 'Selecciona una capa primero.')
            return
        dlg = QDialog(self); dlg.setWindowTitle(f'Campos: {layer.name()}'); dlg.resize(560, 500)
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel(
            f'<b>{len(layer.fields())}</b> campos disponibles. '
            f'Los campos con join aparecen con prefijo del nombre del archivo.',
            wordWrap=True, styleSheet='font-size:11px;padding:4px;'))
        lst = QListWidget(); lst.setStyleSheet('font-family:monospace;font-size:11px;')
        tl = {QVariant.Int:'Int',QVariant.LongLong:'Int64',QVariant.Double:'Float',
              QVariant.String:'Texto',QVariant.Date:'Fecha',QVariant.DateTime:'FechaHora'}
        for fld in layer.fields():
            item = QListWidgetItem(f'{fld.name():<45}  [{tl.get(fld.type(),str(fld.type()))}]')
            # Resaltar campos R1/R2 detectados
            fname_l = fld.name().lower()
            if any(x.lower() in fname_l for x in ['nombre','matricula','estrato','uso','pisos','banos','baños','destino','direccion','avaluo','documento']):
                item.setForeground(QBrush(QColor(C['success'])))
            lst.addItem(item)
        v.addWidget(lst)
        v.addWidget(QLabel(
            '💡 Verde = campo de join detectado (R1/R2). '
            'Si un campo falta, verifica que el join esté activo en las propiedades de la capa.',
            wordWrap=True, styleSheet=f'font-size:10px;color:{C["primary"]};background:{C["info_bg"]};padding:5px;border-radius:3px;'))
        bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(dlg.accept); v.addWidget(bb)
        dlg.exec_()

    # ── BÚSQUEDA PRINCIPAL ────────────────────────────────────────────────────
    def _run_search(self):
        layer = self._active_layer()
        if not layer:
            QMessageBox.warning(self, 'Sin capa', 'Selecciona una capa vectorial primero.')
            return
        try:
            layer.removeSelection()
        except Exception:
            pass

        expr_str, not_found = self._active_form.build_expression(layer)

        if expr_str:
            expr = QgsExpression(expr_str)
            if expr.hasParserError():
                QMessageBox.critical(self, 'Error en expresión',
                    f'{expr.parserErrorString()}\n\nExpresión:\n{expr_str}')
                return

        try:
            req = QgsFeatureRequest()
            if expr_str:
                req.setFilterExpression(expr_str)
            features = list(layer.getFeatures(req))
        except Exception as e:
            QMessageBox.critical(self, 'Error al consultar', str(e))
            return

        self.current_features = features
        self._all_field_names = [f.name() for f in layer.fields()]
        self._nav_index       = 0
        self._populate_table(layer, features)

        if expr_str:
            short = expr_str[:300] + '…' if len(expr_str) > 300 else expr_str
            self.lbl_status.setText(f'🔎 {n} resultado(s) | {short[:120]}')
        else:
            self.lbl_status.setText(f'Sin filtros — {n} registro(s) mostrado(s)')

        if not_found:
            self.lbl_warn.setText(
                f'⚠ Campos no encontrados en la capa (¿falta join?): '
                f'{", ".join(not_found)}\n'
                f'Verifica las Propiedades de capa → Joins.')
            self.lbl_warn.setVisible(True)
        else:
            self.lbl_warn.setVisible(False)

        n = len(features)
        self._set_status(
            f'✅  {n} registro(s) en "{layer.name()}"' if n
            else f'⚠  Sin resultados en "{layer.name()}"'
        )
        if features:
            self._zoom_to_features(features)

    # ── Columnas excluidas / renombradas ─────────────────────────────────────
    _EXCLUDED = {'usuario_log', 'fecha_log', 'globalid', 'globalid_snc',
                 'usuario_log_', 'fecha_log_'}
    _RENAME   = {'shape_area': 'Área (m²)', 'shape_length': 'Perímetro (m)'}

    def _visible_fields(self, layer):
        """Devuelve [(field_real, header_label)] filtrando columnas excluidas."""
        result = []
        for fld in layer.fields():
            fn = fld.name()
            fl = fn.lower()
            # excluir si coincide exacto o termina en sufijo de log/globalid
            if fl in self._EXCLUDED:
                continue
            if any(fl.endswith(s) for s in ('_log', 'globalid', 'globalid_snc')):
                continue
            label = self._RENAME.get(fl, fn)
            result.append((fn, label))
        return result

    def _fmt_cell(self, fn, val):
        """Formatea valor para celda de tabla."""
        if val is None:
            return ''
        fl = fn.lower()
        if fl in ('shape_area', 'shape_length') or fl.endswith('shape_area') or fl.endswith('shape_length'):
            return _fmt_area(val)
        if 'avaluo' in fl or fl.startswith('r_avaluo') or '($)' in fl:
            try:
                num = int(float(str(val).replace(',', '').replace('.', '').strip()))
                return '$ ' + f'{num:,}'.replace(',', '.')
            except Exception:
                pass
        return str(val)

    # ── Tabla embebida ────────────────────────────────────────────────────────
    def _populate_table(self, layer, features):
        n = len(features)
        self._nav_index = max(0, min(self._nav_index, n-1)) if n else 0
        vis = self._visible_fields(layer)
        self._vis_fields = vis

        ALN = Qt.AlignLeft | Qt.AlignVCenter
        self.table.setSortingEnabled(False)
        self.table.setRowCount(n)
        self.table.setColumnCount(len(vis))
        self.table.setHorizontalHeaderLabels([lbl for _, lbl in vis])

        for r, feat in enumerate(features):
            for c, (fn, _) in enumerate(vis):
                try:    v = feat[fn]
                except: v = None
                item = QTableWidgetItem(self._fmt_cell(fn, v))
                item.setTextAlignment(ALN)
                item.setData(Qt.UserRole, feat.id())
                self.table.setItem(r, c, item)

        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()
        if n > 0:
            self.table.blockSignals(True)
            self.table.selectRow(self._nav_index)
            self.table.blockSignals(False)
            self._fill_form(features[self._nav_index], layer)

        color = C['success'] if n > 0 else C['error']
        self.lbl_count.setText(
            '⚠ Sin resultados' if n == 0 else
            '✅ 1 predio' if n == 1 else
            f'✅ Predio {self._nav_index+1} de {n}'
        )
        self.lbl_count.setStyleSheet(
            f'font-weight:bold;font-size:11px;color:{color};background:transparent;')
        self.btn_nav_prev.setEnabled(n > 1 and self._nav_index > 0)
        self.btn_nav_next.setEnabled(n > 1 and self._nav_index < n-1)

        # Actualizar tabla flotante si está abierta
        self._open_float_table(layer, features, vis)

    # ── Tabla flotante dinámica ───────────────────────────────────────────────
    def _open_float_table(self, layer, features, vis):
        """
        Abre (o actualiza) la ventana de reporte flotante dinámica.
        Incluye: búsqueda en tiempo real, ordenamiento, ocultar/mostrar columnas,
        exportar Excel y copiar selección.
        """
        from qgis.PyQt.QtWidgets import (
            QDockWidget, QLineEdit as QLE, QPushButton as QPB,
            QCheckBox, QScrollArea, QVBoxLayout, QHBoxLayout,
            QFrame, QLabel, QMenu, QAction,
        )
        from qgis.PyQt.QtCore import Qt as Qt2

        n = len(features)
        lname = layer.name() if layer else '—'

        # Crear o reutilizar la ventana flotante
        if not hasattr(self, '_float_win') or self._float_win is None or not self._float_win.isVisible():
            win = QDialog(None)   # Sin padre para que sea ventana independiente
            win.setWindowTitle(f'Reporte Predial — {lname}')
            win.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint |
                               Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
            win.resize(1100, 520)
            win.setAttribute(Qt.WA_DeleteOnClose, False)
            self._float_win = win
        else:
            win = self._float_win
            win.setWindowTitle(f'Reporte Predial — {lname}')

        # Limpiar layout anterior
        old_layout = win.layout()
        if old_layout:
            while old_layout.count():
                item = old_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            import sip
            try:
                sip.delete(old_layout)
            except Exception:
                pass

        root = QVBoxLayout(win)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # ── Barra de herramientas ─────────────────────────────────────────
        toolbar = QFrame()
        toolbar.setStyleSheet(
            f'background:{C["header"]};border:1px solid {C["border"]};border-radius:4px;')
        tb_lo = QHBoxLayout(toolbar)
        tb_lo.setContentsMargins(8, 4, 8, 4)
        tb_lo.setSpacing(8)

        lbl_title = QLabel(f'<b>{n}</b> registro(s) — {lname}')
        lbl_title.setStyleSheet(f'font-size:11px;color:{C["primary"]};background:transparent;')

        inp_search = QLE()
        inp_search.setPlaceholderText('🔍 Filtrar en tabla…')
        inp_search.setFixedHeight(28)
        inp_search.setStyleSheet(
            f'border:1px solid {C["border"]};border-radius:3px;padding:2px 8px;'
            f'font-size:11px;background:white;')
        inp_search.setMaximumWidth(280)

        btn_cols  = QPB('⚙ Columnas')
        btn_exp   = QPB('📊 Excel')
        btn_copy  = QPB('📋 Copiar')
        btn_close = QPB('✕')
        for b in [btn_cols, btn_exp, btn_copy]:
            b.setFixedHeight(28)
            b.setStyleSheet(
                f'QPushButton{{background:{C["primary"]};color:white;border:none;'
                f'border-radius:3px;padding:0 10px;font-size:11px;font-weight:bold;}}'
                f'QPushButton:hover{{background:{C["secondary"]};}}')
        btn_close.setFixedSize(28, 28)
        btn_close.setStyleSheet(
            f'QPushButton{{background:{C["error"]};color:white;border:none;'
            f'border-radius:3px;font-size:12px;font-weight:bold;}}'
            f'QPushButton:hover{{background:#e74c3c;}}')

        tb_lo.addWidget(lbl_title)
        tb_lo.addStretch()
        tb_lo.addWidget(inp_search)
        tb_lo.addWidget(btn_cols)
        tb_lo.addWidget(btn_exp)
        tb_lo.addWidget(btn_copy)
        tb_lo.addWidget(btn_close)
        root.addWidget(toolbar)

        # ── Tabla dinámica ────────────────────────────────────────────────
        tbl = QTableWidget()
        tbl.setSortingEnabled(True)
        tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tbl.setAlternatingRowColors(True)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        tbl.horizontalHeader().setStretchLastSection(False)
        tbl.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        tbl.verticalHeader().setVisible(False)
        tbl.verticalHeader().setDefaultSectionSize(20)
        tbl.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        tbl.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        tbl.setWordWrap(False)
        tbl.setContextMenuPolicy(Qt.CustomContextMenu)
        tbl.setStyleSheet(
            f'QTableWidget{{border:1px solid {C["border"]};gridline-color:{C["border"]};'
            f'font-size:11px;background:{C["white"]};selection-background-color:{C["secondary"]};'
            f'selection-color:white;}}'
            f'QTableWidget::item{{padding:0 4px;border:none;}}'
            f'QTableWidget::item:alternate{{background:{C["alt"]};}}'
            f'QHeaderView::section{{background:{C["primary"]};color:white;padding:4px 3px;'
            f'font-weight:bold;font-size:10px;border:none;'
            f'border-right:1px solid rgba(255,255,255,0.2);}}'
        )

        # Llenar tabla
        headers = [lbl for _, lbl in vis]
        tbl.setColumnCount(len(vis))
        tbl.setHorizontalHeaderLabels(headers)
        tbl.setRowCount(n)
        ALN = Qt.AlignLeft | Qt.AlignVCenter
        YELLOW = QColor('#fffde7')   # amarillo claro para celdas con datos
        for r, feat in enumerate(features):
            for c, (fn, _) in enumerate(vis):
                try:    v = feat[fn]
                except: v = None
                txt  = self._fmt_cell(fn, v)
                item = QTableWidgetItem(txt)
                item.setTextAlignment(ALN)
                item.setData(Qt.UserRole, feat.id())
                if txt.strip():          # solo si tiene valor
                    item.setBackground(QBrush(YELLOW))
                tbl.setItem(r, c, item)
        tbl.resizeColumnsToContents()

        root.addWidget(tbl)

        # ── Barra de estado ───────────────────────────────────────────────
        lbl_status_ft = QLabel(f'{n} registro(s) mostrado(s)')
        lbl_status_ft.setStyleSheet(
            f'font-size:10px;color:#555;background:{C["info_bg"]};'
            f'border:1px solid {C["border"]};border-radius:3px;padding:2px 6px;')
        root.addWidget(lbl_status_ft)

        # ── Lógica: búsqueda en tiempo real ───────────────────────────────
        def _filter_table(text):
            tl = text.lower()
            visible = 0
            for r in range(tbl.rowCount()):
                show = any(
                    tl in (tbl.item(r, c).text() if tbl.item(r, c) else '').lower()
                    for c in range(tbl.columnCount())
                ) if tl else True
                tbl.setRowHidden(r, not show)
                if show:
                    visible += 1
            lbl_status_ft.setText(
                f'{visible} de {n} registro(s)' if tl else f'{n} registro(s)')

        inp_search.textChanged.connect(_filter_table)

        # ── Ocultar/mostrar columnas ──────────────────────────────────────
        def _toggle_columns():
            menu = QMenu(win)
            menu.setStyleSheet(
                f'QMenu{{background:{C["white"]};border:1px solid {C["border"]};font-size:11px;}}'
                f'QMenu::item{{padding:4px 20px;}}QMenu::item:selected{{background:{C["hover"]};}}'
            )
            for c, (_, lbl) in enumerate(vis):
                act = QAction(lbl, menu)
                act.setCheckable(True)
                act.setChecked(not tbl.isColumnHidden(c))
                act.setData(c)
                act.triggered.connect(lambda checked, col=c: tbl.setColumnHidden(col, not checked))
                menu.addAction(act)
            menu.exec_(btn_cols.mapToGlobal(btn_cols.rect().bottomLeft()))

        btn_cols.clicked.connect(_toggle_columns)

        # ── Exportar Excel ────────────────────────────────────────────────
        def _export_ft():
            from qgis.PyQt.QtWidgets import QFileDialog
            path, _ = QFileDialog.getSaveFileName(win, 'Exportar reporte', '', 'Excel (*.xlsx)')
            if not path: return
            if not path.lower().endswith('.xlsx'): path += '.xlsx'
            try:
                import openpyxl
                from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
                from openpyxl.utils import get_column_letter
                wb  = openpyxl.Workbook(); ws_x = wb.active; ws_x.title = 'Reporte'
                az='1a4b8c'; azc='2e86de'; gr='f0f4f8'
                FT = Font(name='Arial',bold=True,size=13,color='FFFFFF')
                FS = Font(name='Arial',size=9,color='FFFFFF')
                FH = Font(name='Arial',bold=True,size=10,color='FFFFFF')
                FV = Font(name='Arial',size=10)
                FA = PatternFill('solid',fgColor=az)
                FAC= PatternFill('solid',fgColor=azc)
                FG = PatternFill('solid',fgColor=gr)
                BD = Border(
                    bottom=Side(style='thin',color='cccccc'),
                    right=Side(style='thin',color='cccccc'))
                AL = Alignment(horizontal='left',  vertical='center', wrap_text=True)
                AC = Alignment(horizontal='center', vertical='center')
                fecha = QDate.currentDate().toString('dd/MM/yyyy')
                # Solo columnas visibles
                vis_cols = [(c, fn, lbl) for c,(fn,lbl) in enumerate(vis)
                            if not tbl.isColumnHidden(c)]
                nc = len(vis_cols)
                ws_x.merge_cells(f'A1:{get_column_letter(nc)}1')
                cell = ws_x['A1']
                cell.value = f'REPORTE PREDIAL — {lname}'
                cell.font=FT; cell.fill=FA; cell.alignment=AC
                ws_x.row_dimensions[1].height = 26
                ws_x.merge_cells(f'A2:{get_column_letter(nc)}2')
                cell = ws_x['A2']
                cell.value = f'Fecha: {fecha}   |   Registros visibles: {sum(1 for r in range(tbl.rowCount()) if not tbl.isRowHidden(r))}'
                cell.font=FS; cell.fill=FAC; cell.alignment=AC
                ws_x.row_dimensions[2].height = 16
                for ci,(_, fn_r, lbl_r) in enumerate(vis_cols, 1):
                    c2 = ws_x.cell(3, ci, lbl_r)
                    c2.font=FH; c2.fill=FA; c2.alignment=AC; c2.border=BD
                ws_x.row_dimensions[3].height = 18
                data_row = 4
                for r in range(tbl.rowCount()):
                    if tbl.isRowHidden(r): continue
                    ws_x.row_dimensions[data_row].height = 17
                    par = (data_row % 2 == 0)
                    for ci,(col_idx, fn_r, _) in enumerate(vis_cols, 1):
                        txt = (tbl.item(r, col_idx).text() if tbl.item(r, col_idx) else '')
                        try:
                            cv = int(txt) if txt.isdigit() else float(txt.replace('.','').replace(',','.'))
                        except Exception:
                            cv = txt
                        c2 = ws_x.cell(data_row, ci, cv)
                        c2.font=FV; c2.alignment=AL; c2.border=BD
                        if par: c2.fill=FG
                    data_row += 1
                for ci in range(1, nc+1):
                    ws_x.column_dimensions[get_column_letter(ci)].width = 16
                ws_x.freeze_panes = 'A4'
                ws_x.auto_filter.ref = f'A3:{get_column_letter(nc)}{data_row-1}'
                wb.save(path)
                lbl_status_ft.setText(f'✅ Excel exportado → {path}')
            except Exception as e:
                from qgis.PyQt.QtWidgets import QMessageBox
                QMessageBox.critical(win, 'Error', str(e))

        btn_exp.clicked.connect(_export_ft)

        # ── Copiar selección ──────────────────────────────────────────────
        def _copy_selection():
            from qgis.PyQt.QtWidgets import QApplication
            rows_sel = sorted(set(i.row() for i in tbl.selectedItems()))
            if not rows_sel: return
            vis_c = [c for c in range(tbl.columnCount()) if not tbl.isColumnHidden(c)]
            lines = ['	'.join(headers[c] for c in vis_c)]
            for r in rows_sel:
                lines.append('	'.join(
                    (tbl.item(r,c).text() if tbl.item(r,c) else '') for c in vis_c
                ))
            sep = chr(10)
            QApplication.clipboard().setText(sep.join(lines))
            lbl_status_ft.setText(f'📋 {len(rows_sel)} fila(s) copiadas al portapapeles')

        btn_copy.clicked.connect(_copy_selection)

        # ── Menú contextual ───────────────────────────────────────────────
        def _context_menu(pos):
            menu = QMenu(tbl)
            menu.setStyleSheet(
                f'QMenu{{background:{C["white"]};border:1px solid {C["border"]};font-size:11px;}}'
                f'QMenu::item{{padding:4px 20px;}}QMenu::item:selected{{background:{C["hover"]};}}'
            )
            act_copy = QAction('📋  Copiar selección', menu)
            act_copy.triggered.connect(_copy_selection)
            act_exp  = QAction('📊  Exportar Excel', menu)
            act_exp.triggered.connect(_export_ft)
            menu.addAction(act_copy); menu.addAction(act_exp)
            menu.exec_(tbl.viewport().mapToGlobal(pos))

        tbl.customContextMenuRequested.connect(_context_menu)
        btn_close.clicked.connect(win.hide)

        win.show()
        win.raise_()

    def _on_row_selected(self):
        rows = list({i.row() for i in self.table.selectedItems()})
        if not rows or not self.current_features: return
        idx = rows[0]
        if idx >= len(self.current_features): return
        self._nav_index = idx
        layer = self._active_layer()
        if layer:
            self._fill_form(self.current_features[idx], layer)
            n = len(self.current_features)
            self.lbl_count.setText(f'✅ Predio {idx+1} de {n}')
            self.btn_nav_prev.setEnabled(idx > 0)
            self.btn_nav_next.setEnabled(idx < n-1)
            self._zoom_to_features([self.current_features[idx]])

    def _fill_form(self, feat, layer):
        self._active_form.fill_from_feature(feat, layer)
        if not self.stack.isVisible():
            self.btn_collapse.setChecked(True)
        self.lbl_form_mode.setText('📋 Predio seleccionado')
        np = str(get_value(feat, layer, 'CODIGO') or '').strip()
        self._set_status(f'Predio {self._nav_index+1} de {len(self.current_features)} — {np}')

    def _nav_prev(self):
        if self.current_features and self._nav_index > 0:
            self._nav_index -= 1
            layer = self._active_layer()
            if layer:
                self._populate_table(layer, self.current_features)
                self._zoom_to_features([self.current_features[self._nav_index]])

    def _nav_next(self):
        if self.current_features and self._nav_index < len(self.current_features)-1:
            self._nav_index += 1
            layer = self._active_layer()
            if layer:
                self._populate_table(layer, self.current_features)
                self._zoom_to_features([self.current_features[self._nav_index]])

    # ── Búsqueda rápida ───────────────────────────────────────────────────────
    def _quick_search(self):
        texto = self.inp_quick.text().strip()
        if not texto: return
        layer = self._active_layer()
        if not layer:
            QMessageBox.warning(self, 'Sin capa', 'Selecciona una capa vectorial.')
            return
        safe = texto.replace("'", "''")
        # Buscar en todos los campos de texto + numéricos (CODIGO) de la capa
        partes = []
        for fld in layer.fields():
            fn = f'"{fld.name()}"'
            if fld.type() in STR_T:
                partes.append(f'{fn} ILIKE \'%{safe}%\'')
            elif fld.type() in NUM_T:
                partes.append(f'to_string({fn}) LIKE \'%{safe}%\'')
        if not partes:
            QMessageBox.information(self, 'Sin campos', 'La capa no tiene campos consultables.')
            return
        expr_str = ' OR '.join(partes)
        expr = QgsExpression(expr_str)
        if expr.hasParserError():
            return
        try:
            features = list(layer.getFeatures(QgsFeatureRequest().setFilterExpression(expr_str)))
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e)); return

        self.current_features = features
        self._all_field_names = [f.name() for f in layer.fields()]
        self._nav_index       = 0
        self._populate_table(layer, features)
        n = len(features)
        self.lbl_status.setText(f'⚡ Búsqueda rápida "{texto}": {n} resultado(s)')
        self._set_status(f'Búsqueda rápida: {n} resultado(s)')
        self._add_to_history(texto)
        if features: self._zoom_to_features(features)

    def _add_to_history(self, t):
        if t in self._search_history: self._search_history.remove(t)
        self._search_history.insert(0, t); self._search_history = self._search_history[:10]
        self.cbo_history.blockSignals(True)
        self.cbo_history.clear(); self.cbo_history.addItem('🕑')
        for h in self._search_history: self.cbo_history.addItem(h)
        self.cbo_history.setCurrentIndex(0); self.cbo_history.blockSignals(False)

    def _set_status(self, msg):
        if hasattr(self, 'lbl_status'): self.lbl_status.setText(msg)

    # ── Zoom / selección ──────────────────────────────────────────────────────
    def _zoom_to_features(self, features):
        layer = self._active_layer()
        if not layer or not features: return
        gt = QgsWkbTypes.geometryType(layer.wkbType())
        if gt in (QgsWkbTypes.PolygonGeometry, QgsWkbTypes.LineGeometry, QgsWkbTypes.PointGeometry):
            layer.selectByIds([f.id() for f in features])
            self.iface.setActiveLayer(layer)
            self.iface.actionZoomToSelected().trigger()

    def _select_on_map(self):
        layer = self._active_layer()
        if layer and self.current_features:
            layer.selectByIds([f.id() for f in self.current_features])
            self.iface.setActiveLayer(layer)

    def _zoom_to_selection(self):
        layer = self._active_layer()
        if layer and self.current_features:
            layer.selectByIds([f.id() for f in self.current_features])
            self.iface.setActiveLayer(layer)
            self.iface.actionZoomToSelected().trigger()

    # ── Exportar Excel ────────────────────────────────────────────────────────
    def _export_excel(self):
        if not self.current_features:
            QMessageBox.information(self, 'Sin datos', 'Realiza primero una búsqueda.'); return
        path, _ = QFileDialog.getSaveFileName(self, 'Exportar a Excel', '', 'Excel (*.xlsx)')
        if not path: return
        if not path.lower().endswith('.xlsx'): path += '.xlsx'
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter
        except ImportError:
            QMessageBox.critical(self, 'openpyxl no instalado', 'pip install openpyxl'); return
        try:
            layer = self._active_layer()
            fecha = QDate.currentDate().toString('dd/MM/yyyy')
            vis   = getattr(self, '_vis_fields', [(f.name(), f.name()) for f in (layer.fields() if layer else [])])
            cols  = [fn for fn, _ in vis]
            col_labels = [lbl for _, lbl in vis]
            ncols = len(cols)
            wb = openpyxl.Workbook(); ws = wb.active; ws.title = 'Consulta Predial'
            az='1a4b8c'; azc='2e86de'; gr='f0f4f8'
            FT=Font(name='Arial',bold=True,size=14,color='FFFFFF')
            FS=Font(name='Arial',size=10,color='FFFFFF')
            FH=Font(name='Arial',bold=True,size=10,color='FFFFFF')
            FV=Font(name='Arial',size=10)
            FA=PatternFill('solid',fgColor=az); FAC=PatternFill('solid',fgColor=azc); FG=PatternFill('solid',fgColor=gr)
            BD=Border(bottom=Side(style='thin',color='cccccc'),right=Side(style='thin',color='cccccc'))
            AL=Alignment(horizontal='left',vertical='center',wrap_text=True)
            AC=Alignment(horizontal='center',vertical='center')
            ws.merge_cells(f'A1:{get_column_letter(ncols)}1')
            c=ws['A1']; c.value='CONSULTAS CATASTRALES — IGAC Colombia'; c.font=FT; c.fill=FA; c.alignment=AC; ws.row_dimensions[1].height=28
            ws.merge_cells(f'A2:{get_column_letter(ncols)}2')
            c=ws['A2']; c.value=f'Capa: {layer.name() if layer else "—"}   |   {fecha}   |   {len(self.current_features):,} registros'; c.font=FS; c.fill=FAC; c.alignment=AC; ws.row_dimensions[2].height=18
            for ci,(h_real, h_lbl) in enumerate(zip(cols, col_labels),1):
                c=ws.cell(3,ci,h_lbl); c.font=FH; c.fill=FA; c.alignment=AC; c.border=BD
            ws.row_dimensions[3].height=20
            for ri,feat in enumerate(self.current_features,4):
                ws.row_dimensions[ri].height=18; par=(ri%2==0)
                for ci,fn in enumerate(cols,1):
                    try: v=feat[fn]
                    except: v=None
                    raw=self._fmt_cell(fn, v)
                    try:
                        cv=int(raw) if raw.isdigit() else float(raw.replace('.','').replace(',','.'))
                    except Exception:
                        cv=raw
                    c=ws.cell(ri,ci,cv); c.font=FV; c.alignment=AL; c.border=BD
                    if par: c.fill=FG
            for ci,h in enumerate(cols,1):
                ws.column_dimensions[get_column_letter(ci)].width=max(len(str(h))+3,14)
            ws.freeze_panes='A4'
            ws.auto_filter.ref=f'A3:{get_column_letter(ncols)}{3+len(self.current_features)}'
            wb.save(path)
            QMessageBox.information(self,'Excel exportado',f'✅ {len(self.current_features):,} registros → {path}')
            self._set_status(f'Excel exportado: {len(self.current_features)} registros')
        except Exception as e:
            QMessageBox.critical(self,'Error Excel',str(e))

    def _clear_all(self):
        if self._active_form: self._active_form.clear()
        self.table.setRowCount(0); self.table.setColumnCount(0)
        self.current_features=[]; self._nav_index=0
        self.lbl_count.setText('Sin resultados')
        self.lbl_count.setStyleSheet(f'font-weight:bold;font-size:11px;color:{C["primary"]};background:transparent;')
        self.btn_nav_prev.setEnabled(False); self.btn_nav_next.setEnabled(False)
        self.lbl_form_mode.setText(''); self.inp_quick.clear()
        self.lbl_expr.setVisible(False); self.lbl_warn.setVisible(False)
        self._set_status('Formulario limpiado.')
