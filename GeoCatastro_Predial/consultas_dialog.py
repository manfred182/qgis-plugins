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

import html

from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox,
    QAbstractItemView, QScrollArea, QFrame, QSizePolicy,
    QMessageBox, QStackedWidget, QShortcut, QFileDialog,
    QListWidget, QListWidgetItem, QDialog, QDialogButtonBox,
    QApplication,
)
from qgis.PyQt.QtCore import Qt, QVariant, QSettings, QSize, QPoint, QDate, QTimer
from qgis.PyQt.QtGui import QKeySequence, QColor, QBrush
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFeatureRequest,
    QgsExpression, QgsWkbTypes,
)

from .igac_dominios import DESTINO_ECONOMICO, TIPO_DOCUMENTO, ESTRATO

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
    'VEREDA_CODIGO':       [
        'MANZANA_VEREDA_CODIGO', 'manzana_vereda_codigo',
        'VEREDA_CODIGO', 'vereda_codigo', 'VER_COD',
        'MANZANA_CODIGO', 'manzana_codigo', 'MAN_COD',
    ],
    'MANZANA_VEREDA_CODIGO': [
        'MANZANA_VEREDA_CODIGO', 'manzana_vereda_codigo',
        'MANZANA_CODIGO', 'manzana_codigo', 'VEREDA_CODIGO', 'vereda_codigo',
    ],
    'NUMERO_SUBTERRANEOS': ['NUMERO_SUBTERRANEOS', 'numero_subterraneos', 'NUM_SUBT', 'NSUBTERR'],
    'SHAPE_Area':          ['SHAPE_Area', 'shape_area', 'SHAPE_AREA', 'Shape_Area'],
    'SHAPE_Length':        ['SHAPE_Length', 'shape_length', 'SHAPE_LENGTH', 'Shape_Length'],
    'TIPO_CONSTRUCCION':   ['TIPO_CONSTRUCCION', 'tipo_construccion', 'TIPO_CONS'],
    'TIPO_DOMINIO':        ['TIPO_DOMINIO', 'tipo_dominio', 'TIPO_DOM'],
    'NUMERO_PISOS':        ['NUMERO_PISOS', 'numero_pisos', 'NUM_PISOS'],
    'NUMERO_SOTANOS':      ['NUMERO_SOTANOS', 'numero_sotanos', 'NUM_SOT'],
    'NUMERO_MEZANINES':    ['NUMERO_MEZANINES', 'numero_mezanines', 'NUM_MEZ'],
    'NUMERO_SEMISOTANOS':  ['NUMERO_SEMISOTANOS', 'numero_semisotanos', 'NUM_SEMISOT'],
    'IDENTIFICADOR':       ['IDENTIFICADOR', 'identificador', 'IDENTIFICA'],
    'ETIQUETA':            ['ETIQUETA', 'etiqueta'],
    'CODIGO_EDIFICACION':  ['CODIGO_EDIFICACION', 'codigo_edificacion', 'COD_EDIF'],
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
    'NOMBRE_VEREDA':       ['NOMBRE_VEREDA', 'nombre_vereda', 'NOM_VERED',
                            'NOM_BARRI', 'NOMBRE'],
    # ── Origen del predio (lo genera el merge de la GDB: URBANO/RURAL vs
    # URBANO_INFORMAL/RURAL_INFORMAL) ───────────────────────────────────────
    'ORIGEN':              ['ORIGEN', 'origen'],
}

# La deteccion de campos unidos puede recorrer decenas o cientos de columnas.
# Se conserva un indice por capa y se invalida al cambiar/refrescar la capa.
_FIELD_INDEX_CACHE = {}


def _normalized_field_name(value: str) -> str:
    return (value.lower().replace(' ', '').replace('(', '').replace(')', '')
            .replace('$', '').replace('_', '').replace('/', ''))


def _clear_field_index(layer=None):
    if layer is None:
        _FIELD_INDEX_CACHE.clear()
        return
    try:
        key = layer.id()
    except (AttributeError, RuntimeError):
        key = id(layer)
    _FIELD_INDEX_CACHE.pop(key, None)


def _field_index(layer):
    """Crea una sola vez los indices usados por ``resolve_field``."""
    try:
        key = layer.id()
    except (AttributeError, RuntimeError):
        key = id(layer)
    fields = layer.fields()
    count = fields.count()
    cached = _FIELD_INDEX_CACHE.get(key)
    if cached and cached['count'] == count:
        return cached

    names = [field.name() for field in fields]
    aliases = []
    for position, name in enumerate(names):
        try:
            alias = layer.attributeAlias(position)
        except AttributeError:
            alias = ''
        if alias and alias != name:
            aliases.append((name, alias))
    cached = {
        'count': count,
        'real': set(names),
        'low': {name.lower(): name for name in names},
        'normalized': [(name, name.lower(), _normalized_field_name(name))
                       for name in names],
        'resolved': {},
    }
    _FIELD_INDEX_CACHE[key] = cached
    for name, alias in aliases:
        cached['low'].setdefault(alias.lower(), name)
        cached['normalized'].append((name, alias.lower(), _normalized_field_name(alias)))
    return cached


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


def resolve_field(layer, semantic: str):
    """
    Devuelve el nombre REAL del campo en la capa para el identificador semántico dado.
    Primero prueba candidatos exactos, luego busca por sufijo (join con prefijo variable).
    Maneja campos con espacios en el nombre (ej. 'Avaluo Catastral' → '18479-R1_Avaluo Catastral').
    """
    candidates = _FIELD_CANDIDATES.get(semantic, [semantic])
    index = _field_index(layer)
    resolved = index['resolved']
    if semantic in resolved:
        return resolved[semantic]
    fields_real = index['real']
    fields_low = index['low']

    # 1. Coincidencia exacta (con o sin mayúsculas)
    for c in candidates:
        if c in fields_real:
            resolved[semantic] = c
            return c
        if c.lower() in fields_low:
            result = fields_low[c.lower()]
            resolved[semantic] = result
            return result

    # 2. Sufijo / coincidencia parcial con prefijo join
    for c in candidates:
        c_low  = c.lower()
        c_bare = _normalized_field_name(c)

        for fn_real, fl, fl_bare in index['normalized']:

            # a) Terminación exacta (con o sin separador)
            if fl.endswith(c_low) and len(fl) > len(c_low):
                resolved[semantic] = fn_real
                return fn_real

            # b) Terminación en versión bare (sin espacios/paréntesis/$)
            if fl_bare.endswith(c_bare) and len(c_bare) >= 4 and len(fl_bare) > len(c_bare):
                resolved[semantic] = fn_real
                return fn_real

            # c) Coincidencia exacta bare
            if fl_bare == c_bare and len(c_bare) >= 4:
                resolved[semantic] = fn_real
                return fn_real

    resolved[semantic] = None
    return None


def build_like(layer, semantic: str, value: str, exact=False):
    """
    Construye una cláusula ILIKE para el campo semántico dado.
    Devuelve None si el campo no existe en la capa.
    """
    real = resolve_field(layer, semantic)
    if not real:
        return None
    fields = layer.fields()
    field_index = fields.indexFromName(real)
    if field_index < 0:
        return None
    fld = fields.field(field_index)
    safe = value.strip().replace("'", "''")
    fn = '"{}"'.format(real.replace('"', '""'))
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


def _is_null_value(value):
    return value is None or str(value).strip() in ('', 'None', 'NULL')


def _value_text(value):
    return '' if _is_null_value(value) else str(value).strip()


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
    if _is_null_value(val): return ''
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


def _fmt_currency(value):
    """Formatea pesos sin alterar valores decimales ni separadores de miles."""
    if _is_null_value(value):
        return ''
    try:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            number = int(float(value))
        else:
            raw = str(value).strip().replace('$', '').replace(' ', '')
            if ',' in raw and '.' in raw:
                if raw.rfind(',') > raw.rfind('.'):
                    raw = raw.replace('.', '').replace(',', '.')
                else:
                    raw = raw.replace(',', '')
            elif raw.count('.') > 1:
                raw = raw.replace('.', '')
            elif raw.count(',') > 1:
                raw = raw.replace(',', '')
            elif ',' in raw:
                left, right = raw.rsplit(',', 1)
                raw = left + ('.' + right if len(right) <= 2 else right)
            number = int(float(raw))
        return '$ ' + f'{number:,}'.replace(',', '.')
    except (TypeError, ValueError):
        return str(value)


def _excel_safe_text(value):
    """Neutraliza formulas al exportar o copiar datos controlados por capas."""
    text = '' if _is_null_value(value) else str(value)
    if text.startswith(('=', '+', '-', '@', '\t', '\r')):
        return "'" + text
    return text

def _fmt_tipo_doc(code):
    return TIPO_DOCUMENTO.get(str(code or '').strip(), str(code or ''))


# ─────────────────────────────────────────────────────────────────────────────
#  FORMULARIO UNIFICADO
# ─────────────────────────────────────────────────────────────────────────────

class FormTerreno(QWidget):
    # Combos de dominio (decodifican codigo -> etiqueta). Se bloquean al
    # mostrar un predio/construccion seleccionado para que no se abran por
    # accidente ni se cambien sin querer; se desbloquean con clear() al
    # iniciar una busqueda nueva.
    _FILTER_COMBO_KEYS = ('TipoDoc_cbo', 'DestinoEc_cbo', 'Estrato_cbo')

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

        self.f['VEREDA_CODIGO'] = _inp('Código de manzana o vereda')
        add('Cód. Manzana/Vereda:', self.f['VEREDA_CODIGO'], row, 0)

        # Vereda/Barrio: campo de solo lectura
        self.lbl_vereda = QLabel('')
        self.lbl_vereda.setTextFormat(Qt.PlainText)
        self.lbl_vereda.setStyleSheet(
            f'font-size:10px;color:{C["primary"]};font-style:italic;'
            f'background:{C["info_bg"]};border-radius:3px;padding:1px 5px;')
        g.addWidget(_lbl('Manzana / Vereda:'), row, 2)
        g.addWidget(self.lbl_vereda, row, 3); row += 1

        # Condición del predio (Formal/Informal): solo lectura, calculada del
        # campo ORIGEN que genera el merge de la GDB.
        self.f['CONDICION_PREDIO'] = _inp('Formal / Informal')
        self.f['CONDICION_PREDIO'].setReadOnly(True)
        add('Condición:', self.f['CONDICION_PREDIO'], row, 0); row += 1

        # ── Construcción (campos propios de la capa, solo si el registro es
        # una construcción; quedan vacíos en un predio) ─────────────────────
        g.addWidget(_sec('Construcción'), row, 0, 1, 4); row += 1

        self.f['TIPO_CONSTRUCCION'] = _inp('Convencional / No convencional')
        self.f['TIPO_DOMINIO']      = _inp('Tipo de dominio')
        add('Tipo construcción:', self.f['TIPO_CONSTRUCCION'], row, 0)
        add('Tipo dominio:',      self.f['TIPO_DOMINIO'],      row, 1); row += 1

        self.f['IDENTIFICADOR']      = _inp('Unidad dentro del predio (A, B, C…)')
        self.f['CODIGO_EDIFICACION'] = _inp('Código de edificación')
        add('Identificador:',        self.f['IDENTIFICADOR'],      row, 0)
        add('Cód. edificación:',     self.f['CODIGO_EDIFICACION'], row, 1); row += 1

        self.f['NUMERO_PISOS']   = _inp('Pisos')
        self.f['NUMERO_SOTANOS'] = _inp('Sótanos')
        add('No. pisos:',    self.f['NUMERO_PISOS'],   row, 0)
        add('No. sótanos:',  self.f['NUMERO_SOTANOS'], row, 1); row += 1

        self.f['NUMERO_MEZANINES']   = _inp('Mezanines')
        self.f['NUMERO_SEMISOTANOS'] = _inp('Semisótanos')
        add('No. mezanines:',    self.f['NUMERO_MEZANINES'],   row, 0)
        add('No. semisótanos:',  self.f['NUMERO_SEMISOTANOS'], row, 1); row += 1

        self.f['ETIQUETA'] = _inp('Etiqueta de la construcción')
        add('Etiqueta:', self.f['ETIQUETA'], row, 0); row += 1

        # ── Propietario (campos R1) ────────────────────────────────────────
        g.addWidget(_sec('Propietario'), row, 0, 1, 4); row += 1

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
        g.addWidget(_sec('Áreas'), row, 0, 1, 4); row += 1

        self.f['Area Terreno(m2)']     = _inp('m²')
        self.f['Area Construida (m2)'] = _inp('m²')
        add('Área Terreno (m²):',    self.f['Area Terreno(m2)'],     row, 0)
        add('Área Construida (m²):', self.f['Area Construida (m2)'], row, 1); row += 1

        # ── Áreas geométricas GDB ─────────────────────────────────────────
        self.f['SHAPE_Area']   = _inp('m²')
        self.f['SHAPE_Length'] = _inp('m')
        add('Área Geográfica (m²):', self.f['SHAPE_Area'],   row, 0)
        add('Perímetro (m):',        self.f['SHAPE_Length'], row, 1); row += 1

        # ── Áreas / perímetro calculados (ha, km) ────────────────────────
        self.f['Area Terreno(ha)'] = _inp('ha')
        self.f['Area Terreno(ha)'].setReadOnly(True)
        self.f['SHAPE_Area_ha']    = _inp('ha')
        self.f['SHAPE_Area_ha'].setReadOnly(True)
        add('Área Terreno (ha):',    self.f['Area Terreno(ha)'], row, 0)
        add('Área Geográfica (ha):', self.f['SHAPE_Area_ha'],    row, 1); row += 1

        self.f['SHAPE_Length_km'] = _inp('km')
        self.f['SHAPE_Length_km'].setReadOnly(True)
        add('Perímetro (km):', self.f['SHAPE_Length_km'], row, 0); row += 1

        # ── Información Jurídica ─────────────────────────────────────────
        g.addWidget(_sec('Información Jurídica'), row, 0, 1, 4); row += 1

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
    def build_expression(self, layer):
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

        # Construcción
        if self._txt('TIPO_CONSTRUCCION'):
            filtros['TIPO_CONSTRUCCION'] = self._txt('TIPO_CONSTRUCCION')
        if self._txt('TIPO_DOMINIO'):
            filtros['TIPO_DOMINIO'] = self._txt('TIPO_DOMINIO')
        if self._txt('IDENTIFICADOR'):
            filtros['IDENTIFICADOR'] = self._txt('IDENTIFICADOR')
        if self._txt('CODIGO_EDIFICACION'):
            filtros['CODIGO_EDIFICACION'] = self._txt('CODIGO_EDIFICACION')
        if self._txt('NUMERO_PISOS'):
            filtros['NUMERO_PISOS'] = self._txt('NUMERO_PISOS')
        if self._txt('NUMERO_SOTANOS'):
            filtros['NUMERO_SOTANOS'] = self._txt('NUMERO_SOTANOS')
        if self._txt('NUMERO_MEZANINES'):
            filtros['NUMERO_MEZANINES'] = self._txt('NUMERO_MEZANINES')
        if self._txt('NUMERO_SEMISOTANOS'):
            filtros['NUMERO_SEMISOTANOS'] = self._txt('NUMERO_SEMISOTANOS')
        if self._txt('ETIQUETA'):
            filtros['ETIQUETA'] = self._txt('ETIQUETA')

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
            txt = _value_text(v)
            w.blockSignals(True)
            w.setText(txt)
            w.setStyleSheet(ds_filled if txt else ds_empty)
            w.blockSignals(False)

        def _sc(key, semantic):
            w = self.f.get(key)
            if not isinstance(w, QComboBox): return
            v = get_value(feat, layer, semantic)
            vs = _value_text(v)
            idx = w.findData(vs)
            if idx < 0: idx = w.findText(vs, Qt.MatchContains)
            w.blockSignals(True)
            w.setCurrentIndex(idx if idx >= 0 else 0)
            w.blockSignals(False)

        # GDB
        _s('CODIGO',          'CODIGO')
        _s('CODIGO_ANTERIOR', 'CODIGO_ANTERIOR')
        _s('VEREDA_CODIGO',   'VEREDA_CODIGO')

        # Condición del predio: el merge marca el ORIGEN como
        # URBANO_INFORMAL/RURAL_INFORMAL para predios informales, y
        # URBANO/RURAL para los formales.
        origen_v = _value_text(get_value(feat, layer, 'ORIGEN')).strip().upper()
        w_cond = self.f.get('CONDICION_PREDIO')
        if isinstance(w_cond, QLineEdit):
            if origen_v.endswith('INFORMAL'):
                txt = 'Informal'
            elif origen_v:
                txt = 'Formal'
            else:
                txt = ''
            w_cond.setText(txt)
            w_cond.setStyleSheet(ds_filled if txt else ds_empty)

        # Construcción (vacío en un predio; solo trae datos cuando el
        # registro activo es una construcción)
        _s('TIPO_CONSTRUCCION',  'TIPO_CONSTRUCCION')
        _s('TIPO_DOMINIO',       'TIPO_DOMINIO')
        _s('IDENTIFICADOR',      'IDENTIFICADOR')
        _s('CODIGO_EDIFICACION', 'CODIGO_EDIFICACION')
        _s('NUMERO_PISOS',       'NUMERO_PISOS')
        _s('NUMERO_SOTANOS',     'NUMERO_SOTANOS')
        _s('NUMERO_MEZANINES',   'NUMERO_MEZANINES')
        _s('NUMERO_SEMISOTANOS', 'NUMERO_SEMISOTANOS')
        _s('ETIQUETA',           'ETIQUETA')

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
        dir_v = get_value(feat, layer, 'Direccion')
        if _is_null_value(dir_v):
            dir_v = get_value(feat, layer, 'TEXTO')
        w_dir = self.f.get('Direccion')
        if isinstance(w_dir, QLineEdit):
            txt = _value_text(dir_v)
            w_dir.setText(txt); w_dir.setStyleSheet(ds_filled if txt else ds_empty)

        # Buscar avalúo: primero por resolve_field, luego buscar manualmente cualquier
        # campo que contenga 'avaluo' o 'R_Avaluo' en la capa
        avaluo = get_value(feat, layer, 'Avaluo Catastral')
        if _is_null_value(avaluo):
            for fld in layer.fields():
                fl = fld.name().lower().replace(' ', '').replace('(', '').replace(')', '').replace('$', '')
                if 'avaluo' in fl or fl.startswith('r_avaluo'):
                    try:
                        v = feat[fld.name()]
                        if v is not None and str(v).strip() not in ('', 'None', 'NULL'):
                            avaluo = v
                            break
                    except (KeyError, RuntimeError, TypeError, IndexError):
                        continue
        w_av = self.f.get('Avaluo Catastral')
        if isinstance(w_av, QLineEdit):
            txt = _fmt_currency(avaluo)
            w_av.setText(txt); w_av.setStyleSheet(ds_filled if txt else ds_empty)

        at = get_value(feat, layer, 'Area Terreno(m2)')
        ac = get_value(feat, layer, 'Area Construida (m2)')
        w_at = self.f.get('Area Terreno(m2)')
        w_ac = self.f.get('Area Construida (m2)')
        if isinstance(w_at, QLineEdit):
            txt = _fmt_area(at); w_at.setText(txt); w_at.setStyleSheet(ds_filled if txt else ds_empty)
        if isinstance(w_ac, QLineEdit):
            txt = _fmt_area(ac); w_ac.setText(txt); w_ac.setStyleSheet(ds_filled if txt else ds_empty)

        # Área/perímetro calculados: ha = m² / 10.000, km = m / 1.000
        def _calc(key, raw_value, divisor):
            w = self.f.get(key)
            if not isinstance(w, QLineEdit):
                return
            txt = ''
            if not _is_null_value(raw_value):
                try:
                    txt = _fmt_area(float(str(raw_value).replace(',', '.')) / divisor)
                except (TypeError, ValueError):
                    txt = ''
            w.setText(txt)
            w.setStyleSheet(ds_filled if txt else ds_empty)

        _calc('Area Terreno(ha)', at, 10000)
        _calc('SHAPE_Area_ha', ag, 10000)
        _calc('SHAPE_Length_km', al, 1000)

        # Vereda / Barrio
        ver_cod = str(get_value(feat, layer, 'VEREDA_CODIGO') or '').strip()
        ver_nom = _value_text(get_value(feat, layer, 'NOMBRE_VEREDA'))
        if not ver_nom:
            ver_nom = _buscar_nombre_vereda(ver_cod)
        self.lbl_vereda.setText(ver_nom or ver_cod)

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

        # Se esta mostrando un resultado: bloquear los combos de dominio
        # para que no se abran/cambien sin querer mientras solo se consulta.
        for key in self._FILTER_COMBO_KEYS:
            w = self.f.get(key)
            if isinstance(w, QComboBox):
                w.setEnabled(False)

    def clear(self):
        ss = (f"QLineEdit{{border:1px solid {C['border']};border-radius:3px;"
              f"padding:2px 5px;background:{C['white']};font-size:11px;"
              f"color:{C['text']};min-height:18px;}}")
        for w in self.f.values():
            if isinstance(w, QLineEdit):
                w.clear(); w.setStyleSheet(ss)
            elif isinstance(w, QComboBox):
                w.setCurrentIndex(0)
        # Nueva busqueda: los combos vuelven a ser editables como filtro.
        for key in self._FILTER_COMBO_KEYS:
            w = self.f.get(key)
            if isinstance(w, QComboBox):
                w.setEnabled(True)
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
            fields = lyr.fields()
            indices = [fields.indexFromName(cod_f), fields.indexFromName(nom_f)]
            request = QgsFeatureRequest()
            request.setSubsetOfAttributes(indices)
            request.setFlags(QgsFeatureRequest.NoGeometry)
            try:
                for feat in lyr.getFeatures(request):
                    c = _value_text(feat[cod_f])
                    n = _value_text(feat[nom_f])
                    if c and n:
                        _VEREDA_CACHE[c] = n
            except (KeyError, RuntimeError, TypeError, IndexError):
                continue
    _VEREDA_LOADED[0] = True


def _buscar_nombre_vereda(codigo):
    _cargar_vereda()
    return _VEREDA_CACHE.get(codigo, '')


def _norm_nombre(texto):
    """Normaliza un nombre para comparar: minúsculas, sin tildes ni ñ."""
    t = str(texto or '').strip().lower()
    for a, b in (('á', 'a'), ('é', 'e'), ('í', 'i'), ('ó', 'o'),
                 ('ú', 'u'), ('ü', 'u'), ('ñ', 'n')):
        t = t.replace(a, b)
    return t


def _buscar_codigos_por_nombre(nombre):
    """Devuelve los códigos de vereda cuyo NOMBRE coincide con el texto dado.

    Prioriza la coincidencia exacta; si no hay ninguna, admite coincidencias
    parciales (contiene). Insensible a mayúsculas y tildes. Permite consultar
    por nombre de vereda como si fuera por su código.
    """
    _cargar_vereda()
    objetivo = _norm_nombre(nombre)
    if not objetivo:
        return []
    exactos, parciales = [], []
    for cod, nom in _VEREDA_CACHE.items():
        n = _norm_nombre(nom)
        if n == objetivo:
            exactos.append(cod)
        elif objetivo in n:
            parciales.append(cod)
    return exactos if exactos else parciales


def _resolve_nombre_vereda_field(layer):
    """Nombre real del campo del NOMBRE de la vereda en la capa.

    Exige que el nombre del campo contenga 'nombre' y 'vereda' para no
    confundirlo con el 'Nombre' del propietario ni con la 'Dirección'.
    """
    for f in layer.fields():
        n = f.name().lower().replace(' ', '').replace('_', '')
        if 'nombre' in n and 'vereda' in n:
            return f.name()
    return None


def _codigos_vereda_en_capa(layer, nombre):
    """Códigos territoriales cuyo NOMBRE_VEREDA coincide, leídos de la PROPIA
    capa consultada (campos NOMBRE_VEREDA ↔ MANZANA_VEREDA_CODIGO).

    Es independiente de la GDB y de que R_VEREDA esté cargada: funciona con
    cualquier base y siempre queda al día, porque lee la capa que se consulta.
    Prioriza la coincidencia exacta; si no hay, admite parcial (contiene).
    """
    if layer is None:
        return []
    nom_field = _resolve_nombre_vereda_field(layer)
    cod_field = resolve_field(layer, 'VEREDA_CODIGO')
    objetivo = _norm_nombre(nombre)
    if not nom_field or not cod_field or not objetivo:
        return []
    fields = layer.fields()
    idx_n = fields.indexFromName(nom_field)
    idx_c = fields.indexFromName(cod_field)
    if idx_n < 0 or idx_c < 0:
        return []
    req = QgsFeatureRequest()
    req.setSubsetOfAttributes([idx_n, idx_c])
    req.setFlags(QgsFeatureRequest.NoGeometry)
    exactos, parciales = set(), set()
    try:
        for feat in layer.getFeatures(req):
            n = _norm_nombre(feat[nom_field])
            c = _value_text(feat[cod_field])
            if not c or not n:
                continue
            if n == objetivo:
                exactos.add(c)
            elif objetivo in n:
                parciales.add(c)
    except (KeyError, RuntimeError, TypeError, IndexError):
        return []
    return sorted(exactos) if exactos else sorted(parciales)


def _reset_vereda_cache():
    _VEREDA_LOADED[0] = False
    _VEREDA_CACHE.clear()


_QUERY_RESULT_PROPERTY = 'geocatastro_predial/query_result'
_OMISSIONS_LAYER_PROPERTY = 'geocatastro_predial/omissions_layer_id'
_OMISSIONS_COUNT_PROPERTY = 'geocatastro_predial/omissions_count'
_OMISSIONS_TABLE_PROPERTY = 'geocatastro_predial/omissions_table'


def _is_query_result_layer(layer):
    """True solo para capas consolidadas creadas para consultar en el plugin."""
    try:
        marker = layer.customProperty(_QUERY_RESULT_PROPERTY, False)
        if marker is True or str(marker).lower() in ('1', 'true', 'yes'):
            return True
    except (AttributeError, RuntimeError):
        pass
    try:
        # Compatibilidad con resultados creados por una versión anterior.
        return layer.name().lower().startswith('predios_consolidados')
    except (AttributeError, RuntimeError):
        return False


# ─────────────────────────────────────────────────────────────────────────────
#  DIÁLOGO PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

class ConsultasPredialesDialog(QWidget):
    AUTO_ZOOM_MAX_FEATURES = 500
    MAX_QUERY_RESULTS = 5000
    MAX_PDF_FEATURES = 200

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface            = iface
        self.current_features = []
        self._all_field_names = []
        self._nav_index       = 0
        self._feature_index_by_id = {}
        self._results_layer_id = None
        self._results_truncated = False
        self._schema_layer = None
        self._float_win = None
        self._float_table = None
        self._project_signals_connected = False
        self._active_form     = None
        self._build_ui()
        self._connect_signals()
        self._refresh_layers()
        self._restore_geometry()

    def _max_window_size(self):
        """
        Limita el tamaño de la ventana al marco de la ventana de QGIS (o a la
        pantalla disponible si no se puede leer) para que nunca quede más alta
        que el espacio visible y obligue a desplazarse con la barra lateral.
        """
        geo = None
        try:
            main = self.iface.mainWindow()
        except (AttributeError, RuntimeError):
            main = None
        if main is not None:
            geo = main.geometry()
        if geo is None:
            screen = QApplication.primaryScreen()
            geo = screen.availableGeometry() if screen else None
        if geo is None:
            return 700, 760
        return max(400, geo.width() - 40), max(300, geo.height() - 60)

    def _restore_geometry(self):
        s = QSettings('HerramientaCatastral', 'v32')
        size = s.value('size', QSize(700, 760))
        if not isinstance(size, QSize):
            size = QSize(700, 760)
        max_w, max_h = self._max_window_size()
        self.resize(min(size.width(), max_w), min(size.height(), max_h))
        pos = s.value('pos', None)
        if pos and isinstance(pos, QPoint):
            self.move(pos)

    def closeEvent(self, event):
        s = QSettings('HerramientaCatastral', 'v32')
        s.setValue('size', self.size()); s.setValue('pos', self.pos())
        if self._float_win is not None:
            self._float_win.hide()
        super().closeEvent(event)

    def hide_windows(self):
        if self._float_win is not None:
            self._float_win.hide()
        self.hide()

    def shutdown(self):
        """Libera señales y ventanas cuando QGIS descarga el complemento."""
        if self._project_signals_connected:
            project = QgsProject.instance()
            for signal in (project.layersAdded, project.layersRemoved):
                try:
                    signal.disconnect(self._refresh_layers)
                except (TypeError, RuntimeError):
                    pass
            self._project_signals_connected = False
        self._watch_layer_schema(None)
        if self._float_win is not None:
            self._float_win.close()
            self._float_win.deleteLater()
            self._float_win = None
            self._float_table = None
        self.close()
        self.deleteLater()

    # ── Build UI ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.setStyleSheet(f'background:{C["bg"]};color:{C["text"]};')
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10); root.setSpacing(8)
        self._build_header(root)
        scroll, tl = self._build_scroll_area()
        self._build_tools_row(tl)
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
        tc.addWidget(QLabel('LADM-COL  |  v3.2', styleSheet='color:rgba(255,255,255,0.82);font-size:9px;background:transparent;'))
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

    # (El recorte contra capas activas se calcula automaticamente en
    # map_pdf_export.export_predial_selection_pdf, sin seleccion manual.)

    def _build_action_btns(self, tl):
        r = QHBoxLayout(); r.setSpacing(6)
        self.btn_search = _btn('🔎  Buscar')
        self.btn_clear  = _btn('✖  Limpiar',    primary=False)
        self.btn_select = _btn('✔  Seleccionar', primary=False)
        self.btn_zoom   = _btn('⌖  Zoom',        primary=False)
        for b in [self.btn_search, self.btn_clear, self.btn_select, self.btn_zoom]:
            r.addWidget(b, 1)
        tl.addLayout(r)

    def _build_tools_row(self, tl):
        r = QHBoxLayout(); r.setSpacing(5)
        self.btn_direct_merge = _btn(
            '⚡  Crear capa consultable desde .GDB + R1 + R2', color='#8e44ad')
        self.btn_omissions = _btn(
            '📋  Omisiones gráficas', color='#d35400')
        self.btn_omissions.setEnabled(False)
        r.addWidget(self.btn_direct_merge, 2)
        r.addWidget(self.btn_omissions, 1)
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
        # Barra inferior compacta: estado + salidas visibles.
        bar = QFrame()
        bar.setStyleSheet(
            f'QFrame{{background:{C["header"]};border:1px solid {C["border"]};border-radius:4px;}}')
        bar_lo = QHBoxLayout(bar)
        bar_lo.setContentsMargins(8, 3, 6, 3)
        bar_lo.setSpacing(8)

        self.lbl_status = QLabel('Listo.')
        self.lbl_status.setTextFormat(Qt.PlainText)
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

        self.btn_pdf_bar = QPushButton('🗺  Salida gráfica PDF')
        self.btn_pdf_bar.setFixedHeight(24)
        self.btn_pdf_bar.setStyleSheet(
            f'QPushButton{{background:{C["error"]};color:white;border:none;'
            f'border-radius:3px;padding:0 12px;font-size:10px;font-weight:bold;}}'
            f'QPushButton:hover{{background:#a93226;}}'
            f'QPushButton:disabled{{background:#aaa;}}')

        bar_lo.addWidget(self.lbl_status, 1)
        bar_lo.addWidget(self.btn_export_bar)
        bar_lo.addWidget(self.btn_pdf_bar)
        self.btn_pdf_query = QPushButton('🗺  PDF consulta / vereda')
        self.btn_pdf_query.setToolTip('Exporta todos los resultados del buscador con mapa conjunto, grilla geografica y fichas.')
        self.btn_pdf_query.clicked.connect(lambda: self._export_map_pdf(query=True))
        bar_lo.addWidget(self.btn_pdf_query)
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
        self.btn_export_bar.clicked.connect(self._export_excel)
        self.btn_pdf_bar.clicked.connect(self._export_map_pdf)
        self.cbo_layer.currentIndexChanged.connect(self._on_layer_changed)
        self.btn_nav_prev.clicked.connect(self._nav_prev)
        self.btn_nav_next.clicked.connect(self._nav_next)
        self.btn_diag.clicked.connect(self._show_diagnostics)
        self.btn_direct_merge.clicked.connect(self._open_direct_merge)
        self.btn_omissions.clicked.connect(self._export_graphic_omissions)
        QgsProject.instance().layersAdded.connect(self._refresh_layers)
        QgsProject.instance().layersRemoved.connect(self._refresh_layers)
        self._project_signals_connected = True
        QShortcut(QKeySequence('F5'),     self, self._run_search)
        QShortcut(QKeySequence('Escape'), self, self._clear_all)
        QShortcut(QKeySequence('Ctrl+E'), self, self._export_excel)
        QShortcut(QKeySequence('Ctrl+P'), self, self._export_map_pdf)
        QShortcut(QKeySequence('Ctrl+Z'), self, self._zoom_to_selection)

    # ── Capas ─────────────────────────────────────────────────────────────────
    def _refresh_layers(self, *_):
        _clear_field_index()
        _reset_vereda_cache()
        self.cbo_layer.blockSignals(True)
        prev = self.cbo_layer.currentData()
        self.cbo_layer.clear()
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr, QgsVectorLayer) and _is_query_result_layer(lyr):
                self.cbo_layer.addItem(lyr.name(), lyr.id())
        idx = self.cbo_layer.findData(prev)
        if idx >= 0: self.cbo_layer.setCurrentIndex(idx)
        self.cbo_layer.blockSignals(False)
        self._on_layer_changed()

    def _active_layer(self):
        lid = self.cbo_layer.currentData()
        return QgsProject.instance().mapLayer(lid) if lid else None

    def _watch_layer_schema(self, layer):
        if self._schema_layer is layer:
            return
        if self._schema_layer is not None:
            old_layer = self._schema_layer
            for signal_name, slot in (
                ('updatedFields', self._on_layer_fields_changed),
                ('dataChanged', self._on_layer_data_changed),
            ):
                try:
                    signal = getattr(old_layer, signal_name, None)
                    if signal is None:
                        continue
                    signal.disconnect(slot)
                except (AttributeError, RuntimeError, TypeError):
                    pass
        self._schema_layer = layer
        if layer is not None:
            for signal_name, slot in (
                ('updatedFields', self._on_layer_fields_changed),
                ('dataChanged', self._on_layer_data_changed),
            ):
                try:
                    signal = getattr(layer, signal_name, None)
                    if signal is None:
                        continue
                    signal.connect(slot)
                except (AttributeError, RuntimeError, TypeError):
                    pass

    def _on_layer_fields_changed(self, *_):
        layer = self._active_layer()
        if not layer:
            return
        _clear_field_index(layer)
        if self._results_layer_id == layer.id():
            self._clear_all()
            self._set_status('La estructura de campos cambio; realiza nuevamente la busqueda.')
        self._update_fields_badge(layer)

    def _on_layer_data_changed(self, *_):
        layer = self._active_layer()
        if layer and self._results_layer_id == layer.id():
            self._clear_all()
            self._set_status('Los datos de la capa cambiaron; repite la busqueda.')

    def _on_layer_changed(self):
        layer = self._active_layer()
        layer_id = layer.id() if layer else None
        if self._results_layer_id is not None and self._results_layer_id != layer_id:
            self._clear_all()
        self._watch_layer_schema(layer)
        if not layer:
            self.lbl_layer_meta.setText('—')
            self.lbl_fields_badge.setText('Sin capa seleccionada.')
            self._update_omissions_button(None)
            return
        _clear_field_index(layer)
        nf = layer.featureCount()
        nc = len(layer.fields())
        gt = QgsWkbTypes.displayString(layer.wkbType())
        cr = layer.crs().authid()
        self.lbl_layer_meta.setText(f'{nf:,} registros · {nc} campos · {gt} · {cr}')
        self._update_fields_badge(layer)
        self._update_omissions_button(layer)

    def _omissions_layer(self, result_layer=None):
        result_layer = result_layer or self._active_layer()
        if result_layer is None:
            return None
        try:
            layer_id = result_layer.customProperty(_OMISSIONS_LAYER_PROPERTY, '')
            return QgsProject.instance().mapLayer(layer_id) if layer_id else None
        except (AttributeError, RuntimeError):
            return None

    def _update_omissions_button(self, result_layer=None):
        if not hasattr(self, 'btn_omissions'):
            return
        omissions = self._omissions_layer(result_layer) if result_layer else None
        count = omissions.featureCount() if omissions is not None else 0
        self.btn_omissions.setText('📋  Omisiones gráficas ({:,})'.format(count))
        self.btn_omissions.setEnabled(omissions is not None and count > 0)
        if omissions is not None:
            self.btn_omissions.setToolTip(
                '{} registro(s) alfanumérico(s) sin geometría.'.format(count))
        else:
            self.btn_omissions.setToolTip(
                'El reporte se habilita después de crear la capa consolidada.')

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

    # ── Consolidar / Merge ────────────────────────────────────────────────────
    def _show_merge_dialog(self):
        from .merge_dialog import MergeConsolidacionDialog
        if getattr(self, '_merge_dlg', None) is not None:
            try:
                self._merge_dlg.close()
            except RuntimeError:
                pass
        self._merge_dlg = MergeConsolidacionDialog(self.iface, self)
        self._merge_dlg.setWindowFlags(Qt.Window)
        self._merge_dlg.show()
        self._merge_dlg.raise_()
        self._merge_dlg.activateWindow()
        return self._merge_dlg

    def _select_created_layer(self, layer):
        if layer is None:
            return
        self._refresh_layers()
        index = self.cbo_layer.findData(layer.id())
        if index >= 0:
            self.cbo_layer.setCurrentIndex(index)
        self._set_status(
            'Capa «{}» creada y lista para consultar.'.format(layer.name()))

    def _open_direct_merge(self):
        self._show_merge_dialog()

    def _open_merge(self):
        self._show_merge_dialog()

    def _export_graphic_omissions(self):
        omissions = self._omissions_layer()
        if omissions is None:
            QMessageBox.information(
                self, 'Omisiones gráficas',
                'Primero crea la capa consolidada para calcular las omisiones.')
            return
        if omissions.featureCount() <= 0:
            QMessageBox.information(
                self, 'Omisiones gráficas',
                'Todos los registros alfanuméricos tienen geometría asociada.')
            return

        path, _ = QFileDialog.getSaveFileName(
            self, 'Guardar reporte de omisiones gráficas',
            'Reporte_Omisiones_Graficas.xlsx', 'Excel (*.xlsx)')
        if not path:
            return
        if not path.lower().endswith('.xlsx'):
            path += '.xlsx'
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter
        except ImportError:
            QMessageBox.critical(
                self, 'openpyxl no instalado',
                'El entorno Python de QGIS necesita openpyxl para crear el reporte.')
            return

        labels = {
            'NUMERO_PREDIAL': 'Número predial',
            'NO_PREDIAL': 'NoPredial',
            'NOMBRE': 'Nombre / propietario',
            'TIPO_DOCUMENTO': 'Tipo documento',
            'NUMERO_DOCUMENTO': 'Número documento',
            'DIRECCION': 'Dirección',
            'PRESENTE_R1': 'Presente en R1',
            'PRESENTE_R2': 'Presente en R2',
            'ORIGEN_REGISTRO': 'Origen alfanumérico',
            'MOTIVO': 'Tipo de omisión',
        }
        fields = [field.name() for field in omissions.fields()]
        try:
            workbook = openpyxl.Workbook()
            sheet = workbook.active
            sheet.title = 'Omisiones gráficas'
            count = omissions.featureCount()
            last_col = get_column_letter(len(fields))

            title_fill = PatternFill('solid', fgColor='C65911')
            header_fill = PatternFill('solid', fgColor='F4B183')
            alt_fill = PatternFill('solid', fgColor='FFF2CC')
            white_bold = Font(name='Arial', size=13, bold=True, color='FFFFFF')
            header_font = Font(name='Arial', size=10, bold=True, color='5B2C06')
            body_font = Font(name='Arial', size=10)
            center = Alignment(horizontal='center', vertical='center')
            left = Alignment(horizontal='left', vertical='center', wrap_text=True)
            border = Border(bottom=Side(style='thin', color='D9D9D9'))

            sheet.merge_cells('A1:{}1'.format(last_col))
            title = sheet['A1']
            title.value = 'REPORTE DE OMISIONES GRÁFICAS'
            title.fill = title_fill
            title.font = white_bold
            title.alignment = center
            sheet.row_dimensions[1].height = 26

            sheet.merge_cells('A2:{}2'.format(last_col))
            subtitle = sheet['A2']
            subtitle.value = (
                'Registros de R1/R2 sin código predial asociado a una geometría | '
                'Total: {:,} | Fecha: {}'.format(
                    count, QDate.currentDate().toString('dd/MM/yyyy')))
            subtitle.fill = title_fill
            subtitle.font = Font(name='Arial', size=9, color='FFFFFF')
            subtitle.alignment = center

            widths = []
            for column, field_name in enumerate(fields, 1):
                label = labels.get(field_name, field_name)
                cell = sheet.cell(3, column, label)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = center
                cell.border = border
                widths.append(len(label))

            for row, feature in enumerate(omissions.getFeatures(), 4):
                for column, field_name in enumerate(fields, 1):
                    value = _excel_safe_text(_value_text(feature[field_name]))
                    cell = sheet.cell(row, column, value)
                    cell.number_format = '@'
                    cell.data_type = 's'
                    cell.font = body_font
                    cell.alignment = left
                    cell.border = border
                    if row % 2 == 0:
                        cell.fill = alt_fill
                    widths[column - 1] = max(widths[column - 1], len(value))

            for column, width in enumerate(widths, 1):
                sheet.column_dimensions[get_column_letter(column)].width = min(
                    max(width + 2, 14), 48)
            sheet.freeze_panes = 'A4'
            sheet.auto_filter.ref = 'A3:{}{}'.format(last_col, count + 3)
            workbook.save(path)
            self._set_status('Reporte de omisiones gráficas exportado: {}'.format(path))
            QMessageBox.information(
                self, 'Reporte generado',
                'Se exportaron {:,} omisiones gráficas.'.format(count))
        except Exception as error:
            QMessageBox.critical(self, 'Error al exportar omisiones', str(error))

    # ── BÚSQUEDA PRINCIPAL ────────────────────────────────────────────────────
    def _run_search(self):
        layer = self._active_layer()
        if not layer:
            QMessageBox.warning(self, 'Sin capa', 'Selecciona una capa vectorial primero.')
            return
        try:
            layer.removeSelection()
        except RuntimeError as error:
            self.iface.messageBar().pushWarning(
                'Herramienta catastral',
                f'No se pudo limpiar la selección anterior: {error}',
            )

        expr_str, not_found = self._active_form.build_expression(layer)

        if not_found:
            missing_text = ', '.join(not_found)
            QMessageBox.warning(
                self,
                'Campos no disponibles',
                f'No se aplicaron estos filtros porque sus campos no existen: '
                f'{missing_text}. Verifica las uniones de la capa.'
            )
            if not expr_str:
                self._set_status('Busqueda cancelada: faltan campos requeridos.')
                return

        if expr_str:
            expr = QgsExpression(expr_str)
            if expr.hasParserError():
                QMessageBox.critical(self, 'Error en expresión',
                    f'{expr.parserErrorString()}\n\nExpresión:\n{expr_str}')
                return

        try:
            features, truncated = self._fetch_features(layer, expr_str)
        except Exception as e:
            QMessageBox.critical(self, 'Error al consultar', str(e))
            return

        n = len(features)
        self.current_features = features
        self._results_layer_id = layer.id()
        self._results_truncated = truncated
        self._feature_index_by_id = {
            feature.id(): index for index, feature in enumerate(features)
        }
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
        if truncated:
            self._set_status(
                f'⚠ Se muestran los primeros {n} registros. Agrega filtros '
                f'para obtener un resultado completo y mas preciso.'
            )
        else:
            self._set_status(
                f'✅  {n} registro(s) en "{layer.name()}"' if n
                else f'⚠  Sin resultados en "{layer.name()}"'
            )
        if features and n <= self.AUTO_ZOOM_MAX_FEATURES:
            self._zoom_to_features(features)
        elif features and not truncated:
            self._set_status(
                f'✅  {n} registros. Zoom automatico omitido para mantener '
                f'la interfaz fluida; usa el boton Zoom cuando lo necesites.'
            )

    def _fetch_features(self, layer, expression=''):
        """Consulta acotada para impedir agotamiento de memoria en la interfaz."""
        request = QgsFeatureRequest()
        if expression:
            request.setFilterExpression(expression)
        # Los resultados usan atributos e identificadores; QGIS obtiene las
        # geometrias al seleccionar o hacer zoom.
        request.setFlags(QgsFeatureRequest.NoGeometry)
        request.setLimit(self.MAX_QUERY_RESULTS + 1)
        features = list(layer.getFeatures(request))
        truncated = len(features) > self.MAX_QUERY_RESULTS
        if truncated:
            features = features[:self.MAX_QUERY_RESULTS]
        return features, truncated

    # ── Columnas excluidas / renombradas ─────────────────────────────────────
    _EXCLUDED = {'usuario_log', 'fecha_log', 'globalid', 'globalid_snc',
                 'usuario_log_', 'fecha_log_'}
    _RENAME   = {
        'shape_area': 'Área (m²)',
        'shape_length': 'Perímetro (m)',
        'manzana_vereda_codigo': 'Código manzana/vereda',
        'tipo_unidad': 'Tipo de unidad',
        'origen': 'Origen',
        'clase': 'Clasificación',
    }
    # Se adelantan justo despues del codigo predial: en la capa consolidada
    # de Predios+Construcciones quedan perdidos entre los campos de los
    # joins R1/R2 si se dejan en su posicion natural del esquema.
    _PRIORITY_AFTER_CODIGO = ('tipo_unidad', 'origen')

    def _visible_fields(self, layer):
        """Devuelve [(field_real, header_label)] filtrando columnas excluidas."""
        result = []
        priority_found = {}
        for fld in layer.fields():
            fn = fld.name()
            fl = fn.lower()
            # excluir si coincide exacto o termina en sufijo de log/globalid
            if fl in self._EXCLUDED:
                continue
            if any(fl.endswith(s) for s in ('_log', 'globalid', 'globalid_snc')):
                continue
            label = self._RENAME.get(fl, fn)
            if fl in self._PRIORITY_AFTER_CODIGO:
                priority_found[fl] = (fn, label)
            else:
                result.append((fn, label))
        if priority_found:
            # Orden fijo (TIPO_UNIDAD antes que ORIGEN), sin importar en que
            # orden hayan quedado en el esquema de la capa.
            priority = [priority_found[fl] for fl in self._PRIORITY_AFTER_CODIGO
                        if fl in priority_found]
            insert_at = next(
                (i + 1 for i, (fn, _label) in enumerate(result)
                 if fn.lower() == 'codigo'),
                0)
            result[insert_at:insert_at] = priority
        return result

    def _fmt_cell(self, fn, val):
        """Formatea valor para celda de tabla."""
        if _is_null_value(val):
            return ''
        fl = fn.lower()
        if fl in ('shape_area', 'shape_length') or fl.endswith('shape_area') or fl.endswith('shape_length'):
            return _fmt_area(val)
        if 'avaluo' in fl or fl.startswith('r_avaluo') or '($)' in fl:
            return _fmt_currency(val)
        return str(val)

    # ── Tabla embebida ────────────────────────────────────────────────────────
    def _populate_table(self, layer, features):
        n = len(features)
        self._nav_index = max(0, min(self._nav_index, n-1)) if n else 0
        vis = self._visible_fields(layer)
        self._vis_fields = vis

        # La tabla interna esta oculta. Antes se llenaba completa y luego se
        # repetia el mismo trabajo en la ventana visible de reporte.
        self.table.blockSignals(True)
        self.table.clear()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        self.table.blockSignals(False)
        if n > 0:
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
            QLineEdit as QLE, QPushButton as QPB,
            QVBoxLayout, QHBoxLayout,
            QFrame, QLabel, QMenu, QAction,
        )
        n = len(features)
        lname = layer.name() if layer else '—'
        limit_note = ' (limite de seguridad)' if self._results_truncated else ''

        # Cada busqueda obtiene una ventana limpia. Esto evita layouts
        # duplicados y elimina la dependencia fragil del modulo ``sip``.
        if self._float_win is not None:
            self._float_win.close()
            self._float_win.deleteLater()
        win = QDialog(None)   # Sin padre para que sea ventana independiente
        win.setWindowIcon(self.windowIcon())
        win.setWindowTitle(f'Reporte Predial — {lname}')
        win.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint |
                           Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        win.resize(1100, 520)
        win.setAttribute(Qt.WA_DeleteOnClose, False)
        self._float_win = win

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

        lbl_title = QLabel(
            f'<b>{n}</b> registro(s){limit_note} — {html.escape(lname)}'
        )
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
        btn_pdf   = QPB('🗺 PDF')
        btn_copy  = QPB('📋 Copiar')
        btn_close = QPB('✕')
        for b in [btn_cols, btn_exp, btn_pdf, btn_copy]:
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
        tb_lo.addWidget(btn_pdf)
        tb_lo.addWidget(btn_copy)
        tb_lo.addWidget(btn_close)
        root.addWidget(toolbar)

        # ── Tabla dinámica ────────────────────────────────────────────────
        tbl = QTableWidget()
        tbl.setSortingEnabled(False)
        tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tbl.setAlternatingRowColors(True)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
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
        tbl.setUpdatesEnabled(False)
        tbl.setColumnCount(len(vis))
        tbl.setHorizontalHeaderLabels(headers)
        tbl.setRowCount(n)
        ALN = Qt.AlignLeft | Qt.AlignVCenter
        YELLOW = QColor('#fffde7')   # amarillo claro para celdas con datos
        for r, feat in enumerate(features):
            for c, (fn, _) in enumerate(vis):
                try:    v = feat[fn]
                except (KeyError, RuntimeError, TypeError, IndexError): v = None
                txt  = self._fmt_cell(fn, v)
                item = QTableWidgetItem(txt)
                item.setTextAlignment(ALN)
                item.setData(Qt.UserRole, feat.id())
                if txt.strip():          # solo si tiene valor
                    item.setBackground(QBrush(YELLOW))
                tbl.setItem(r, c, item)
        # ResizeToContents inspecciona todas las celdas. Para reportes grandes
        # se usan anchos iniciales por encabezado, ajustables por el usuario.
        if n <= 250:
            tbl.resizeColumnsToContents()
        else:
            for c, header in enumerate(headers):
                tbl.setColumnWidth(c, min(max(len(header) * 8 + 24, 100), 240))
        tbl.setSortingEnabled(True)
        tbl.setUpdatesEnabled(True)

        root.addWidget(tbl)

        # ── Barra de estado ───────────────────────────────────────────────
        lbl_status_ft = QLabel(f'{n} registro(s) mostrado(s)')
        lbl_status_ft.setTextFormat(Qt.PlainText)
        lbl_status_ft.setStyleSheet(
            f'font-size:10px;color:#555;background:{C["info_bg"]};'
            f'border:1px solid {C["border"]};border-radius:3px;padding:2px 6px;')
        root.addWidget(lbl_status_ft)

        # ── Lógica: búsqueda en tiempo real ───────────────────────────────
        def _filter_table(text):
            tl = text.lower()
            visible = 0
            tbl.setUpdatesEnabled(False)
            try:
                for r in range(tbl.rowCount()):
                    show = any(
                        tl in (tbl.item(r, c).text() if tbl.item(r, c) else '').lower()
                        for c in range(tbl.columnCount())
                    ) if tl else True
                    tbl.setRowHidden(r, not show)
                    if show:
                        visible += 1
            finally:
                tbl.setUpdatesEnabled(True)
            lbl_status_ft.setText(
                f'{visible} de {n} registro(s)' if tl else f'{n} registro(s)')

        filter_timer = QTimer(win)
        filter_timer.setSingleShot(True)
        filter_timer.setInterval(180)
        filter_timer.timeout.connect(lambda: _filter_table(inp_search.text()))
        inp_search.textChanged.connect(lambda _text: filter_timer.start())

        def _select_report_row():
            selected = tbl.selectedItems()
            if not selected:
                return
            feature_id = selected[0].data(Qt.UserRole)
            index = self._feature_index_by_id.get(feature_id)
            if index is None or index >= len(self.current_features):
                return
            self._show_result(index, select_report_row=False)

        tbl.itemSelectionChanged.connect(_select_report_row)
        self._float_table = tbl

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
            if filter_timer.isActive():
                filter_timer.stop()
                _filter_table(inp_search.text())
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
                if not vis_cols:
                    QMessageBox.information(
                        win, 'Sin columnas',
                        'Activa al menos una columna antes de exportar.'
                    )
                    return
                nc = len(vis_cols)
                ws_x.merge_cells(f'A1:{get_column_letter(nc)}1')
                cell = ws_x['A1']
                cell.value = f'REPORTE PREDIAL — {lname}{limit_note}'
                cell.font=FT; cell.fill=FA; cell.alignment=AC
                ws_x.row_dimensions[1].height = 26
                ws_x.merge_cells(f'A2:{get_column_letter(nc)}2')
                cell = ws_x['A2']
                cell.value = f'Fecha: {fecha}   |   Registros visibles: {sum(1 for r in range(tbl.rowCount()) if not tbl.isRowHidden(r))}'
                cell.font=FS; cell.fill=FAC; cell.alignment=AC
                ws_x.row_dimensions[2].height = 16
                max_widths = [len(str(lbl_r)) for _, _, lbl_r in vis_cols]
                for ci,(_, fn_r, lbl_r) in enumerate(vis_cols, 1):
                    c2 = ws_x.cell(3, ci, _excel_safe_text(lbl_r))
                    c2.font=FH; c2.fill=FA; c2.alignment=AC; c2.border=BD
                ws_x.row_dimensions[3].height = 18
                data_row = 4
                for r in range(tbl.rowCount()):
                    if tbl.isRowHidden(r): continue
                    ws_x.row_dimensions[data_row].height = 17
                    par = (data_row % 2 == 0)
                    for ci,(col_idx, fn_r, _) in enumerate(vis_cols, 1):
                        txt = _excel_safe_text(
                            tbl.item(r, col_idx).text()
                            if tbl.item(r, col_idx) else ''
                        )
                        # Los identificadores catastrales se escriben como texto para
                        # conservar todos sus dígitos y sus ceros iniciales.
                        c2 = ws_x.cell(data_row, ci, txt)
                        c2.number_format = '@'
                        c2.data_type = 's'
                        max_widths[ci - 1] = max(max_widths[ci - 1], len(txt))
                        c2.font=FV; c2.alignment=AL; c2.border=BD
                        if par: c2.fill=FG
                    data_row += 1
                for ci, width in enumerate(max_widths, 1):
                    ws_x.column_dimensions[get_column_letter(ci)].width = min(max(width + 2, 14), 50)
                ws_x.freeze_panes = 'A4'
                ws_x.auto_filter.ref = f'A3:{get_column_letter(nc)}{data_row-1}'
                wb.save(path)
                lbl_status_ft.setText(f'✅ Excel exportado → {path}')
            except Exception as e:
                from qgis.PyQt.QtWidgets import QMessageBox
                QMessageBox.critical(win, 'Error', str(e))

        btn_exp.clicked.connect(_export_ft)
        btn_pdf.clicked.connect(self._export_map_pdf)

        # ── Copiar selección ──────────────────────────────────────────────
        def _copy_selection():
            from qgis.PyQt.QtWidgets import QApplication
            rows_sel = sorted(set(i.row() for i in tbl.selectedItems()))
            if not rows_sel: return
            vis_c = [c for c in range(tbl.columnCount()) if not tbl.isColumnHidden(c)]
            lines = ['	'.join(_excel_safe_text(headers[c]) for c in vis_c)]
            for r in rows_sel:
                lines.append('	'.join(
                    _excel_safe_text(tbl.item(r,c).text() if tbl.item(r,c) else '')
                    for c in vis_c
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
        selected = self.table.selectedItems()
        if not selected or not self.current_features:
            return
        feature_id = selected[0].data(Qt.UserRole)
        index = self._feature_index_by_id.get(feature_id)
        if index is not None:
            self._show_result(index, select_report_row=False)

    def _show_result(self, index, select_report_row=True):
        """Muestra un resultado sin reconstruir las tablas completas."""
        if not (0 <= index < len(self.current_features)):
            return
        layer = self._active_layer()
        if not layer or layer.id() != self._results_layer_id:
            return
        self._nav_index = index
        feature = self.current_features[index]
        self._fill_form(feature, layer)
        n = len(self.current_features)
        self.lbl_count.setText(f'✅ Predio {index+1} de {n}')
        self.btn_nav_prev.setEnabled(index > 0)
        self.btn_nav_next.setEnabled(index < n-1)

        table = getattr(self, '_float_table', None)
        if select_report_row and table is not None:
            feature_id = feature.id()
            for row in range(table.rowCount()):
                item = table.item(row, 0)
                if item and item.data(Qt.UserRole) == feature_id:
                    table.blockSignals(True)
                    table.selectRow(row)
                    table.scrollToItem(item, QAbstractItemView.PositionAtCenter)
                    table.blockSignals(False)
                    break
        self._zoom_to_features([feature])

    def _fill_form(self, feat, layer):
        self._active_form.fill_from_feature(feat, layer)
        if not self.stack.isVisible():
            self.btn_collapse.setChecked(True)
        self.lbl_form_mode.setText('📋 Predio seleccionado')
        np = str(get_value(feat, layer, 'CODIGO') or '').strip()
        self._set_status(f'Predio {self._nav_index+1} de {len(self.current_features)} — {np}')

    def _nav_prev(self):
        if self.current_features and self._nav_index > 0:
            self._show_result(self._nav_index - 1)

    def _nav_next(self):
        if self.current_features and self._nav_index < len(self.current_features)-1:
            self._show_result(self._nav_index + 1)

    # ── Búsqueda rápida ───────────────────────────────────────────────────────
    def _quick_search(self):
        texto = self.inp_quick.text().strip()
        if not texto: return
        layer = self._active_layer()
        if not layer:
            QMessageBox.warning(self, 'Sin capa', 'Selecciona una capa vectorial.')
            return
        safe = texto.replace("'", "''")
        # Si el texto coincide con un NOMBRE de vereda, la búsqueda rápida se
        # resuelve por su CÓDIGO (resultado limpio, como si se hubiera escrito el
        # código de la vereda) y NO se mezcla con direcciones ni propietarios.
        # Se resuelve leyendo la propia capa consultada (independiente de la GDB
        # y siempre al día); si esa capa no trae el nombre, se usa R_VEREDA.
        codigos_vereda = _codigos_vereda_en_capa(layer, texto)
        if not codigos_vereda:
            codigos_vereda = _buscar_codigos_por_nombre(texto)
        real_cod_vereda = resolve_field(layer, 'VEREDA_CODIGO')
        if codigos_vereda and real_cod_vereda:
            fn = '"{}"'.format(real_cod_vereda.replace('"', '""'))
            vals = ', '.join(
                "'{}'".format(str(c).replace("'", "''")) for c in codigos_vereda)
            expr_str = '{} IN ({})'.format(fn, vals)
        else:
            # Búsqueda genérica en los campos catastrales relevantes. En capas
            # sin ninguno de ellos se conserva el comportamiento anterior.
            partes = []
            search_semantics = (
                'CODIGO', 'CODIGO_ANTERIOR', 'Nombre', 'No Documento',
                'Matricula Inmobiliaria', 'Direccion', 'TEXTO', 'VEREDA_CODIGO',
                'NOMBRE_VEREDA',
            )
            field_names = []
            for semantic in search_semantics:
                real = resolve_field(layer, semantic)
                if real and real not in field_names:
                    field_names.append(real)
            fields = layer.fields()
            searchable_fields = [
                fields.field(index)
                for index in (fields.indexFromName(name) for name in field_names)
                if index >= 0
            ]
            if not searchable_fields:
                searchable_fields = [fld for fld in fields
                                     if fld.type() in (STR_T | NUM_T)]
            for fld in searchable_fields:
                fn = '"{}"'.format(fld.name().replace('"', '""'))
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
            QMessageBox.critical(
                self, 'Error en busqueda',
                f'{expr.parserErrorString()}\n\nExpresion:\n{expr_str}'
            )
            return
        try:
            features, truncated = self._fetch_features(layer, expr_str)
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e)); return

        n = len(features)
        self.current_features = features
        self._results_layer_id = layer.id()
        self._results_truncated = truncated
        self._feature_index_by_id = {
            feature.id(): index for index, feature in enumerate(features)
        }
        self._all_field_names = [f.name() for f in layer.fields()]
        self._nav_index       = 0
        self._populate_table(layer, features)
        n = len(features)
        self.lbl_status.setText(f'⚡ Búsqueda rápida "{texto}": {n} resultado(s)')
        self._set_status(
            f'Busqueda rapida: primeros {n} resultados; agrega mas texto.'
            if truncated else f'Busqueda rapida: {n} resultado(s)'
        )
        self._add_to_history(texto)
        if features and n <= self.AUTO_ZOOM_MAX_FEATURES:
            self._zoom_to_features(features)
        elif features and not truncated:
            self._set_status(
                f'Busqueda rapida: {n} resultados. Zoom automatico omitido '
                f'para mantener la interfaz fluida.'
            )

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
        if (layer and layer.id() == self._results_layer_id
                and self.current_features):
            layer.selectByIds([f.id() for f in self.current_features])
            self.iface.setActiveLayer(layer)

    def _zoom_to_selection(self):
        layer = self._active_layer()
        if (layer and layer.id() == self._results_layer_id
                and self.current_features):
            layer.selectByIds([f.id() for f in self.current_features])
            self.iface.setActiveLayer(layer)
            self.iface.actionZoomToSelected().trigger()

    # ── Exportar Excel ────────────────────────────────────────────────────────
    @staticmethod
    def _build_construction_index(layer):
        """
        Indexa, en una sola pasada, las construcciones/unidades de la capa
        consolidada por su CODIGO predial, para no recorrer toda la capa por
        cada predio al exportar varios en un mismo PDF (mismo criterio de
        cacheo que ``_buscar_nombre_vereda``/``_VEREDA_CACHE``). Devuelve
        None si la capa no trae los campos TIPO_UNIDAD/CODIGO (no es la
        consolidada del merge).
        """
        tipo_unidad_field = resolve_field(layer, 'TIPO_UNIDAD')
        codigo_field = resolve_field(layer, 'CODIGO')
        if not (tipo_unidad_field and codigo_field):
            return None
        index = {}
        try:
            for cfeat in layer.getFeatures():
                try:
                    tipo_unidad = _value_text(cfeat[tipo_unidad_field]).strip().upper()
                    codigo_value = cfeat[codigo_field]
                except (KeyError, RuntimeError, TypeError, IndexError):
                    continue
                if tipo_unidad != 'CONSTRUCCION' or _is_null_value(codigo_value):
                    continue
                index.setdefault(str(codigo_value), []).append(cfeat)
        except Exception:
            return None
        return index

    def _pdf_details(self, feat, layer, construction_index=None):
        """Compone los datos base que alimentan la plantilla cartografica.

        El recorte contra capas activas se agrega automaticamente en
        map_pdf_export.export_predial_selection_pdf. ``construction_index``
        (opcional) es el resultado de ``_build_construction_index``, para no
        repetirlo por cada predio; si no se da, se resuelve puntualmente con
        una consulta por expresion sobre ``layer``.
        """
        def raw(semantic):
            return _value_text(get_value(feat, layer, semantic))

        direction = raw('Direccion') or raw('TEXTO')
        vereda_code = raw('VEREDA_CODIGO')
        vereda = raw('NOMBRE_VEREDA') or _buscar_nombre_vereda(vereda_code)
        territorial = ' / '.join(value for value in (
            vereda_code, vereda) if value)

        document_type = raw('Tipo Documento')
        document_number = raw('No Documento')
        document = ' / '.join(value for value in (
            TIPO_DOCUMENTO.get(document_type, document_type), document_number)
                              if value and value != '-- Todos --')

        # Condicion del predio (Formal/Informal) y Zona (Urbano/Rural): mismo
        # campo ORIGEN del merge que ya usa la casilla "Condicion" del panel
        # de detalle. Reemplaza las filas de Zona Fisica/Economica y Estrato
        # (pedido del usuario, 2026-11-09: en vez de esas, identificar si el
        # predio es urbano o rural).
        origin_value = raw('ORIGEN').strip().upper()
        if origin_value.endswith('INFORMAL'):
            condition = 'Informal'
        elif origin_value:
            condition = 'Formal'
        else:
            condition = ''
        if origin_value.startswith('URBANO'):
            zone_type = 'Urbano'
        elif origin_value.startswith('RURAL'):
            zone_type = 'Rural'
        else:
            zone_type = ''

        destination_code = raw('Destino Economico')
        destination = DESTINO_ECONOMICO.get(destination_code, destination_code)
        if destination == '-- Todos --':
            destination = ''

        appraisal = get_value(feat, layer, 'Avaluo Catastral')
        if _is_null_value(appraisal):
            for field in layer.fields():
                normalized = _normalized_field_name(field.name())
                if 'avaluo' not in normalized:
                    continue
                try:
                    candidate = feat[field.name()]
                except (KeyError, RuntimeError, TypeError, IndexError):
                    continue
                if not _is_null_value(candidate):
                    appraisal = candidate
                    break

        area_land = get_value(feat, layer, 'Area Terreno(m2)')
        area_built = get_value(feat, layer, 'Area Construida (m2)')
        if _is_null_value(area_built):
            area_built = get_value(feat, layer, 'Area Construida m2')

        # Area/perimetro geometricos (medidos por QGIS, distintos del area de
        # terreno declarada en R1) y campos de R2 (Estrato, Uso, Pisos, Baños,
        # Locales, Puntaje): mismos datos que ya se ven en el panel de
        # detalle, para que la ficha PDF quede tan completa como la consulta
        # principal (pedido del usuario, 2026-11-06).
        def _ha_km(raw_value, divisor):
            if _is_null_value(raw_value):
                return ''
            try:
                return _fmt_area(float(str(raw_value).replace(',', '.')) / divisor)
            except (TypeError, ValueError):
                return ''

        shape_area = get_value(feat, layer, 'SHAPE_Area')
        shape_length = get_value(feat, layer, 'SHAPE_Length')

        # Construcciones/unidades asociadas al mismo predio (misma CODIGO),
        # cuando la capa activa es la consolidada del merge (trae los campos
        # TIPO_UNIDAD y CODIGO). Pedido del usuario, 2026-10-12: que la
        # salida grafica tambien muestre las construcciones y unidades de
        # construccion asociadas a cada predio consultado.
        construction_rows = []
        tipo_unidad_field = resolve_field(layer, 'TIPO_UNIDAD')
        codigo_field = resolve_field(layer, 'CODIGO')
        if tipo_unidad_field and codigo_field:
            try:
                own_tipo_unidad = _value_text(feat[tipo_unidad_field]).strip().upper()
                codigo_value = feat[codigo_field]
            except (KeyError, RuntimeError, TypeError, IndexError):
                own_tipo_unidad = ''
                codigo_value = None
            if own_tipo_unidad != 'CONSTRUCCION' and not _is_null_value(codigo_value):
                if construction_index is not None:
                    construcciones = [
                        cfeat for cfeat in construction_index.get(str(codigo_value), [])
                        if cfeat.id() != feat.id()
                    ]
                else:
                    safe_codigo = str(codigo_value).replace("'", "''")
                    expr = '"{}" = \'{}\' AND "{}" = \'CONSTRUCCION\''.format(
                        codigo_field.replace('"', '""'), safe_codigo,
                        tipo_unidad_field.replace('"', '""'))
                    request = QgsFeatureRequest().setFilterExpression(expr)
                    try:
                        construcciones = [
                            cfeat for cfeat in layer.getFeatures(request)
                            if cfeat.id() != feat.id()
                        ]
                    except Exception:
                        construcciones = []
                if construcciones:
                    max_listed = 4
                    construction_rows.append((
                        'Construcciones asociadas',
                        '{} unidad(es)'.format(len(construcciones))))
                    for index, cfeat in enumerate(construcciones[:max_listed], start=1):
                        tipo_c = _value_text(get_value(cfeat, layer, 'TIPO_CONSTRUCCION'))
                        identificador = _value_text(get_value(cfeat, layer, 'IDENTIFICADOR'))
                        pisos = _value_text(get_value(cfeat, layer, 'NUMERO_PISOS'))
                        label = 'Unidad {}'.format(identificador or index)
                        parts = [p for p in (
                            tipo_c, (pisos + ' piso(s)') if pisos else '') if p]
                        construction_rows.append(
                            (label, ' - '.join(parts) or 'Sin datos adicionales'))
                    remaining = len(construcciones) - max_listed
                    if remaining > 0:
                        construction_rows.append((
                            'Construcciones adicionales',
                            '+{} mas (no mostradas)'.format(remaining)))

        result = [
            ('Codigo predial', raw('CODIGO')),
            ('Codigo anterior', raw('CODIGO_ANTERIOR')),
            ('Matricula inmobiliaria', raw('Matricula Inmobiliaria')),
            ('Propietario', raw('Nombre')),
            ('Tipo y numero de documento', document),
            ('Direccion', direction),
            ('Manzana o vereda', territorial),
            ('Zona', zone_type),
            ('Condicion del predio', condition),
            ('Destino economico', destination),
            ('Avaluo catastral', _fmt_currency(appraisal)),
            ('Area de terreno', (_fmt_area(area_land) + ' m2') if not _is_null_value(area_land) else ''),
            ('Area construida', (_fmt_area(area_built) + ' m2') if not _is_null_value(area_built) else ''),
            ('Area geografica', (_fmt_area(shape_area) + ' m2') if not _is_null_value(shape_area) else ''),
            ('Area geografica (ha)', _ha_km(shape_area, 10000)),
            ('Perimetro', (_fmt_area(shape_length) + ' m') if not _is_null_value(shape_length) else ''),
            ('Perimetro (km)', _ha_km(shape_length, 1000)),
            ('Vigencia', raw('Vigencia')),
            ('Uso', raw('Uso')),
            ('Pisos', raw('Pisos')),
            ('Baños', raw('Baños')),
            ('Locales', raw('Locales')),
            ('Puntaje', raw('Puntaje')),
        ]
        result.extend(construction_rows)
        return result

    def _pdf_selected_features(self, layer):
        """Predios seleccionados; si no hay seleccion usa el predio navegado."""
        try:
            selected_ids = list(layer.selectedFeatureIds())
        except (AttributeError, RuntimeError):
            selected_ids = []

        if selected_ids:
            selected_set = set(selected_ids)
            features = [
                feature for feature in self.current_features
                if feature.id() in selected_set
            ]
            included = {feature.id() for feature in features}
            for feature_id in selected_ids:
                if feature_id in included:
                    continue
                feature = layer.getFeature(feature_id)
                if feature is not None and feature.isValid():
                    features.append(feature)
            return features

        if (self.current_features
                and 0 <= self._nav_index < len(self.current_features)):
            return [self.current_features[self._nav_index]]
        return []

    def _export_map_pdf(self, checked=False, query=False):
        """Exporta una pagina carta por cada predio seleccionado."""
        layer = self._active_layer()
        if not layer:
            QMessageBox.warning(
                self, 'Sin capa',
                'Selecciona primero la capa consolidada que deseas consultar.')
            return
        if self.current_features and getattr(self, '_results_layer_id', None) != layer.id():
            QMessageBox.warning(self, 'Consulta desactualizada', 'Ejecuta nuevamente el buscador sobre la capa activa.')
            return
        if query and getattr(self, '_results_truncated', False):
            QMessageBox.warning(self, 'Consulta incompleta', 'Refina la busqueda antes de exportar: los resultados estan limitados.')
            return
        features = list(self.current_features) if query else self._pdf_selected_features(layer)
        if not features:
            QMessageBox.information(
                self, 'Sin predios seleccionados',
                'Realiza una consulta o selecciona uno o varios predios en el mapa.')
            return
        if len(features) > self.MAX_PDF_FEATURES:
            QMessageBox.warning(
                self, 'Seleccion demasiado grande',
                'La salida admite hasta {} predios por PDF. '
                'Reduce la seleccion y vuelve a intentarlo.'.format(
                    self.MAX_PDF_FEATURES))
            return

        from .map_pdf_export import safe_pdf_filename, selection_pdf_filename
        if len(features) == 1:
            code = _value_text(get_value(features[0], layer, 'CODIGO'))
            suggested = safe_pdf_filename(code)
        else:
            suggested = selection_pdf_filename(len(features))
        if query:
            suggested = 'Consulta_Vereda_{}.pdf'.format(len(features))
        path, _ = QFileDialog.getSaveFileName(
            self, 'Guardar salida grafica en PDF', suggested,
            'Documento PDF (*.pdf)')
        if not path:
            return
        if not path.lower().endswith('.pdf'):
            path += '.pdf'
        try:
            from .map_pdf_export import export_predial_selection_pdf

            construction_index = self._build_construction_index(layer)
            records = [
                (feature.id(), self._pdf_details(feature, layer, construction_index))
                for feature in features
            ]

            result = export_predial_selection_pdf(
                self.iface, layer, records, path, overview=query)
            QMessageBox.information(
                self, 'PDF generado',
                'Salida grafica exportada correctamente:\n{}\n\n{} pagina(s), '
                'con grilla geografica e informacion de la consulta.'.format(
                    result['path'], result['page_count']))
            self._set_status(
                'PDF exportado: {} elemento(s)'.format(len(features)))
        except Exception as error:
            QMessageBox.critical(self, 'Error al generar PDF', str(error))

    def _export_excel(self):
        if not self.current_features:
            QMessageBox.information(self, 'Sin datos', 'Realiza primero una búsqueda.'); return
        layer = self._active_layer()
        if not layer or layer.id() != self._results_layer_id:
            QMessageBox.warning(
                self, 'Resultados desactualizados',
                'La capa activa cambio. Realiza nuevamente la busqueda.'
            )
            return
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
            fecha = QDate.currentDate().toString('dd/MM/yyyy')
            vis   = getattr(self, '_vis_fields', [(f.name(), f.name()) for f in (layer.fields() if layer else [])])
            cols  = [fn for fn, _ in vis]
            col_labels = [lbl for _, lbl in vis]
            ncols = len(cols)
            if not ncols:
                QMessageBox.information(
                    self, 'Sin columnas',
                    'La capa activa no contiene columnas exportables.'
                )
                return
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
            c=ws['A1']; c.value='CONSULTAS CATASTRALES — LADM-COL'; c.font=FT; c.fill=FA; c.alignment=AC; ws.row_dimensions[1].height=28
            ws.merge_cells(f'A2:{get_column_letter(ncols)}2')
            limit_note = '   |   RESULTADO LIMITADO' if self._results_truncated else ''
            c=ws['A2']; c.value=f'Capa: {layer.name() if layer else "—"}   |   {fecha}   |   {len(self.current_features):,} registros{limit_note}'; c.font=FS; c.fill=FAC; c.alignment=AC; ws.row_dimensions[2].height=18
            for ci,(h_real, h_lbl) in enumerate(zip(cols, col_labels),1):
                c=ws.cell(3,ci,_excel_safe_text(h_lbl)); c.font=FH; c.fill=FA; c.alignment=AC; c.border=BD
            ws.row_dimensions[3].height=20
            max_widths = [len(str(label)) for label in col_labels]
            for ri,feat in enumerate(self.current_features,4):
                ws.row_dimensions[ri].height=18; par=(ri%2==0)
                for ci,fn in enumerate(cols,1):
                    try: v=feat[fn]
                    except (KeyError, RuntimeError, TypeError, IndexError): v=None
                    raw=_excel_safe_text(self._fmt_cell(fn, v))
                    # Evitar que Excel redondee códigos largos, use notación
                    # científica o elimine ceros iniciales.
                    c=ws.cell(ri,ci,raw); c.number_format='@'; c.data_type='s'
                    max_widths[ci - 1] = max(max_widths[ci - 1], len(raw))
                    c.font=FV; c.alignment=AL; c.border=BD
                    if par: c.fill=FG
            for ci,width in enumerate(max_widths,1):
                ws.column_dimensions[get_column_letter(ci)].width=min(max(width+2,14),50)
            ws.freeze_panes='A4'
            ws.auto_filter.ref=f'A3:{get_column_letter(ncols)}{3+len(self.current_features)}'
            wb.save(path)
            QMessageBox.information(self,'Excel exportado',f'✅ {len(self.current_features):,} registros → {path}')
            self._set_status(f'Excel exportado: {len(self.current_features)} registros')
        except Exception as e:
            QMessageBox.critical(self,'Error Excel',str(e))

    def _clear_all(self):
        if self._results_layer_id is not None:
            result_layer = QgsProject.instance().mapLayer(self._results_layer_id)
            if result_layer is not None:
                try:
                    result_layer.removeSelection()
                except RuntimeError:
                    pass
        if self._active_form: self._active_form.clear()
        self.table.setRowCount(0); self.table.setColumnCount(0)
        self.current_features=[]; self._feature_index_by_id={}; self._nav_index=0
        self._results_layer_id = None
        self._results_truncated = False
        self._vis_fields = []
        if self._float_win is not None:
            self._float_win.hide()
        self._float_table = None
        self.lbl_count.setText('Sin resultados')
        self.lbl_count.setStyleSheet(f'font-weight:bold;font-size:11px;color:{C["primary"]};background:transparent;')
        self.btn_nav_prev.setEnabled(False); self.btn_nav_next.setEnabled(False)
        self.lbl_form_mode.setText(''); self.inp_quick.clear()
        self.lbl_expr.setVisible(False); self.lbl_warn.setVisible(False)
        self._set_status('Formulario limpiado.')
