"""
consultas_dialog.py  –  V3.0
Plugin Consultas Prediales IGAC – Colombia

NUEVO EN V3:
  • CONSULTAS REGISTRO 1 + REGISTRO 2: busca simultáneamente en capas de terreno
    (R1) y construcción (R2) usando el NoPredial como llave de cruce.
  • SELECCIÓN POR AÑO Y ZONA: filtro rápido para capas IGAC 2024-2026, urbano/rural.
  • DETECCIÓN AUTOMÁTICA DE PAREJAS: al seleccionar una capa de terreno, encuentra
    automáticamente su correspondiente capa de construcción (mismo año y zona).
  • TABLA R2 DEDICADA: muestra todas las construcciones del predio seleccionado.
  • NAVEGACIÓN R1+R2: al navegar entre predios, también se actualizan las
    construcciones asociadas.
  • EXPORTACIÓN COMBINADA: exporta R1 y R2 juntos en el mismo Excel.
  • BÚSQUEDA EXPANDIDA: busca por código, matrícula, nombre, documento, vereda.
  • EXPANSIÓN POR PROPIETARIO: al buscar por NoDocumento, encuentra todos los
    predios del mismo propietario automáticamente.
  • CAPAS UNIFICADAS R1+R2: detecta capas que ya tienen datos de terreno y
    construcción combinados.
"""

from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox,
    QAbstractItemView, QScrollArea, QFrame, QSizePolicy,
    QMessageBox, QStackedWidget, QFileDialog, QShortcut,
    QListWidget, QListWidgetItem, QDialog, QDialogButtonBox,
    QSplitter, QTabWidget,
)
import os, re, unicodedata

from qgis.PyQt.QtCore import Qt, QVariant, QSettings, QSize, QPoint, QDate
from qgis.PyQt.QtGui import QKeySequence, QPixmap
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFeatureRequest,
    QgsExpression, QgsWkbTypes
)

from .igac_dominios import (
    DESTINO_ECONOMICO, detect_layer_type, classify_layer_name,
    YEARS, ZONE_NAMES,
)

# ── Paleta ────────────────────────────────────────────────────────────────────
def _plain(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[^a-z0-9]', '', s.lower())

EXCLUDED_FIELDS = {'usuariolog', 'fechalog', 'globalid', 'globalsnc',
                   'usuario_log', 'fecha_log', 'global_id', 'global_snc',
                   'globalidsnc',
                   'gdb_geomattr_data', 'sde_state_id', 'objectid', 'objectid_1',
                   'fid', 'shape_le',
                   'st_length', 'st_perimeter', 'st_area'}

RENAME_FIELDS = {
    'shape_length': 'Perimetro (m)',
    'shape_leng':   'Perimetro (m)',
    'shapelength':  'Perimetro (m)',
    'shapeleng':    'Perimetro (m)',
    'shape_area':   'Area (m\u00b2)',
    'shapearea':    'Area (m\u00b2)',
}

def _filter_fields(names):
    result = []
    for name in names:
        n = name
        n_lower = n.lower()
        for pfx in ('r1_', 'r2_', 'u_', 'r_'):
            if n_lower.startswith(pfx):
                n = n[len(pfx):]
                break
        if _plain(n) not in EXCLUDED_FIELDS:
            result.append(name)
    return result

def _fmt_area(val):
    try:
        num = float(val)
        txt = ('{:.4f}'.format(num)).rstrip('0').rstrip('.')
        return txt.replace('.', ',')
    except (ValueError, TypeError):
        return str(val) if val is not None else ''

def _fmt_table_val(fname, val):
    raw = str(val) if val is not None else ''
    n = fname.lower()
    for pfx in ('r1_', 'r2_', 'u_', 'r_'):
        if n.startswith(pfx):
            n = n[len(pfx):]
            break
    bare = _plain(n)
    if ('area' in bare or 'perim' in bare or 'superficie' in bare
            or bare in ('shape_leng', 'shapelength', 'shape_length')):
        return _fmt_area(raw)
    return raw

C = {
    'primary':   '#1a4b8c',
    'secondary': '#2e86de',
    'bg':        '#f0f3f7',
    'white':     '#ffffff',
    'border':    '#cdd4dc',
    'text':      '#2c3e50',
    'header':    '#dde3ea',
    'alt':       '#f8f9fa',
    'hover':     '#d5e8f9',
    'success':   '#27ae60',
    'error':     '#c0392b',
    'warn':      '#e67e22',
    'warn_bg':   '#fff8e1',
    'info_bg':   '#e3f2fd',
    'tag_blue':  '#e3f2fd',
    'spatial':   '#6c3483',
    'spatial_bg':'#f5eef8',
    'r2':        '#8e44ad',
    'r2_bg':     '#f5eef8',
}

INT_TYPES   = {QVariant.Int, QVariant.LongLong, QVariant.UInt, QVariant.ULongLong}
FLOAT_TYPES = {QVariant.Double}
STR_TYPES   = {QVariant.String}
NUM_TYPES   = INT_TYPES | FLOAT_TYPES

# ═════════════════════════════════════════════════════════════════════════════
#  MOTOR DE BÚSQUEDA DE CAMPOS ROBUSTO
# ═════════════════════════════════════════════════════════════════════════════

_FIELD_ALIASES = {
    # ── Identificación predial ────────────────────────────────────────────────
    'nopredial': [
        'no_predial', 'nopredial', 'cod_predial', 'codigo_predial',
        'codigopred', 'num_predia', 'npredial', 'predialnum',
        'nupre', 'NUPRE', 'predial', 'codigo',
    ],
    'numeropredial': [
        'numeropred', 'num_predial', 'numpredial', 'numero_pre',
        'nuevopredial', 'npredialnu', 'predial30',
        'nopredialnu', 'nopredial_n', 'codigo',
        'Numero_Pre', 'NUMERO_PRE',
    ],
    'nopredialanterior': [
        'noprediant', 'no_pred_an', 'predialant', 'predial_an',
        'npredant', 'anterior',
        'codigo_anterior', 'cod_anterior', 'codigoanterior',
    ],
    'codigovereda': [
        'codigovered', 'codigo_vere', 'cod_vereda',
        'vereda_codigo', 'vereda_cod', 'veredacod',
        'codvereda',
    ],
    'vereda': [
        'vereda', 'nombre_vereda', 'nom_vereda', 'nomvereda',
        'vereda_nombre', 'veredanombre', 'nombre', 'name',
        'denominacion', 'nomb', 'nombres',
    ],
    'codigobarrio': [
        'codigobarrio', 'cod_barrio', 'codbarrio', 'barrio_cod',
    ],
    'barrio': [
        'barrio', 'nombre_barrio', 'nom_barrio', 'nombarrio',
        'barrio_nombre', 'barrionombre', 'sector_urbano', 'localidad',
    ],
    'numerosubterraneos': [
        'numerosubte', 'num_subter', 'subterraneo',
        'numero_subterraneos', 'numero_sub',
        'subter', 'nsubterran',
    ],
    # ── Propietario ───────────────────────────────────────────────────────────
    'nodocumento': [
        'nodocument', 'no_documen', 'nodocumen',
        'no_doc', 'num_doc', 'ndoc', 'nro_doc', 'nodoc',
        'documento', 'n_documento', 'numero_doc', 'numdocumen',
        'numero_documento', 'identificacion', 'cedula', 'nit',
        'num_identif', 'numidentif',
    ],
    'tipodocumento': [
        'tipodocume', 'tipo_docum', 'tip_doc', 'tipodoc',
        'tipo_doc', 'tdocumento',
    ],
    'nombre': [
        'nombre', 'nom', 'names', 'nom_propiet',
        'nombreprop', 'nom_prop', 'propietari',
    ],
    'estadocivil': [
        'estadocivi', 'estado_civ', 'est_civil', 'civilstate', 'ecivil',
    ],
    'tipoderecho': [
        'tipoderech', 'tipo_derec', 'tip_derech', 'tderecho',
    ],
    'tiporegistro': [
        'tiporegist', 'tipo_regis', 'tip_regist', 'tregistro', 'tipo_reg',
    ],
    'matriculainmobiliaria': [
        'matriculai', 'matricula_', 'matriculain',
        'matricula', 'mat_inm', 'mat_inmob', 'matric',
        'matr_inmob', 'mat', 'inm', 'inmobiliaria',
        'nromatricula', 'num_matricula', 'numeromatricula',
        'matinmobiliaria', 'mat_inmobiliaria',
    ],
    # ── Características ───────────────────────────────────────────────────────
    'destinoeconomico': [
        'destinoecon', 'destinoec', 'destino_ec',
        'dest_econ', 'destecon', 'destino',
        'destino_economico', 'des_econom', 'deseconomi', 'uso_suelo',
    ],
    'condicionpredio': [
        'condicionpr', 'condicion_', 'condpred',
        'cond_predi', 'condicion', 'tipo_predi',
        'tipo_predio', 'condpredio',
    ],
    'direccion': [
        'direccion', 'direc', 'dir', 'address',
        'dire', 'direcc', 'direcci',
        'dirpredio', 'direccionpredio', 'direccion_inmueble',
        'dir_inmueble', 'direccion_inm',
    ],
    'zonafisica': [
        'zonafisica', 'zona_fisic', 'zona_f', 'zf',
    ],
    'zonaeconomica': [
        'zonaeconom', 'zona_econ', 'zona_e', 'ze',
    ],
    'departamento': [
        'departamen', 'depto', 'dep', 'dept', 'cod_depart', 'depart',
    ],
    'municipio': [
        'municipio', 'munic', 'mun', 'cod_munic', 'codmunic', 'cod_mpio', 'mpio',
    ],
    'comuna': [
        'comuna', 'com', 'corregimie', 'corregimien', 'cod_comuni', 'barrio',
    ],
    # ── Áreas ─────────────────────────────────────────────────────────────────
    'areaterreno': [
        'areaterren', 'area_terre', 'area_terr',
        'are_terren', 'areaterr', 'area_t',
        'aterren', 'area_digitad', 'areadigita', 'terr_area',
    ],
    'areaperimetral': [
        'areaperimet', 'area_perim', 'perimetro',
        'shape_length', 'shape_leng',
        'shapelength', 'shape_len', 'st_perimeter',
        'perimeter', 'perim',
    ],
    'areageografica': [
        'areageograf', 'area_geogr', 'area_geo',
        'shape_area', 'shapearea',
        'st_area', 'geoarea', 'area_geografica',
        'area_geo_ha',
    ],
    'areaconstruida': [
        'areaconstru', 'area_const', 'area_constr',
        'arecons', 'a_construi', 'areaconstrui',
    ],
    'avaluocatastral': [
        'avaluocata', 'avaluo_cat', 'avaluo', 'avl_catast',
        'avaluo_c', 'avcatast', 'avaluo_catastral',
        'aval_catastral', 'avaluocatastr', 'av_catastral',
        'r1avaluo', 'r1_avaluo', 'r1avaluocatastral',
    ],
    # ── Temporalidad ──────────────────────────────────────────────────────────
    'vigencia': [
        'vigencia', 'vig', 'anio', 'año', 'periodo', 'year',
    ],
    # ── Construcción (R2) ─────────────────────────────────────────────────────
    'estrato': ['estrato', 'estr', 'est', 'nivel'],
    'uso':     ['uso', 'usoconstruc', 'usoconstruccion', 'uso_constr', 'tipouso', 'tipo_uso'],
    'pisos':   ['pisos', 'num_pisos', 'npisos', 'piso', 'nropisos', 'nropiso', 'numeropisos', 'cantpisos', 'cant_pisos'],
    'puntaje': ['puntaje', 'punt', 'score'],
    'habitaciones': ['habitacion', 'habitac', 'hab', 'cuartos', 'num_hab', 'nro_hab', 'nrohabitaciones', 'cant_hab', 'canthabitaciones', 'numerohabitaciones'],
    'banos':   ['banos', 'baños', 'bano', 'baño', 'num_banos', 'nro_banos', 'nrobano', 'nrobanos', 'cant_banos', 'cantbanos', 'numerobanos'],
    'locales': ['locales', 'local', 'num_locales'],
    'codigounidad': [
        'codigounid', 'cod_unidad', 'unidad_cod', 'unidad',
        'numero_unidad', 'num_unidad', 'nrounidad',
    ],
    'anoconstruccion': [
        'anoconstru', 'ano_constru', 'anno_construccion', 'añoconstruc',
        'year_const', 'anoconst', 'fecha_construccion',
        'anoconstruc', 'ano_const', 'construccion_ano',
    ],
    'tipoconstruccion': [
        'tipoconstru', 'tipo_const', 'tipo_constru', 'tconstruccion',
        'tipo_edificacion', 'tip_edific',
    ],
    'areaprivada': [
        'areaprivad', 'area_privad', 'area_priv', 'areapriv',
        'superficie_privada',
    ],
    'areacomun': [
        'areacomun', 'area_comun', 'area_com',
        'superficie_comun',
    ],
    'pisoubicacion': [
        'pisoubicac', 'piso_ubica', 'piso_ubic', 'piso_nivel',
        'nivel_piso',
    ],
}


def find_field(layer, canonical_name: str):
    cn = _plain(canonical_name)
    fields_map_plain = {_plain(f.name()): f.name() for f in layer.fields()}

    if cn in fields_map_plain:
        return fields_map_plain[cn]

    for fname_plain, fname_real in fields_map_plain.items():
        if len(fname_plain) >= 6:
            if cn.startswith(fname_plain) and abs(len(cn) - len(fname_plain)) <= 4:
                return fname_real

    for fname_plain, fname_real in fields_map_plain.items():
        if len(cn) >= 6:
            if fname_plain.startswith(cn) and abs(len(cn) - len(fname_plain)) <= 4:
                return fname_real

    aliases = _FIELD_ALIASES.get(cn, [])
    for alias in aliases:
        alias_plain = _plain(alias)
        if alias_plain in fields_map_plain:
            return fields_map_plain[alias_plain]

    for fname_plain, fname_real in fields_map_plain.items():
        if len(cn) >= 3 and len(fname_plain) >= 3:
            if cn in fname_plain or fname_plain in cn:
                return fname_real
        elif len(cn) >= 2 and len(fname_plain) >= 2:
            if cn == fname_plain:
                return fname_real

    for prefix in ['r1', 'r2', 'u', 'r']:
        p = prefix + '_'
        for fname_plain, fname_real in fields_map_plain.items():
            if fname_plain.startswith(p):
                stripped = fname_plain[len(p):]
                if stripped == cn or (len(cn) >= 3 and len(stripped) >= 3 and (cn in stripped or stripped in cn)):
                    return fname_real

    return None


def build_clause(field_name: str, value: str, layer,
                 partial: bool = True, exact: bool = False) -> str:
    fld_type = None
    for fld in layer.fields():
        if fld.name() == field_name:
            fld_type = fld.type()
            break

    safe_val = value.strip().replace("'", "''")
    fn = f'"{field_name}"'

    if exact:
        if fld_type in NUM_TYPES:
            try:
                num = int(value.strip())
                return f'{fn} = {num}'
            except ValueError:
                try:
                    num = float(value.strip())
                    return f'{fn} = {num}'
                except ValueError:
                    pass
        return f'{fn} = \'{safe_val}\''

    if fld_type in NUM_TYPES:
        return f'to_string({fn}) ILIKE \'%{safe_val}%\''
    else:
        return f'{fn} ILIKE \'%{safe_val}%\''

# ═════════════════════════════════════════════════════════════════════════════
#  HELPERS DE ESTILO
# ═════════════════════════════════════════════════════════════════════════════

def _btn(text, primary=True, color=None, small=False):
    b = QPushButton(text)
    pad   = '2px 7px' if small else '4px 10px'
    fsize = '10px'    if small else '11px'
    if color:
        b.setStyleSheet(f"""
            QPushButton {{
                background:{color}; color:white; border:none;
                border-radius:4px; padding:{pad}; font-weight:bold; font-size:{fsize};
            }}
            QPushButton:hover   {{ background:{color}cc; }}
            QPushButton:pressed {{ background:{color}99; }}
            QPushButton:disabled {{ background:#95a5a6; color:#ddd; }}
        """)
    elif primary:
        b.setStyleSheet(f"""
            QPushButton {{
                background:{C['primary']}; color:white; border:none;
                border-radius:4px; padding:{pad}; font-weight:bold; font-size:{fsize};
            }}
            QPushButton:hover   {{ background:{C['secondary']}; }}
            QPushButton:pressed {{ background:#123a70; }}
            QPushButton:disabled {{ background:#95a5a6; }}
        """)
    else:
        b.setStyleSheet(f"""
            QPushButton {{
                background:{C['white']}; color:{C['primary']};
                border:2px solid {C['primary']}; border-radius:4px;
                padding:{pad}; font-weight:bold; font-size:{fsize};
            }}
            QPushButton:hover   {{ background:{C['hover']}; }}
            QPushButton:pressed {{ background:{C['border']}; }}
        """)
    return b


def _inp(ph='', fixed_w=None):
    w = QLineEdit()
    w.setPlaceholderText(ph)
    w.setStyleSheet(f"""
        QLineEdit {{
            border:1px solid {C['border']}; border-radius:3px;
            padding:2px 5px; background:{C['white']};
            font-size:11px; color:{C['text']}; min-height:18px;
        }}
        QLineEdit:focus {{ border:2px solid {C['secondary']}; }}
    """)
    if fixed_w:
        w.setFixedWidth(fixed_w)
    return w


def _cbo(items_dict=None):
    w = QComboBox()
    w.setStyleSheet(f"""
        QComboBox {{
            border:1px solid {C['border']}; border-radius:3px;
            padding:2px 5px; background:{C['white']};
            font-size:11px; color:{C['text']}; min-height:18px;
        }}
        QComboBox:focus {{ border:2px solid {C['secondary']}; }}
        QComboBox::drop-down {{ border:none; width:18px; }}
        QComboBox QAbstractItemView {{ font-size:11px; }}
    """)
    if items_dict:
        for k, v in items_dict.items():
            w.addItem(v, k)
    return w


def _group(title):
    g = QGroupBox(title)
    g.setStyleSheet(f"""
        QGroupBox {{
            font-weight:bold; font-size:12px; color:{C['primary']};
            border:1px solid {C['border']}; border-radius:6px;
            margin-top:8px; padding-top:6px; background:{C['white']};
        }}
        QGroupBox::title {{ subcontrol-origin:margin; left:10px; padding:0 4px; }}
    """)
    return g


def _section(text):
    w = QLabel(f'\u25b8  {text}')
    w.setStyleSheet(
        f'font-size:10px; font-weight:bold; color:{C["primary"]};'
        f'padding:2px 0; border-bottom:1px solid {C["border"]}; margin-top:2px;'
    )
    return w

# ═════════════════════════════════════════════════════════════════════════════
#  FORMULARIO TERRENO / PROPIETARIO (R1)
# ═════════════════════════════════════════════════════════════════════════════

class FormTerreno(QWidget):
    LABEL = 'Terreno / Predio'

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f'background:{C["white"]};')
        g = QGridLayout(self)
        g.setContentsMargins(6, 4, 6, 4)
        g.setHorizontalSpacing(5)
        g.setVerticalSpacing(2)
        row = 0
        self.f = {}

        def lbl(text):
            l = QLabel(text)
            l.setStyleSheet(
                f'font-size:9px; font-weight:bold; color:{C["text"]};'
            )
            return l

        def add(label, widget, r, col=0):
            g.addWidget(lbl(label), r, col * 2)
            g.addWidget(widget,     r, col * 2 + 1)

        # Identificacion
        g.addWidget(_section('Identificacion predial'), row, 0, 1, 4); row += 1

        self.f['NumeroPredial']    = _inp('No. Predial (30 digitos)')
        self.f['NoPredialAnterior']= _inp('Codigo anterior del predio')
        add('No. Predial:',       self.f['NumeroPredial'],     row, 0)
        add('Codigo anterior:',   self.f['NoPredialAnterior'], row, 1)
        row += 1

        self.f['MatriculaInmobiliaria'] = _inp('Matricula inmobiliaria')
        self.f['CodigoVereda']         = _inp('Codigo de vereda')
        add('Matricula Inmobiliaria:', self.f['MatriculaInmobiliaria'], row, 0)
        add('Codigo Vereda:',         self.f['CodigoVereda'],          row, 1)
        row += 1

        self.f['Vereda']     = _inp('Vereda o Barrio')
        self.f['Direccion']  = _inp('Direccion del predio')
        add('Vereda / Barrio:', self.f['Vereda'], row, 0)
        add('Direccion:',       self.f['Direccion'], row, 1)
        row += 1

        # Caracteristicas
        g.addWidget(_section('Caracteristicas'), row, 0, 1, 4); row += 1

        self.f['ZonaFisica']      = _inp('Codigo zona fisica')
        self.f['ZonaEconomica']   = _inp('Codigo zona economica')
        add('Zona Fisica:',       self.f['ZonaFisica'],    row, 0)
        add('Zona Economica:',    self.f['ZonaEconomica'], row, 1)
        row += 1

        self.f['DestinoEconomico']= _cbo(DESTINO_ECONOMICO)
        self.f['NumeroSubterraneos'] = _inp('Cantidad')
        add('Destino economico:', self.f['DestinoEconomico'], row, 0)
        add('Subterraneos:',      self.f['NumeroSubterraneos'], row, 1)
        row += 1

        # Areas y Avaluo
        g.addWidget(_section('Areas y Avaluo'), row, 0, 1, 4); row += 1

        self.f['AreaTerreno']   = _inp('m' + chr(178))
        self.f['AreaConstruida']= _inp('m' + chr(178))
        add('Area de Terreno (m' + chr(178) + '):',   self.f['AreaTerreno'],    row, 0)
        add('Area Construida (m' + chr(178) + '):',self.f['AreaConstruida'], row, 1)
        row += 1

        self.f['AreaGeografica']= _inp('m' + chr(178))
        self.f['AreaPerimetral']= _inp('m')
        add('Area Grafica (m' + chr(178) + '):', self.f['AreaGeografica'], row, 0)
        add('Perimetro (m):',     self.f['AreaPerimetral'], row, 1)
        row += 1

        self.f['AvaluoCatastral']= _inp('Valor en pesos')
        self.f['Vigencia']       = _inp('Ano de vigencia')
        add('Avaluo Catastral:', self.f['AvaluoCatastral'], row, 0)
        add('Vigencia:',         self.f['Vigencia'],        row, 1)
        row += 1

        # Propietario
        g.addWidget(_section('Propietario / Titular'), row, 0, 1, 4); row += 1

        self.f['Nombre']       = _inp('Nombre del propietario')
        self.f['TipoDocumento']= _inp('CC / NIT / Otro')
        add('Nombre:',          self.f['Nombre'],        row, 0)
        add('Tipo Doc.:',      self.f['TipoDocumento'], row, 1)
        row += 1

        self.f['NoDocumento']          = _inp('Numero de identificacion')
        add('No. Documento:',          self.f['NoDocumento'],           row, 0)
        row += 1

        # Construccion
        g.addWidget(_section('Construccion (R2)'), row, 0, 1, 4); row += 1

        self.f['Estrato']= _inp('1 al 6')
        self.f['Uso']    = _inp('Uso de la construccion')
        add('Estrato:', self.f['Estrato'], row, 0)
        add('Uso:',     self.f['Uso'],     row, 1)
        row += 1

        self.f['Pisos']  = _inp('Cantidad de pisos')
        self.f['Banos']  = _inp('Cantidad de banos')
        add('Pisos:', self.f['Pisos'], row, 0)
        add('Banos:', self.f['Banos'], row, 1)
        row += 1

        self.f['Locales']= _inp('Cantidad de locales')
        self.f['Puntaje']= _inp('Puntaje de construccion')
        add('Locales:', self.f['Locales'], row, 0)
        add('Puntaje:', self.f['Puntaje'], row, 1)
        row += 1

        self.f['Habitaciones']= _inp('Cantidad habitaciones')
        add('Habitaciones:', self.f['Habitaciones'], row, 0)

        g.setColumnStretch(1, 1)
        g.setColumnStretch(3, 1)

    def get_inputs(self):
        result = {}
        text_keys = [
            'NumeroPredial', 'NoPredialAnterior', 'Vereda', 'CodigoVereda',
            'NumeroSubterraneos', 'Direccion', 'ZonaFisica', 'ZonaEconomica',
            'AreaTerreno', 'AreaPerimetral', 'AreaGeografica', 'AreaConstruida',
            'AvaluoCatastral', 'Vigencia', 'MatriculaInmobiliaria',
            'Nombre', 'TipoDocumento', 'NoDocumento',
            'Estrato', 'Uso', 'Pisos', 'Banos', 'Locales', 'Puntaje',
            'Habitaciones',
        ]
        for k in text_keys:
            if self.f.get(k) and self.f[k].text().strip():
                result[k] = self.f[k].text().strip()
        combo_keys = ['DestinoEconomico']
        for k in combo_keys:
            if self.f.get(k) and self.f[k].currentData():
                result[k] = self.f[k].currentData()
        return result

    def get_searched_fields(self):
        return list(self.get_inputs().keys())

    def build_expression(self, layer) -> tuple:
        inputs  = self.get_inputs()
        clauses = []
        warnings= []
        for canonical, value in inputs.items():
            real = find_field(layer, canonical)
            if not real:
                warnings.append(canonical)
                continue
            is_combo = canonical in ['DestinoEconomico']
            clause = build_clause(real, str(value), layer,
                                  partial=not is_combo, exact=is_combo)
            clauses.append(clause)
        expr = ' AND '.join(f'({c})' for c in clauses)
        return expr, warnings

    def clear(self):
        default_style = f"""
            QLineEdit {{
                border:1px solid {C['border']}; border-radius:3px;
                padding:2px 5px; background:{C['white']};
                font-size:11px; color:{C['text']}; min-height:18px;
            }}
            QLineEdit:focus {{ border:2px solid {C['secondary']}; }}
        """
        for w in self.f.values():
            if isinstance(w, QLineEdit):
                w.clear()
                w.setStyleSheet(default_style)
            elif isinstance(w, QComboBox):
                w.setCurrentIndex(0)

# ═════════════════════════════════════════════════════════════════════════════
#  DIALOGO PRINCIPAL
# ═════════════════════════════════════════════════════════════════════════════

class ConsultasPredialesDialog(QWidget):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface             = iface
        self.current_features  = []
        self._active_form      = None
        self._searched_fields  = []
        self._all_field_names  = []
        self._nav_index        = 0
        self._r2_features      = []
        self._r2_field_names   = []
        self._construccion_layer = None
        self._terreno_layer    = None

        self._build_ui()
        self._connect_signals()
        self._refresh_layers()
        self._restore_geometry()

    def _restore_geometry(self):
        s = QSettings('HerramientaCatastral', 'v2')
        size = s.value('size', QSize(720, 800))
        pos  = s.value('pos',  None)
        if isinstance(size, QSize):
            self.resize(size)
        if pos and isinstance(pos, QPoint):
            self.move(pos)
    def closeEvent(self, event):
        s = QSettings('HerramientaCatastral', 'v2')
        s.setValue('size', self.size())
        s.setValue('pos',  self.pos())
        try:
            QgsProject.instance().layersAdded.disconnect(self._refresh_layers)
            QgsProject.instance().layersRemoved.disconnect(self._refresh_layers)
        except Exception:
            pass
        self._results_dialog.close()
        super().closeEvent(event)

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.setStyleSheet(f'background:{C["bg"]}; color:{C["text"]};')
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(6)

        self._build_header(root)
        top_scroll, top_layout = self._build_scroll_area()
        self._build_layer_selector(top_layout)
        self._build_quick_search(top_layout)
        self._build_form_panel(top_layout)
        self._build_action_buttons(top_layout)
        self._build_nav(top_layout)
        self._build_r2_header(top_layout)
        self._build_status(top_layout)
        top_scroll.setWidget(top_scroll._inner)
        self._build_results_area(root, top_scroll)
        footer = QLabel('Sistema de Consulta Catastral - Colombia')
        footer.setStyleSheet(f'font-size:9px; color:#888; background:transparent; padding:2px 0;')
        footer.setAlignment(Qt.AlignCenter)
        root.addWidget(footer)

    def _build_header(self, root):
        h = QFrame()
        h.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {C['primary']}, stop:1 {C['secondary']});
                border-radius:8px; padding:0px;
            }}""")
        h.setFixedHeight(52)
        lo = QHBoxLayout(h); lo.setContentsMargins(10,0,14,0); lo.setSpacing(8)
        icon_path = os.path.join(os.path.dirname(__file__), 'icons', 'icon.png')
        ico_logo = QLabel()
        if os.path.exists(icon_path):
            pix = QPixmap(icon_path).scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            ico_logo.setPixmap(pix)
        ico_logo.setStyleSheet('background:transparent;')
        ico_logo.setFixedSize(32, 32)
        lo.addWidget(ico_logo)
        ico = QLabel('Consulta Catastral Local')
        ico.setStyleSheet('font-size:14px; font-weight:bold; color:white; background:transparent;')
        lo.addWidget(ico)
        ls = QLabel('IGAC Colombia')
        ls.setStyleSheet('color:rgba(255,255,255,0.82); font-size:10px; background:transparent;')
        lo.addWidget(ls)
        lf = QLabel('Fuente: Datos Catastrales')
        lf.setStyleSheet('color:rgba(255,255,255,0.55); font-size:9px; background:transparent;')
        lo.addWidget(lf, 1)
        root.addWidget(h)

    def _build_scroll_area(self):
        s = QScrollArea()
        s.setWidgetResizable(True); s.setFrameShape(QFrame.NoFrame)
        s.setStyleSheet(f'background:{C["bg"]}; border:none;')
        inner = QWidget()
        inner.setStyleSheet(f'background:{C["bg"]};')
        lo = QVBoxLayout(inner)
        lo.setContentsMargins(0,0,0,4); lo.setSpacing(6)
        s._inner = inner
        return s, lo

    def _build_layer_selector(self, tl):
        box = _group('Capa activa')
        lg = QVBoxLayout(box); lg.setContentsMargins(8,10,8,8); lg.setSpacing(4)
        r1 = QHBoxLayout()
        self.cbo_layer = _cbo()
        self.cbo_layer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_refresh = QPushButton('Refrescar')
        self.btn_refresh.setFixedHeight(28)
        self.btn_refresh.setStyleSheet(f"QPushButton{{background:{C['primary']};color:white;border:none;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:bold;}}QPushButton:hover{{background:{C['secondary']};}}")
        self.btn_diag = QPushButton('Campos')
        self.btn_diag.setFixedHeight(28)
        self.btn_diag.setToolTip('Ver todos los campos de la capa activa')
        self.btn_diag.setStyleSheet(f"QPushButton{{background:{C['primary']};color:white;border:none;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:bold;}}QPushButton:hover{{background:{C['secondary']};}}")
        r1.addWidget(self.cbo_layer,1); r1.addWidget(self.btn_refresh); r1.addWidget(self.btn_diag)
        lg.addLayout(r1)
        self.lbl_layer_meta = QLabel('---')
        self.lbl_layer_meta.setStyleSheet('font-size:10px;color:#555;')
        self.lbl_layer_meta.setWordWrap(True); lg.addWidget(self.lbl_layer_meta)
        self.lbl_tipo_badge = QLabel('')
        self.lbl_tipo_badge.setStyleSheet(f'font-size:11px;font-weight:bold;color:{C["primary"]};background:{C["tag_blue"]};padding:2px 8px;border-radius:3px;')
        lg.addWidget(self.lbl_tipo_badge)
        self.lbl_r2_badge = QLabel('')
        self.lbl_r2_badge.setStyleSheet(f'font-size:11px;font-weight:bold;color:{C["r2"]};background:{C["r2_bg"]};padding:2px 8px;border-radius:3px;')
        lg.addWidget(self.lbl_r2_badge)
        tl.addWidget(box)

    def _build_quick_search(self, tl):
        box = QFrame()
        box.setStyleSheet(f"QFrame{{background:{C['info_bg']};border:1px solid {C['secondary']};border-radius:5px;padding:2px;}}")
        lo = QHBoxLayout(box); lo.setContentsMargins(6,4,6,4); lo.setSpacing(5)
        self.inp_quick = QLineEdit()
        self.inp_quick.setPlaceholderText('Buscar: codigo, matricula, nombre, documento, vereda...')
        self.inp_quick.setStyleSheet(f"QLineEdit{{background:white;border:1px solid {C['border']};border-radius:4px;padding:4px 8px;font-size:12px;}}QLineEdit:focus{{border-color:{C['secondary']};}}")
        self.inp_quick.returnPressed.connect(self._quick_search)
        self.cbo_history = QComboBox()
        self.cbo_history.setFixedWidth(28); self.cbo_history.setFixedHeight(28)
        self.cbo_history.setToolTip('Historial de busquedas recientes')
        self.cbo_history.setStyleSheet(f"QComboBox{{background:{C['white']};border:1px solid {C['border']};border-radius:4px;font-size:11px;padding:0 4px;}}QComboBox::drop-down{{border:none;width:20px;}}QComboBox:hover{{border-color:{C['secondary']};}}")
        self.cbo_history.addItem('H')
        self.cbo_history.currentTextChanged.connect(self._load_from_history)
        self._search_history = []
        btn = QPushButton('Buscar')
        btn.setFixedHeight(28)
        btn.setStyleSheet(f"QPushButton{{background:{C['secondary']};color:white;border:none;border-radius:4px;padding:0 12px;font-weight:bold;font-size:11px;}}QPushButton:hover{{background:{C['primary']};}}")
        btn.clicked.connect(self._quick_search)
        lo.addWidget(self.inp_quick,1); lo.addWidget(self.cbo_history); lo.addWidget(btn)
        tl.addWidget(box)

    def _build_form_panel(self, tl):
        fh = QFrame()
        fh.setStyleSheet(f"QFrame{{background:{C['header']};border:1px solid {C['border']};border-radius:4px;}}")
        fl = QHBoxLayout(fh); fl.setContentsMargins(8,4,8,4)
        t = QLabel('Filtros avanzados (R1 - Terreno / Propietario)')
        t.setStyleSheet(f'font-weight:bold;font-size:11px;color:{C["primary"]};background:transparent;')
        self.lbl_form_mode = QLabel('')
        self.lbl_form_mode.setStyleSheet(f'font-size:10px;color:{C["success"]};background:transparent;font-style:italic;')
        self.btn_collapse = QPushButton('Ocultar')
        self.btn_collapse.setFixedSize(70,22); self.btn_collapse.setCheckable(True); self.btn_collapse.setChecked(True)
        self.btn_collapse.setToolTip('Mostrar / ocultar filtros avanzados')
        self.btn_collapse.setStyleSheet(f"QPushButton{{background:{C['primary']};color:white;border:none;border-radius:3px;font-size:10px;font-weight:bold;padding:0 8px;}}QPushButton:hover{{background:{C['secondary']};}}")
        self.btn_collapse.toggled.connect(self._toggle_form)
        fl.addWidget(t); fl.addWidget(self.lbl_form_mode,1); fl.addWidget(self.btn_collapse)
        tl.addWidget(fh)
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f'background:{C["white"]};border:1px solid {C["border"]};border-radius:4px;')
        self.stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.form_terreno = FormTerreno()
        self.stack.addWidget(self.form_terreno)
        self._active_form = self.form_terreno
        tl.addWidget(self.stack)

    def _build_action_buttons(self, tl):
        r = QHBoxLayout(); r.setSpacing(5)
        self.btn_clear   = _btn('Limpiar')
        self.btn_select  = _btn('Seleccionar')
        self.btn_zoom    = _btn('Zoom')
        self.btn_export  = _btn('Excel')
        for b in [self.btn_clear, self.btn_select, self.btn_zoom, self.btn_export]:
            r.addWidget(b)
        tl.addLayout(r)

    def _build_nav(self, tl):
        nf = QFrame()
        nf.setStyleSheet(f"QFrame{{background:{C['header']};border:1px solid {C['border']};border-radius:4px;}}")
        nl = QHBoxLayout(nf); nl.setContentsMargins(6,3,6,3); nl.setSpacing(6)
        self.btn_nav_prev = QPushButton('<< Anterior')
        self.btn_nav_next = QPushButton('Siguiente >>')
        ss = f"QPushButton{{background:{C['primary']};color:white;border:none;border-radius:3px;font-weight:bold;font-size:10px;padding:0 10px;}}QPushButton:hover{{background:{C['secondary']};}}QPushButton:disabled{{background:#95a5a6;color:#ddd;}}"
        for b in [self.btn_nav_prev, self.btn_nav_next]:
            b.setFixedHeight(24); b.setStyleSheet(ss)
        self.lbl_count = QLabel('Sin resultados')
        self.lbl_count.setStyleSheet(f'font-weight:bold;font-size:11px;color:{C["primary"]};background:transparent;')
        self.lbl_count.setAlignment(Qt.AlignCenter)
        nl.addWidget(self.btn_nav_prev); nl.addWidget(self.lbl_count,1); nl.addWidget(self.btn_nav_next)
        tl.addWidget(nf)

    def _build_r2_header(self, tl):
        self.lbl_r2_info = QLabel('')
        self.lbl_r2_info.setStyleSheet(f'font-size:10px;color:{C["r2"]};background:{C["r2_bg"]};border-radius:3px;padding:2px 6px;')
        self.lbl_r2_info.hide()
        tl.addWidget(self.lbl_r2_info)

    def _build_status(self, tl):
        self.lbl_status = QLabel('Listo - selecciona una capa y realiza una busqueda.')
        self.lbl_status.setStyleSheet(f'font-size:10px;color:#555;background:{C["info_bg"]};border:1px solid {C["border"]};border-radius:3px;padding:3px 8px;')
        self.lbl_status.setWordWrap(True); tl.addWidget(self.lbl_status)
        self.lbl_expr = QLabel(); self.lbl_expr.hide(); tl.addWidget(self.lbl_expr)
        self.lbl_warn = QLabel(); self.lbl_warn.hide(); tl.addWidget(self.lbl_warn)
        self.lbl_spatial_status = QLabel('')
        self.lbl_spatial_status.setStyleSheet(f'font-size:11px;font-weight:bold;color:{C["success"]};background:{C["spatial_bg"]};border-radius:3px;padding:2px 6px;')
        self.lbl_spatial_status.setWordWrap(True); tl.addWidget(self.lbl_spatial_status)

    def _build_results_area(self, root, top_scroll):
        self._results_dialog = QDialog(self)
        self._results_dialog.setWindowTitle('Resultados - Consultas Catastrales')
        self._results_dialog.setMinimumSize(600, 250)
        self._results_dialog.resize(850, 350)
        self._results_dialog.setAttribute(Qt.WA_DeleteOnClose, False)
        self._results_dialog.setStyleSheet(f'background:{C["bg"]};')
        dl = QVBoxLayout(self._results_dialog)
        dl.setContentsMargins(6, 6, 6, 6)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border:1px solid {C['border']}; border-radius:4px; background:{C['white']}; }}
            QTabBar::tab {{
                background:{C['header']}; color:{C['text']}; border:1px solid {C['border']};
                border-bottom:1px solid {C['border']}; padding:4px 12px; font-weight:bold; font-size:10px;
                border-top-left-radius:4px; border-top-right-radius:4px; margin-right:1px;
            }}
            QTabBar::tab:selected {{ background:{C['white']}; border-bottom:1px solid {C['white']}; color:{C['primary']}; }}
            QTabBar::tab:hover {{ background:{C['hover']}; }}
        """)

        # Tab R1
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setMinimumSectionSize(50)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(20)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setMinimumHeight(100)
        self.table.setStyleSheet(f"""
            QTableWidget {{border:1px solid {C['border']};gridline-color:{C['border']};font-size:11px;background:{C['white']};}}
            QTableWidget::item {{padding:0px 3px;border:none;}}
            QTableWidget::item:alternate {{background:{C['alt']};}}
            QTableWidget::item:selected {{background:{C['secondary']};color:white;}}
            QHeaderView::section {{background:{C['primary']};color:white;padding:4px 3px;font-weight:bold;font-size:10px;border:none;border-right:1px solid rgba(255,255,255,0.2);}}
        """)
        self.table.itemSelectionChanged.connect(self._on_table_row_selected)

        # Tab R2
        self.r2_table = QTableWidget()
        self.r2_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.r2_table.setSortingEnabled(True)
        self.r2_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.r2_table.setAlternatingRowColors(True)
        self.r2_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.r2_table.horizontalHeader().setStretchLastSection(False)
        self.r2_table.horizontalHeader().setMinimumSectionSize(50)
        self.r2_table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.r2_table.verticalHeader().setVisible(False)
        self.r2_table.verticalHeader().setDefaultSectionSize(20)
        self.r2_table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.r2_table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.r2_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.r2_table.setMinimumHeight(80)
        self.r2_table.setStyleSheet(f"""
            QTableWidget {{border:1px solid {C['border']};gridline-color:{C['border']};font-size:11px;background:{C['white']};}}
            QTableWidget::item {{padding:0px 3px;border:none;}}
            QTableWidget::item:alternate {{background:{C['r2_bg']};}}
            QTableWidget::item:selected {{background:{C['r2']};color:white;}}
            QHeaderView::section {{background:{C['r2']};color:white;padding:4px 3px;font-weight:bold;font-size:10px;border:none;border-right:1px solid rgba(255,255,255,0.2);}}
        """)

        self.tabs.addTab(self.table, 'R1 - Terreno / Propietario')
        self.tabs.addTab(self.r2_table, 'R2 - Construcciones')
        dl.addWidget(self.tabs)

        # Show results toggle button in main UI
        self._results_btn = QPushButton('Resultados')
        self._results_btn.setFixedHeight(28)
        self._results_btn.setToolTip('Mostrar / ocultar ventana flotante de resultados')
        self._results_btn.setCheckable(True)
        self._results_btn.setStyleSheet(f"""
            QPushButton {{
                background:{C['primary']}; color:white; border:none;
                border-radius:4px; padding:0 10px; font-weight:bold; font-size:11px;
            }}
            QPushButton:hover {{ background:{C['secondary']}; }}
        """)
        self._results_btn.clicked.connect(self._toggle_results)

        root.addWidget(top_scroll, 1)
        root.addWidget(self._results_btn, 0, Qt.AlignRight)

    def _toggle_results(self):
        if self._results_dialog.isVisible():
            self._results_dialog.hide()
            self._results_btn.setChecked(False)
        else:
            self._results_dialog.show()
            self._results_btn.setChecked(True)

    # ── Conexiones ─────────────────────────────────────────────────────────────
    def _connect_signals(self):
        self.btn_refresh.clicked.connect(self._refresh_layers)
        self.btn_clear.clicked.connect(self._clear_all)
        self.btn_select.clicked.connect(self._select_on_map)
        self.btn_zoom.clicked.connect(self._zoom_to_selection)
        self.btn_export.clicked.connect(self._export_excel)
        self.cbo_layer.currentIndexChanged.connect(self._on_layer_changed)
        self.btn_nav_prev.clicked.connect(self._nav_prev)
        self.btn_nav_next.clicked.connect(self._nav_next)
        self.btn_diag.clicked.connect(self._show_field_diagnostics)
        QgsProject.instance().layersAdded.connect(self._refresh_layers)
        QgsProject.instance().layersRemoved.connect(self._refresh_layers)
        QShortcut(QKeySequence('Escape'), self, self._clear_all)
        QShortcut(QKeySequence('Ctrl+E'), self, self._export_excel)
        QShortcut(QKeySequence('Ctrl+Z'), self, self._zoom_to_selection)

    # ── Capas ─────────────────────────────────────────────────────────────────
    def _refresh_layers(self, *_):
        self.cbo_layer.blockSignals(True)
        prev = self.cbo_layer.currentData()
        self.cbo_layer.clear()

        for lyr in QgsProject.instance().mapLayers().values():
            if not isinstance(lyr, QgsVectorLayer):
                continue
            self.cbo_layer.addItem(lyr.name(), lyr.id())

        idx = self.cbo_layer.findData(prev)
        if idx >= 0:
            self.cbo_layer.setCurrentIndex(idx)
        self.cbo_layer.blockSignals(False)
        self._on_layer_changed()

    def _active_layer(self):
        lid = self.cbo_layer.currentData()
        return QgsProject.instance().mapLayer(lid) if lid else None

    def _find_construccion_pair(self):
        layer = self._active_layer()
        if not layer:
            QMessageBox.information(self, 'Sin capa', 'Selecciona una capa primero.')
            return
        z, t, y = classify_layer_name(layer.name())
        if not z:
            z = 'u_' if layer.name().lower().startswith('u') else 'r_'
        if not y:
            y = ''

        best = None
        for lyr in QgsProject.instance().mapLayers().values():
            if not isinstance(lyr, QgsVectorLayer):
                continue
            lz, lt, ly = classify_layer_name(lyr.name())
            if lt == 'construccion':
                if y and lz == z and ly == y:
                    best = lyr
                    break
                if lz == z and not best:
                    best = lyr

        if best:
            self._construccion_layer = best
            self.lbl_r2_badge.setText('R2: ' + best.name())
            self.lbl_r2_info.setText('R2 activa: ' + best.name() + ' (' + str(len(best.fields())) + ' campos, ' + str(best.featureCount()) + ' registros)')
            self.lbl_r2_info.show()
            self._set_status('Capa R2 encontrada: ' + best.name())
        else:
            self._construccion_layer = None
            self.lbl_r2_badge.setText('')
            self.lbl_r2_info.hide()
            QMessageBox.information(self, 'Sin pareja R2',
                'No se encontro una capa de construccion (R2) para esta capa. '
                'Asegurate de tener cargada la capa de construccion correspondiente.')

    def _on_layer_changed(self):
        layer = self._active_layer()
        if not layer:
            self.lbl_layer_meta.setText('---')
            self.lbl_tipo_badge.setText('')
            self.lbl_r2_badge.setText('')
            self.lbl_r2_info.hide()
            return
        n_feats  = layer.featureCount()
        n_fields = len(layer.fields())
        geo_type = QgsWkbTypes.displayString(layer.wkbType())
        crs_name = layer.crs().authid()
        src      = layer.source().split('|')[0]
        self.lbl_layer_meta.setText(
            str(n_feats) + ' registros - ' + str(n_fields) + ' campos - ' + geo_type + ' - ' + crs_name + ' | ' + src
        )
        ltype = detect_layer_type(layer.name())
        self.lbl_tipo_badge.setText(ltype.upper() if ltype != 'desconocido' else '')

        # Detectar capa unificada R1+R2
        has_np = find_field(layer, 'NoPredial') is not None
        has_cod_unidad = find_field(layer, 'CodigoUnidad') is not None
        has_area_const = find_field(layer, 'AreaConstruida') is not None or find_field(layer, 'AreaConstruccion') is not None
        has_pisos = find_field(layer, 'Pisos') is not None
        is_joined = has_np and (has_cod_unidad or (has_area_const and has_pisos))

        self.stack.setCurrentIndex(0)
        self._active_form = self.form_terreno

        if is_joined:
            self._construccion_layer = layer
            self._terreno_layer = layer
            self.lbl_r2_badge.setText('Unificada R1+R2')
            self.lbl_r2_info.setText('Capa unificada R1+R2: ' + layer.name() + ' - contiene datos de terreno y construccion')
            self.lbl_r2_info.show()
            self.tabs.setTabText(0, 'R1 - Terreno / Propietario')
            self.tabs.setTabText(1, 'R2 - Construccion (misma capa)')
        elif ltype == 'terreno':
            self._find_construccion_pair()
            self.tabs.setTabText(0, 'R1 - Terreno / Propietario')
            self.tabs.setTabText(1, 'R2 - Construcciones')
        elif ltype == 'construccion':
            self._construccion_layer = layer
            z2, t2, y2 = classify_layer_name(layer.name())
            for lyr in QgsProject.instance().mapLayers().values():
                if not isinstance(lyr, QgsVectorLayer):
                    continue
                lz, lt, ly = classify_layer_name(lyr.name())
                if lt == 'terreno':
                    if y2 and lz == z2 and ly == y2:
                        self._terreno_layer = lyr
                        break
                    if lz == z2:
                        self._terreno_layer = lyr
            self.lbl_r2_badge.setText('R2 activa: ' + layer.name())
            self.lbl_r2_info.setText('R2 activa: ' + layer.name() + ' (' + str(len(layer.fields())) + ' campos)')
            self.lbl_r2_info.show()
        else:
            self._construccion_layer = None
            self._terreno_layer = None
            self.lbl_r2_badge.setText('')
            self.lbl_r2_info.hide()

    # ── Diagnostico de campos ─────────────────────────────────────────────────
    def _show_field_diagnostics(self):
        layer = self._active_layer()
        if not layer:
            QMessageBox.information(self, 'Sin capa', 'Selecciona una capa primero.')
            return

        dlg = QDialog(self)
        dlg.setWindowTitle('Campos de la capa: ' + layer.name())
        dlg.resize(520, 450)
        v = QVBoxLayout(dlg)
        info = QLabel('La capa tiene <b>' + str(len(layer.fields())) + '</b> campos.')
        info.setWordWrap(True)
        info.setStyleSheet('font-size:11px; color:#555; padding:4px;')
        v.addWidget(info)
        lst = QListWidget()
        lst.setStyleSheet('font-family:monospace; font-size:11px;')
        type_labels = {
            QVariant.Int: 'Entero', QVariant.LongLong: 'Entero largo',
            QVariant.Double: 'Decimal', QVariant.String: 'Texto',
            QVariant.Date: 'Fecha', QVariant.DateTime: 'FechaHora',
        }
        for fld in layer.fields():
            tname = type_labels.get(fld.type(), 'tipo:' + str(fld.type()))
            item = QListWidgetItem(fld.name().ljust(30) + '  [' + tname + ']')
            lst.addItem(item)
        v.addWidget(lst)
        note = QLabel('Nombres truncados a 10 chars son normales en shapefiles (.shp). El plugin los detecta automaticamente.')
        note.setWordWrap(True)
        note.setStyleSheet('font-size:10px; color:' + C["primary"] + '; background:' + C["info_bg"] + '; padding:5px; border-radius:3px;')
        v.addWidget(note)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(dlg.accept)
        v.addWidget(bb)
        dlg.exec_()

    # ── Busqueda R1 ────────────────────────────────────────────────────────────
    def _run_search(self):
        layer = self._active_layer()
        if not layer:
            QMessageBox.warning(self, 'Sin capa', 'Selecciona una capa vectorial primero.')
            return

        try:
            layer.removeSelection()
        except Exception:
            pass

        warnings = []
        expr_str = ''
        if self._active_form:
            expr_str, warnings = self._active_form.build_expression(layer)
            self._searched_fields = self._active_form.get_searched_fields()

        if expr_str:
            expr = QgsExpression(expr_str)
            if expr.hasParserError():
                QMessageBox.critical(self, 'Error en expresion', 'Error: ' + expr.parserErrorString())
                return

        try:
            req = QgsFeatureRequest()
            if expr_str:
                req.setFilterExpression(expr_str)
            self.current_features = list(layer.getFeatures(req))
        except Exception as e:
            QMessageBox.critical(self, 'Error al consultar', str(e))
            return

        self._all_field_names = _filter_fields([f.name() for f in layer.fields()])
        self._nav_index = 0
        self.lbl_form_mode.setText('')
        self._populate_table(layer, self.current_features)

        if expr_str:
            self.lbl_expr.setText('Filtro ejecutado: ' + expr_str[:200])
            self.lbl_expr.show()
        else:
            inputs = self._active_form.get_inputs() if self._active_form else {}
            if inputs:
                self.lbl_expr.setText('No se pudo construir el filtro. Usa "Campos" para ver los nombres.')
                self.lbl_expr.show()
            else:
                self.lbl_expr.setText('Sin filtro - mostrando todos los registros')
                self.lbl_expr.show()

        if warnings:
            self.lbl_warn.setText('Campos no encontrados: ' + ', '.join(warnings))
            self.lbl_warn.show()
        else:
            self.lbl_warn.hide()

        self.lbl_spatial_status.setText('')
        n = len(self.current_features)
        self._set_status('R1: ' + str(n) + ' registro(s) en "' + layer.name() + '"' if n > 0 else 'Sin resultados')
        if self.current_features:
            self._zoom_to_features(self.current_features)
            self._load_r2_for_current()

    def _search_r2(self):
        layer = self._construccion_layer or self._active_layer()
        if not layer:
            QMessageBox.warning(self, 'Sin capa R2',
                'No hay capa de construccion (R2) seleccionada. Usa "Buscar R2" para encontrarla.')
            return

        ltype = detect_layer_type(layer.name())
        if ltype != 'construccion' and layer != self._construccion_layer:
            QMessageBox.warning(self, 'Capa incorrecta',
                'La capa activa no es de construccion (R2). Usa "Buscar R2" para encontrar la capa correcta.')
            return

        texto = self.inp_quick.text().strip()
        if texto:
            nopredial = find_field(layer, 'NoPredial')
            if nopredial:
                partes = ['"' + nopredial + '" ILIKE \'%' + texto.replace("'", "''") + '%\'']
                expr_str = ' OR '.join(partes)
                try:
                    req = QgsFeatureRequest().setFilterExpression(expr_str)
                    feats = list(layer.getFeatures(req))
                    self._r2_features = feats
                    self._r2_field_names = _filter_fields([f.name() for f in layer.fields()])
                    self._populate_r2_table(layer, feats)
                    self.tabs.setCurrentIndex(1)
                    self._set_status('R2: ' + str(len(feats)) + ' construccion(es) encontrada(s)')
                    return
                except Exception as e:
                    QMessageBox.critical(self, 'Error', str(e))
                    return

        try:
            feats = list(layer.getFeatures())
            self._r2_features = feats
            self._r2_field_names = _filter_fields([f.name() for f in layer.fields()])
            self._populate_r2_table(layer, feats)
            self.tabs.setCurrentIndex(1)
            self._set_status('R2: ' + str(len(feats)) + ' registro(s) de construccion')
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))

    # ── Poblacion de tablas ────────────────────────────────────────────────────
    def _populate_table(self, layer, features):
        n = len(features)
        self._nav_index = max(0, min(getattr(self, '_nav_index', 0), n - 1)) if n else 0

        ALN = Qt.AlignLeft | Qt.AlignVCenter
        self.table.setSortingEnabled(False)
        self.table.setRowCount(n)
        self.table.setColumnCount(len(self._all_field_names))
        labels = [RENAME_FIELDS.get(_plain(f), f) for f in self._all_field_names]
        self.table.setHorizontalHeaderLabels(labels)

        for r, feat in enumerate(features):
            for c, fname in enumerate(self._all_field_names):
                try:
                    val = feat[fname]
                except Exception:
                    val = None
                txt = _fmt_table_val(fname, val)
                item = QTableWidgetItem(txt)
                item.setTextAlignment(ALN)
                item.setData(Qt.UserRole, feat.id())
                self.table.setItem(r, c, item)

        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        if n > 0:
            self.table.blockSignals(True)
            self.table.selectRow(self._nav_index)
            self.table.blockSignals(False)

        if n > 0:
            self._fill_form_from_feature(features[self._nav_index], layer)

        if n > 0:
            self._results_dialog.show()
            self._results_btn.setChecked(True)

        color = C['success'] if n > 0 else C['error']
        if n == 0:
            self.lbl_count.setText('Sin resultados R1')
        elif n == 1:
            self.lbl_count.setText('1 predio encontrado')
        else:
            self.lbl_count.setText('Predio ' + str(self._nav_index + 1) + ' de ' + str(n))
        self.lbl_count.setStyleSheet('font-weight:bold; font-size:11px; color:' + color + '; background:transparent;')
        self.btn_nav_prev.setEnabled(n > 1 and self._nav_index > 0)
        self.btn_nav_next.setEnabled(n > 1 and self._nav_index < n - 1)

    def _populate_r2_table(self, layer, features):
        n = len(features)
        ALN = Qt.AlignLeft | Qt.AlignVCenter
        self.r2_table.setSortingEnabled(False)
        self.r2_table.setRowCount(n)
        field_names = self._r2_field_names or _filter_fields([f.name() for f in layer.fields()])
        self.r2_table.setColumnCount(len(field_names))
        labels = [RENAME_FIELDS.get(_plain(f), f) for f in field_names]
        self.r2_table.setHorizontalHeaderLabels(labels)

        for r, feat in enumerate(features):
            for c, fname in enumerate(field_names):
                try:
                    val = feat[fname]
                except Exception:
                    val = None
                txt = _fmt_table_val(fname, val)
                item = QTableWidgetItem(txt)
                item.setTextAlignment(ALN)
                item.setData(Qt.UserRole, feat.id())
                self.r2_table.setItem(r, c, item)

        self.r2_table.setSortingEnabled(True)
        self.r2_table.resizeColumnsToContents()
        self.r2_table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)

    def _load_r2_for_current(self):
        self._r2_features = []
        self._r2_field_names = []

        if not self._construccion_layer:
            return
        if not self.current_features or self._nav_index >= len(self.current_features):
            self._clear_r2_table()
            return

        feat = self.current_features[self._nav_index]
        layer = self._active_layer()
        if not layer:
            self._clear_r2_table()
            return

        # Estrategia 1: buscar por NoPredial
        r2_feats = self._load_r2_by_field(layer, feat, 'NoPredial')
        if r2_feats:
            self._set_r2_results(r2_feats)
            return

        # Estrategia 2: buscar por MatriculaInmobiliaria
        r2_feats = self._load_r2_by_field(layer, feat, 'MatriculaInmobiliaria')
        if r2_feats:
            self._set_r2_results(r2_feats)
            return

        # Estrategia 3: buscar por otros codigos
        for canon in ('NUPRE', 'NumeroPredial', 'CodigoPredial'):
            r2_feats = self._load_r2_by_field(layer, feat, canon)
            if r2_feats:
                self._set_r2_results(r2_feats)
                return

        self._clear_r2_table()
        self._set_status('Sin construcciones (R2) para este predio')

    def _load_r2_by_field(self, layer, feat, canonical):
        src_field = find_field(layer, canonical)
        if not src_field:
            return []
        src_val = feat[src_field]
        if src_val is None:
            return []
        src_str = str(src_val).strip()
        if not src_str:
            return []

        r2_field = find_field(self._construccion_layer, canonical)
        if not r2_field:
            return []

        try:
            # Coincidencia exacta para numericos
            fld_info = self._construccion_layer.fields().field(r2_field)
            if fld_info.type() in NUM_TYPES:
                try:
                    num_val = int(src_str)
                    clause = '"' + r2_field + '" = ' + str(num_val)
                    req = QgsFeatureRequest().setFilterExpression(clause)
                    res = list(self._construccion_layer.getFeatures(req))
                    if res:
                        return res
                except ValueError:
                    pass

            # ILIKE exacto
            safe = src_str.replace("'", "''")
            clause = '"' + r2_field + '" ILIKE \'' + safe + '\''
            req = QgsFeatureRequest().setFilterExpression(clause)
            res = list(self._construccion_layer.getFeatures(req))
            if res:
                return res

            # ILIKE parcial
            clause = '"' + r2_field + '" ILIKE \'%' + safe + '%\''
            req = QgsFeatureRequest().setFilterExpression(clause)
            return list(self._construccion_layer.getFeatures(req))
        except Exception:
            return []

    def _set_r2_results(self, feats):
        self._r2_features = feats
        self._r2_field_names = _filter_fields([f.name() for f in self._construccion_layer.fields()])
        self._populate_r2_table(self._construccion_layer, feats)
        if feats:
            self.tabs.setCurrentIndex(1)
            self._set_status(str(len(feats)) + ' construccion(es) para este predio')

    def _clear_r2_table(self):
        self._r2_features = []
        self._r2_field_names = []
        if hasattr(self, 'r2_table') and self._construccion_layer:
            self._populate_r2_table(self._construccion_layer, [])

    # ── Navegacion ──────────────────────────────────────────────────────────────
    def _on_table_row_selected(self):
        rows = list({i.row() for i in self.table.selectedItems()})
        if not rows or not self.current_features:
            return
        idx = rows[0]
        if idx >= len(self.current_features):
            return
        self._nav_index = idx
        layer = self._active_layer()
        if layer:
            self._fill_form_from_feature(self.current_features[idx], layer)
            n = len(self.current_features)
            self.lbl_count.setText('Predio ' + str(idx + 1) + ' de ' + str(n))
            self.btn_nav_prev.setEnabled(idx > 0)
            self.btn_nav_next.setEnabled(idx < n - 1)
            self._zoom_to_features([self.current_features[idx]])
            self._load_r2_for_current()

    def _nav_prev(self):
        if self.current_features and self._nav_index > 0:
            self._nav_index -= 1
            layer = self._active_layer()
            if layer:
                self._populate_table(layer, self.current_features)
                self._zoom_to_features([self.current_features[self._nav_index]])
                self._load_r2_for_current()

    def _nav_next(self):
        if self.current_features and self._nav_index < len(self.current_features) - 1:
            self._nav_index += 1
            layer = self._active_layer()
            if layer:
                self._populate_table(layer, self.current_features)
                self._zoom_to_features([self.current_features[self._nav_index]])
                self._load_r2_for_current()

    def _toggle_form(self, expanded):
        self.stack.setVisible(expanded)
        self.btn_collapse.setText('Ocultar' if expanded else 'Mostrar')

    def _quick_search(self):
        texto = self.inp_quick.text().strip()
        if not texto:
            return
        layer = self._active_layer()
        if not layer:
            QMessageBox.warning(self, 'Sin capa', 'Selecciona una capa vectorial.')
            return

        codigos_vereda = self._lookup_vereda_codes(texto)
        if codigos_vereda:
            real_cod = find_field(layer, 'CodigoVereda')
            real_nom = find_field(layer, 'Vereda')
            partes = []
            if real_nom:
                partes.append('"' + real_nom + '" ILIKE \'%' + texto.replace("'", "''") + '%\'')
            if real_cod:
                for cod in codigos_vereda:
                    partes.append('"' + real_cod + '" = \'' + cod.replace("'", "''") + '\'')
            if partes:
                self._ejecutar_busqueda(layer, texto, ' OR '.join(partes), ['Vereda', 'CodigoVereda'])
                return

        campos_buscar = [
            'NoPredial', 'NumeroPredial',
            'Nombre', 'NoDocumento',
            'MatriculaInmobiliaria',
            'Vereda', 'CodigoVereda',
            'Direccion', 'NUPRE',
        ]
        partes = []
        for canon in campos_buscar:
            real = find_field(layer, canon)
            if not real:
                continue
            fld  = layer.fields().field(real)
            if fld.type() in (QVariant.String,):
                partes.append('"' + real + '" ILIKE \'%' + texto.replace("'", "''") + '%\'')
            else:
                partes.append('to_string("' + real + '") ILIKE \'%' + texto.replace("'", "''") + '%\'')
        if partes:
            self._ejecutar_busqueda(layer, texto, ' OR '.join(partes), campos_buscar)
        else:
            QMessageBox.warning(self, 'Sin campos', 'No se encontraron campos clave en la capa.')

    def _ejecutar_busqueda(self, layer, texto, expr_str, campos_buscar):
        expr = QgsExpression(expr_str)
        if expr.hasParserError():
            QMessageBox.critical(self, 'Error en expresion', expr.parserErrorString())
            return
        try:
            req = QgsFeatureRequest().setFilterExpression(expr_str)
            self.current_features = list(layer.getFeatures(req))
            self._all_field_names = _filter_fields([f.name() for f in layer.fields()])
            self._searched_fields = campos_buscar
            self._nav_index = 0
            self._populate_table(layer, self.current_features)
            n = len(self.current_features)
            self.lbl_expr.setText('Busqueda: "' + texto + '" - ' + str(n) + ' resultado(s)')
            self.lbl_expr.show()
            self._set_status('Busqueda rapida "' + texto + '": ' + str(n) + ' resultado(s)')
            self._add_to_history(texto)
            ndoc = find_field(layer, 'NoDocumento')
            if ndoc and self.current_features:
                self._expand_by_owner(layer, ndoc, texto)
            if self.current_features:
                self._zoom_to_features(self.current_features)
                self._load_r2_for_current()
            else:
                self._r2_features = []
                self._r2_field_names = []
                if self._construccion_layer:
                    self._populate_r2_table(self._construccion_layer, [])
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))

    def _expand_by_owner(self, layer, ndoc_field, texto):
        """Si la busqueda fue por NoDocumento, busca todos los predios del mismo propietario."""
        try:
            doc_vals = set()
            for f in self.current_features:
                v = f[ndoc_field]
                if v is not None:
                    doc_vals.add(str(v).strip())
            if not doc_vals:
                return
            nombre_field = find_field(layer, 'Nombre')
            if not nombre_field:
                return
            name_parts = []
            for f in self.current_features:
                nv = f[nombre_field]
                if nv is not None and str(nv).strip():
                    safe_name = str(nv).strip().replace("'", "''")
                    name_parts.append('"' + nombre_field + '" ILIKE \'%' + safe_name + '%\'')
            if not name_parts:
                return
            name_expr = ' OR '.join(name_parts)
            name_req = QgsFeatureRequest().setFilterExpression(name_expr)
            all_feats = list(layer.getFeatures(name_req))
            existing_ids = {f.id() for f in self.current_features}
            new_feats = [f for f in all_feats if f.id() not in existing_ids]
            if new_feats:
                self.current_features.extend(new_feats)
                self._set_status('Expandido: ' + str(len(self.current_features)) + ' predios del propietario encontrados')
        except Exception:
            pass

    def _add_to_history(self, texto):
        if texto in self._search_history:
            self._search_history.remove(texto)
        self._search_history.insert(0, texto)
        self._search_history = self._search_history[:10]
        self.cbo_history.blockSignals(True)
        self.cbo_history.clear()
        self.cbo_history.addItem('H')
        for h in self._search_history:
            self.cbo_history.addItem(h)
        self.cbo_history.setCurrentIndex(0)
        self.cbo_history.blockSignals(False)

    def _load_from_history(self, texto):
        if texto and texto != 'H':
            self.inp_quick.setText(texto)
            self.cbo_history.setCurrentIndex(0)

    def _set_status(self, msg):
        if hasattr(self, 'lbl_status'):
            self.lbl_status.setText(msg)

    def _zoom_to_features(self, features, zoom_all=True):
        layer = self._active_layer()
        if not layer or not features:
            return

        if QgsWkbTypes.geometryType(layer.wkbType()) in (
            QgsWkbTypes.PolygonGeometry,
            QgsWkbTypes.LineGeometry,
            QgsWkbTypes.PointGeometry,
        ):
            layer.selectByIds([f.id() for f in features])
            self.iface.setActiveLayer(layer)
            self.iface.actionZoomToSelected().trigger()
            return

        src_np = find_field(layer, 'NoPredial')
        if not src_np:
            return
        valores_np = set()
        for f in features:
            v = f[src_np]
            if v is not None and str(v).strip():
                valores_np.add(str(v).strip())
        if not valores_np:
            return
        tgt = self._find_polygon_layer_auto()
        if not tgt:
            return
        tgt_np = find_field(tgt, 'NoPredial')
        if not tgt_np:
            return
        ids_sel = [
            f.id() for f in tgt.getFeatures()
            if f[tgt_np] is not None and str(f[tgt_np]).strip() in valores_np
        ]
        if ids_sel:
            tgt.selectByIds(ids_sel)
            self.iface.setActiveLayer(tgt)
            self.iface.actionZoomToSelected().trigger()

    def _find_polygon_layer_auto(self):
        candidates = []
        for lyr in QgsProject.instance().mapLayers().values():
            if not isinstance(lyr, QgsVectorLayer):
                continue
            if QgsWkbTypes.geometryType(lyr.wkbType()) != QgsWkbTypes.PolygonGeometry:
                continue
            fn = find_field(lyr, 'NoPredial')
            if not fn:
                continue
            score = sum(2 for kw in ['terreno', 'predio', 'lote', 'parcela', 'catast']
                        if kw in lyr.name().lower())
            candidates.append((score, lyr))
        return max(candidates, key=lambda x: x[0])[1] if candidates else None

    # ── Acciones ──────────────────────────────────────────────────────────────
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

    def _fill_form_from_feature(self, feat, layer):
        form = self._active_form
        if not hasattr(form, 'f'):
            return

        text_fields = [
            'NumeroPredial', 'NoPredialAnterior', 'Vereda', 'CodigoVereda',
            'NumeroSubterraneos', 'Direccion', 'ZonaFisica', 'ZonaEconomica',
            'AreaTerreno', 'AreaPerimetral', 'AreaGeografica', 'AreaConstruida',
            'AvaluoCatastral', 'Vigencia', 'MatriculaInmobiliaria',
            'Nombre', 'TipoDocumento', 'NoDocumento',
            'Estrato', 'Uso', 'Pisos', 'Banos', 'Locales', 'Puntaje',
            'Habitaciones',
        ]
        combo_fields = ['DestinoEconomico']
        combo_fields = ['DestinoEconomico']

        display_style = 'QLineEdit { border:1px solid ' + C['secondary'] + '; border-radius:3px; padding:2px 5px; background:#fffde7; font-size:11px; color:' + C['text'] + '; min-height:18px; }'

        for canon in text_fields:
            widget = form.f.get(canon)
            if not widget:
                continue
            real = find_field(layer, canon)
            if not real:
                widget.clear()
                continue
            try:
                val = feat[real]
                txt = '' if val is None else str(val)

                if txt:
                    if canon in ('Banos', 'Pisos', 'Habitaciones', 'Locales', 'NumeroSubterraneos', 'Puntaje', 'Estrato', 'Vigencia'):
                        try:
                            txt = str(int(txt))
                        except ValueError:
                            pass
                    elif canon == 'AvaluoCatastral':
                        try:
                            num = float(txt)
                            txt = '$ ' + format(num, ',.0f').replace(',', '.')
                        except ValueError:
                            pass
                    elif canon in ('AreaGeografica', 'AreaTerreno', 'AreaConstruida', 'AreaPerimetral'):
                        txt = _fmt_area(txt)

                widget.blockSignals(True)
                widget.setText(txt)
                widget.setStyleSheet(display_style if txt else '')
                widget.blockSignals(False)
            except Exception:
                pass

        for canon in combo_fields:
            widget = form.f.get(canon)
            if not widget:
                continue
            real = find_field(layer, canon)
            if not real:
                continue
            try:
                val = feat[real]
                if val is None:
                    continue
                idx = widget.findData(str(val))
                if idx < 0:
                    idx = widget.findText(str(val), Qt.MatchContains)
                if idx >= 0:
                    widget.blockSignals(True)
                    widget.setCurrentIndex(idx)
                    widget.blockSignals(False)
            except Exception:
                pass

        if not self.stack.isVisible():
            self.btn_collapse.setChecked(True)

        self._auto_fill_vereda(feat, layer)

        self.lbl_form_mode.setText('Datos del predio seleccionado')
        idx = getattr(self, '_nav_index', 0)
        n = len(self.current_features) if self.current_features else 0
        self._set_status('Predio ' + str(idx + 1) + ' de ' + str(n) + ' cargado en formulario')

    def _auto_fill_vereda(self, feat, layer):
        form = self._active_form
        if not hasattr(form, 'f'):
            return
        cod_w = form.f.get('CodigoVereda')
        nom_w = form.f.get('Vereda')
        if not cod_w or not nom_w:
            return
        real_cod = find_field(layer, 'CodigoVereda')
        if real_cod:
            cod = str(feat[real_cod] or '').strip()
        else:
            cod = cod_w.text().strip()
        if not cod:
            return
        for lyr in QgsProject.instance().mapLayers().values():
            if not isinstance(lyr, QgsVectorLayer):
                continue
            _, lt, _ = classify_layer_name(lyr.name())
            if lt not in ('vereda', 'manzana'):
                n = lyr.name().lower().replace(' ', '_').replace('-', '_')
                if not any(kw in n for kw in ['vereda', 'veredas', 'barrio', 'localidad']):
                    continue
            cod_field = find_field(lyr, 'CodigoVereda')
            if not cod_field:
                continue
            nom_field = find_field(lyr, 'Vereda')
            if not nom_field:
                for name_candidate in ['Nombre', 'NombreVereda', 'NomVereda', 'VeredaNombre', 'Name']:
                    nom_field = find_field(lyr, name_candidate)
                    if nom_field:
                        break
            if not nom_field:
                for f in lyr.fields():
                    fn = _plain(f.name())
                    if fn in ('nombre', 'name', 'nom', 'nombres', 'nomb', 'denominacion'):
                        nom_field = f.name()
                        break
            if not cod_field or not nom_field:
                continue
            for f in lyr.getFeatures():
                val = str(f[cod_field] or '').strip()
                if val == cod:
                    nom_w.setText(str(f[nom_field] or ''))
                    display_style = 'QLineEdit { border:1px solid ' + C['secondary'] + '; border-radius:3px; padding:2px 5px; background:#fffde7; font-size:11px; color:' + C['text'] + '; min-height:18px; }'
                    nom_w.setStyleSheet(display_style)
                    return

    def _lookup_vereda_codes(self, texto):
        codigos = []
        for lyr in QgsProject.instance().mapLayers().values():
            if not isinstance(lyr, QgsVectorLayer):
                continue
            _, lt, _ = classify_layer_name(lyr.name())
            if lt not in ('vereda', 'manzana'):
                n = lyr.name().lower().replace(' ', '_').replace('-', '_')
                if not any(kw in n for kw in ['vereda', 'veredas', 'barrio', 'localidad']):
                    continue
            cod_field = find_field(lyr, 'CodigoVereda')
            if not cod_field:
                continue
            nom_field = find_field(lyr, 'Vereda')
            if not nom_field:
                for name_candidate in ['Nombre', 'NombreVereda', 'NomVereda', 'VeredaNombre', 'Name']:
                    nom_field = find_field(lyr, name_candidate)
                    if nom_field:
                        break
            if not nom_field:
                for f in lyr.fields():
                    fn = _plain(f.name())
                    if fn in ('nombre', 'name', 'nom', 'nombres', 'nomb', 'denominacion'):
                        nom_field = f.name()
                        break
            if not nom_field:
                continue
            t = texto.lower().replace("'", "''")
            for f in lyr.getFeatures():
                val = str(f[nom_field] or '').strip()
                if t in val.lower():
                    cod = str(f[cod_field] or '').strip()
                    if cod and cod not in codigos:
                        codigos.append(cod)
        return codigos

    def _export_excel(self):
        if not self.current_features and not self._r2_features:
            QMessageBox.information(self, 'Sin datos', 'Realiza primero una busqueda.')
            return

        path, _ = QFileDialog.getSaveFileName(self, 'Exportar a Excel', '', 'Excel (*.xlsx)')
        if not path:
            return
        if not path.lower().endswith('.xlsx'):
            path += '.xlsx'

        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter
        except ImportError:
            QMessageBox.critical(self, 'Libreria faltante',
                'Se requiere openpyxl. Instalala con: pip install openpyxl')
            return

        try:
            layer = self._active_layer()
            fecha_hoy = QDate.currentDate().toString('dd/MM/yyyy')
            nombre_capa = layer.name() if layer else '---'

            wb = openpyxl.Workbook()
            azul = '1a4b8c'
            azul_claro = '2e86de'
            gris_claro = 'f0f4f8'
            verde = '27ae60'
            morado = '8e44ad'

            st_titulo = Font(name='Arial', bold=True, size=14, color='FFFFFF')
            st_sub = Font(name='Arial', size=10, color='FFFFFF')
            st_hdr = Font(name='Arial', bold=True, size=10, color='FFFFFF')
            st_valor = Font(name='Arial', size=10)

            fill_azul = PatternFill('solid', fgColor=azul)
            fill_hdr = PatternFill('solid', fgColor=azul_claro)
            fill_alt = PatternFill('solid', fgColor=gris_claro)
            fill_r2 = PatternFill('solid', fgColor=morado)

            borde = Border(bottom=Side(style='thin', color='cccccc'), right=Side(style='thin', color='cccccc'))
            alin_izq = Alignment(horizontal='left', vertical='center', wrap_text=True)
            alin_cen = Alignment(horizontal='center', vertical='center')

            # Hoja R1
            if self.current_features:
                field_names = self._all_field_names
                ws = wb.active
                ws.title = 'R1 - Terreno'
                ws.merge_cells('A1:' + get_column_letter(len(field_names)) + '1')
                c = ws['A1']
                c.value = 'REGISTRO 1 - TERRENO / PROPIETARIO'
                c.font = st_titulo
                c.fill = fill_azul
                c.alignment = alin_cen
                ws.row_dimensions[1].height = 28

                ws.merge_cells('A2:' + get_column_letter(len(field_names)) + '2')
                c = ws['A2']
                c.value = 'Capa: ' + nombre_capa + ' | Fecha: ' + fecha_hoy + ' | ' + str(len(self.current_features)) + ' registros'
                c.font = st_sub
                c.fill = fill_hdr
                c.alignment = alin_cen
                ws.row_dimensions[2].height = 18

                for col, fname in enumerate(field_names, start=1):
                    c = ws.cell(row=3, column=col, value=fname)
                    c.font = st_hdr
                    c.fill = fill_azul
                    c.alignment = alin_cen
                    c.border = borde
                ws.row_dimensions[3].height = 20

                for r_idx, feat in enumerate(self.current_features, start=4):
                    es_par = (r_idx % 2 == 0)
                    ws.row_dimensions[r_idx].height = 18
                    for col, fname in enumerate(field_names, start=1):
                        try:
                            val = feat[fname]
                        except Exception:
                            val = None
                        raw = val if val is not None else ''
                        if isinstance(raw, (int, float)):
                            cell_val = raw
                        else:
                            s = str(raw).strip()
                            try:
                                cell_val = int(s) if '.' not in s else float(s)
                            except Exception:
                                cell_val = s
                        c = ws.cell(row=r_idx, column=col, value=cell_val)
                        c.font = st_valor
                        c.alignment = alin_izq
                        c.border = borde
                        if es_par:
                            c.fill = fill_alt

                for col_idx in range(1, len(field_names) + 1):
                    max_w = len(field_names[col_idx - 1])
                    for feat in self.current_features:
                        try:
                            v = feat[field_names[col_idx - 1]]
                            if v is not None:
                                max_w = max(max_w, min(len(str(v)), 40))
                        except Exception:
                            pass
                    ws.column_dimensions[get_column_letter(col_idx)].width = max(max_w + 3, 12)

                ws.freeze_panes = 'A4'
                ws.auto_filter.ref = 'A3:' + get_column_letter(len(field_names)) + str(3 + len(self.current_features))

            # Hoja R2
            if self._r2_features:
                r2_names = self._r2_field_names
                ws2 = wb.create_sheet('R2 - Construccion')
                ws2.merge_cells('A1:' + get_column_letter(len(r2_names)) + '1')
                c = ws2['A1']
                c.value = 'REGISTRO 2 - CONSTRUCCIONES'
                c.font = Font(name='Arial', bold=True, size=14, color='FFFFFF')
                c.fill = fill_r2
                c.alignment = alin_cen
                ws2.row_dimensions[1].height = 28

                ws2.merge_cells('A2:' + get_column_letter(len(r2_names)) + '2')
                c = ws2['A2']
                c.value = 'Capa: ' + (self._construccion_layer.name() if self._construccion_layer else '---') + ' | Fecha: ' + fecha_hoy + ' | ' + str(len(self._r2_features)) + ' construcciones'
                c.font = st_sub
                c.fill = PatternFill('solid', fgColor='a569bd')
                c.alignment = alin_cen
                ws2.row_dimensions[2].height = 18

                for col, fname in enumerate(r2_names, start=1):
                    c = ws2.cell(row=3, column=col, value=fname)
                    c.font = st_hdr
                    c.fill = fill_r2
                    c.alignment = alin_cen
                    c.border = borde
                ws2.row_dimensions[3].height = 20

                for r_idx, feat in enumerate(self._r2_features, start=4):
                    es_par = (r_idx % 2 == 0)
                    ws2.row_dimensions[r_idx].height = 18
                    for col, fname in enumerate(r2_names, start=1):
                        try:
                            val = feat[fname]
                        except Exception:
                            val = None
                        raw = val if val is not None else ''
                        if isinstance(raw, (int, float)):
                            cell_val = raw
                        else:
                            s = str(raw).strip()
                            try:
                                cell_val = int(s) if '.' not in s else float(s)
                            except Exception:
                                cell_val = s
                        c = ws2.cell(row=r_idx, column=col, value=cell_val)
                        c.font = st_valor
                        c.alignment = alin_izq
                        c.border = borde
                        if es_par:
                            c.fill = fill_alt

                for col_idx in range(1, len(r2_names) + 1):
                    max_w = len(r2_names[col_idx - 1])
                    for feat in self._r2_features:
                        try:
                            v = feat[r2_names[col_idx - 1]]
                            if v is not None:
                                max_w = max(max_w, min(len(str(v)), 40))
                        except Exception:
                            pass
                    ws2.column_dimensions[get_column_letter(col_idx)].width = max(max_w + 3, 12)

                ws2.freeze_panes = 'A4'
                ws2.auto_filter.ref = 'A3:' + get_column_letter(len(r2_names)) + str(3 + len(self._r2_features))

            # Hoja Resumen
            ws3 = wb.create_sheet('Resumen', 0)
            ws3.sheet_view.showGridLines = False

            def _c(row, col, val, bold=False, bg=None, center=False, sz=10):
                cell = ws3.cell(row=row, column=col, value=val)
                cell.font = Font(name='Arial', bold=bold, size=sz, color='FFFFFF' if bg else '2c3e50')
                cell.alignment = Alignment(horizontal='center' if center else 'left', vertical='center')
                if bg:
                    cell.fill = PatternFill('solid', fgColor=bg)
                return cell

            ws3.merge_cells('A1:C1')
            _c(1, 1, 'RESUMEN DE CONSULTA CATASTRAL', bold=True, bg='1a4b8c', center=True, sz=13)
            ws3.row_dimensions[1].height = 26
            ws3.merge_cells('A2:C2')
            _c(2, 1, 'Capa: ' + nombre_capa + ' | Fecha: ' + fecha_hoy, bg='2e86de', center=True, sz=9)

            resumen_data = [
                ('Capa consultada (R1)', nombre_capa),
                ('Capa construccion (R2)', self._construccion_layer.name() if self._construccion_layer else '---'),
                ('Fecha exportacion', fecha_hoy),
                ('Total registros R1', len(self.current_features) if self.current_features else 0),
                ('Total registros R2', len(self._r2_features) if self._r2_features else 0),
            ]
            for i, (lbl, val) in enumerate(resumen_data, start=4):
                ws3.row_dimensions[i].height = 18
                _c(i, 1, lbl, bold=True)
                _c(i, 2, val)
                for col in [1, 2]:
                    ws3.cell(i, col).border = Border(bottom=Side(style='thin', color='cccccc'))

            ws3.column_dimensions['A'].width = 28
            ws3.column_dimensions['B'].width = 36

            wb.save(path)

            total = (len(self.current_features) if self.current_features else 0) + \
                    (len(self._r2_features) if self._r2_features else 0)
            QMessageBox.information(self, 'Excel exportado',
                str(total) + ' registros exportados (' +
                str(len(self.current_features) if self.current_features else 0) + ' R1 + ' +
                str(len(self._r2_features) if self._r2_features else 0) + ' R2): ' + path)
            self._set_status('Excel exportado: ' + str(total) + ' registros')
        except Exception as e:
            QMessageBox.critical(self, 'Error al exportar Excel', str(e))

    def _clear_all(self):
        if self._active_form:
            self._active_form.clear()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        self.r2_table.setRowCount(0)
        self.r2_table.setColumnCount(0)
        self.current_features = []
        self._r2_features = []
        self._searched_fields = []
        self._nav_index = 0
        self.lbl_count.setText('Sin resultados')
        self.lbl_count.setStyleSheet('font-weight:bold; font-size:11px; color:' + C["primary"] + '; background:transparent;')
        self.btn_nav_prev.setEnabled(False)
        self.btn_nav_next.setEnabled(False)
        self.lbl_form_mode.setText('')
        self.inp_quick.clear()
        self.lbl_expr.hide()
        self.lbl_warn.hide()
        self._results_dialog.hide()
        self._results_btn.setChecked(False)
        self._set_status('Formulario limpiado - listo para nueva busqueda.')
