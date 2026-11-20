"""Pestaña de integración: GDB + R1 + R2 + cartera en una sola capa.

Consolida verticalmente las capas de terreno rural/urbano (formal e informal),
une los registros R1/R2, agrega la cartera y aplica el semáforo por predio.
"""

from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import BadZipFile, ZipFile

from qgis.PyQt.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QSortFilterProxyModel,
    QTimer,
    Qt,
    QVariant,
)
from qgis.PyQt.QtGui import QColor, QIcon, QPixmap
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QProgressDialog,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)
from qgis.core import (
    NULL,
    QgsExpression,
    QgsFeature,
    QgsFeatureRequest,
    QgsField,
    QgsFields,
    QgsMemoryProviderUtils,
    QgsProject,
    QgsProviderRegistry,
    QgsCategorizedSymbolRenderer,
    QgsRendererCategory,
    QgsSymbol,
    QgsVectorLayer,
)

from .cartera_core import (
    STATUS_CLEAR,
    STATUS_DEBT,
    STATUS_UNKNOWN,
    normalize_words,
)
from .gdb_join_core import (
    classify_terrain_source,
    collapse_join_values,
    build_export_analytics,
    check_municipality_license,
    dominant_municipality,
    is_code_segment_name,
    key_variants,
    left_join_rows_automatic,
    merge_field_definitions,
    municipality_matches_license,
    municipality_of_code,
    parse_number,
    partition_predial_rows,
    stack_attribute_sources,
    summarize_presence_matches,
    unmatched_right_groups,
)

# Municipio habilitado para el aplicativo (se muestra en los mensajes; el
# control real vive en el hash con sal de gdb_join_core).
LICENSED_MUNICIPALITY_CODE = '18479'
LICENSED_MUNICIPALITY_NAME = 'Morelia (Caquetá)'

# Pistas para descubrir el campo de código predial / ficha (un solo campo).
KEY_HINTS = (
    'numero_predial', 'numero predial', 'num_predial', 'codigo_predial',
    'cod_predial', 'codigo', 'cod_pred', 'nupre', 'ficha',
)

VALUE_HINTS = ('saldo', 'deuda', 'mora', 'valor_deuda', 'cartera', 'valor')
OWNER_HINTS = ('propietario', 'titular', 'nombre', 'contribuyente')
DESDE_HINTS = ('vigencia_desde', 'vig_desde', 'anio_desde', 'ano_desde', 'desde')
HASTA_HINTS = ('vigencia_hasta', 'vig_hasta', 'anio_hasta', 'ano_hasta', 'hasta')
STATUS_LABELS = {
    STATUS_DEBT: 'EN DEUDA',
    STATUS_CLEAR: 'PAZ Y SALVO',
    STATUS_UNKNOWN: 'SIN INFORMACIÓN',
}

COLORS = {
    'primary': '#174A7E',
    'secondary': '#2E86DE',
    'deuda': '#D73027',
    'paz': '#1A9850',
    'sin_info': '#969696',
    'warning': '#E67E22',
    'background': '#F3F6F9',
    'border': '#CBD5E1',
    'text': '#263238',
}

TERRAIN_LAYER_ORDER = {
    'r_terreno': 0,
    'u_terreno': 1,
    'r_terreno_informal': 2,
    'u_terreno_informal': 3,
}


def _is_null(value):
    return value is None or value is NULL


def _text(value):
    return '' if _is_null(value) else str(value).strip()


def _valid_layer(layer):
    return layer is not None and layer.isValid() and isinstance(layer, QgsVectorLayer)


class JoinCanceled(Exception):
    """Cancelación solicitada desde la barra de progreso."""


class JoinedLayerTableModel(QAbstractTableModel):
    """Modelo liviano: no crea un widget por cada celda del resultado."""

    def __init__(self, features=None, fields=None, parent=None):
        super().__init__(parent)
        self._rows = [tuple(feature.attributes()) for feature in (features or [])]
        self._headers = [name for name, _type in (fields or [])]
        self._status_column = self.field_index('CART_ESTADO')

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        status = ''
        if 0 <= self._status_column < len(self._rows[index.row()]):
            status = _text(self._rows[index.row()][self._status_column])
        if role == Qt.BackgroundRole:
            if status == STATUS_LABELS[STATUS_DEBT]:
                return QColor('#FCE8E6')
            if status == STATUS_LABELS[STATUS_CLEAR]:
                return QColor('#E6F4EA')
            if status == STATUS_LABELS[STATUS_UNKNOWN]:
                return QColor('#F1F3F4')
            return None
        if role == Qt.ForegroundRole:
            if status == STATUS_LABELS[STATUS_DEBT]:
                return QColor('#9C1C16')
            if status == STATUS_LABELS[STATUS_CLEAR]:
                return QColor('#0B6B36')
            return None
        if role not in (Qt.DisplayRole, Qt.ToolTipRole):
            return None
        value = self._rows[index.row()][index.column()]
        return _text(value)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal and 0 <= section < len(self._headers):
            return self._headers[section]
        if orientation == Qt.Vertical:
            return section + 1
        return None

    def field_index(self, field_name):
        try:
            return self._headers.index(field_name)
        except ValueError:
            return -1

    def row_values(self, row):
        return self._rows[row] if 0 <= row < len(self._rows) else ()


class JoinedLayerFilterProxyModel(QSortFilterProxyModel):
    """Filtro combinado por texto y por un atributo sin duplicar la tabla."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._text = ''
        self._field = ''
        self._value = ''

    def set_criteria(self, text='', field_name='', value=''):
        self._text = _text(text).casefold()
        self._field = _text(field_name)
        self._value = _text(value).casefold()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        if model is None:
            return False
        row = model.row_values(source_row)
        if self._field:
            column = model.field_index(self._field)
            if column < 0 or column >= len(row):
                return False
            if _text(row[column]).casefold() != self._value:
                return False
        if self._text and not any(
            self._text in _text(value).casefold() for value in row
        ):
            return False
        return True


class FieldPickerDialog(QDialog):
    """Permite elegir los campos que forman el código predial de un origen.

    Se puede marcar UN campo (código completo en una sola columna) o VARIOS
    campos (el código está partido y se concatena en el orden marcado).
    """

    def __init__(self, parent, title, field_names, selected):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(420, 460)
        root = QVBoxLayout(self)
        info = QLabel(
            'Marca los campos que forman el código predial. Si el código está\n'
            'partido en varias columnas, márcalas en el orden a concatenar\n'
            '(los que se marcan primero se concatenan primero).'
        )
        info.setWordWrap(True)
        root.addWidget(info)
        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.MultiSelection)
        for name in field_names:
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if name in selected else Qt.Unchecked)
            self.list.addItem(item)
        root.addWidget(self.list, 1)
        btn_hint = QPushButton('⚡ Marcar campos con nombre de código (Numero Predial / FICHA / manzana / vereda…)')
        btn_hint.clicked.connect(self._mark_hints)
        root.addWidget(btn_hint)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self.selected = sorted(selected)

    def _mark_hints(self):
        for index in range(self.list.count()):
            item = self.list.item(index)
            item.setCheckState(Qt.Checked if is_code_segment_name(item.text()) else Qt.Unchecked)

    def accepted_selection(self):
        chosen = []
        for index in range(self.list.count()):
            item = self.list.item(index)
            if item.checkState() == Qt.Checked:
                chosen.append(item.text())
        return chosen


class GdbJoinWidget(QWidget):
    """Pestaña de cruce GDB + R1/R2 + cartera."""

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self._gdb_path = ''
        self._gdb_temps = []
        self._gdb_layers = []          # lista de QgsVectorLayer descubiertos
        self._vereda_lookup = {}       # código de vereda -> nombre (R_VEREDA)
        self._joined_layer = None      # capa temporal unificada
        self._last_fields = []
        self._table_model = None
        self._table_proxy = None
        self._last_status_counts = {}
        self._last_coverage = {}
        self._last_code_issues = []
        self._last_empty_code_counts = {}
        self._code_fields = {
            'gdb': [],
            'r1': [],
            'r2': [],
            'cartera': [],
        }
        self._build_ui()
        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(250)
        self._filter_timer.timeout.connect(self.apply_filter)
        self._connect_signals()
        self.destroyed.connect(self._cleanup_gdb_temps)

    # ------------------------------------------------------------------ UI
    def _app_icon(self):
        """Icono del semáforo para ventanas emergentes (progreso, diálogos)."""
        icon_path = Path(__file__).with_name('icon.png')
        return QIcon(str(icon_path)) if icon_path.is_file() else QIcon()

    def _button(self, text, color=None):
        button = QPushButton(text)
        bg = color or COLORS['primary']
        button.setMinimumHeight(34)
        button.setStyleSheet(
            f'QPushButton{{background:{bg};color:white;border:none;border-radius:5px;'
            f'padding:7px 12px;font-weight:bold;}}'
            f'QPushButton:hover{{background:{COLORS["secondary"]};}}'
            'QPushButton:pressed{padding-top:8px;padding-bottom:6px;}'
            'QPushButton:disabled{background:#B0BEC5;color:#ECEFF1;}'
        )
        return button

    def _group(self, title):
        group = QGroupBox(title)
        group.setStyleSheet(
            f'QGroupBox{{background:white;border:1px solid {COLORS["border"]};'
            'border-radius:7px;margin-top:10px;padding-top:10px;font-weight:bold;}'
            f'QGroupBox::title{{subcontrol-origin:margin;left:12px;padding:0 5px;'
            f'color:{COLORS["primary"]};}}'
        )
        return group

    def _build_ui(self):
        self.setStyleSheet(
            f'QWidget{{color:{COLORS["text"]};font-size:10pt;}}'
            f'QComboBox,QLineEdit{{background:white;border:1px solid {COLORS["border"]};'
            'border-radius:4px;padding:5px 8px;min-height:23px;}}'
            f'QComboBox:focus,QLineEdit:focus{{border:1px solid {COLORS["secondary"]};}}'
            f'QTableView{{background:white;alternate-background-color:#F7FAFC;'
            f'border:1px solid {COLORS["border"]};gridline-color:#E2E8F0;}}'
            f'QHeaderView::section{{background:#EAF2F8;color:{COLORS["primary"]};'
            'border:0;border-right:1px solid #D5E2EC;border-bottom:1px solid #C7D7E3;'
            'padding:7px;font-weight:bold;}}'
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 10)
        root.setSpacing(9)

        header = QHBoxLayout()
        header.setSpacing(10)
        logo_path = Path(__file__).with_name('logo_semaforo_cartera.png')
        if logo_path.exists():
            logo_label = QLabel()
            logo_pixmap = QPixmap(str(logo_path))
            logo_label.setPixmap(
                logo_pixmap.scaledToHeight(73, Qt.SmoothTransformation)
            )
            header.addWidget(logo_label, 0)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel('🚦  SEMÁFORO DE CARTERA PREDIAL')
        title.setStyleSheet(
            f'background:{COLORS["primary"]};color:white;border-radius:7px;'
            'padding:11px 14px;font-size:14pt;font-weight:bold;'
        )
        subtitle = QLabel(
            'Integra automáticamente los cuatro terrenos, R1, R2 y cartera en una sola capa.'
        )
        subtitle.setStyleSheet('color:#526472;padding:0 4px 2px 4px;')
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        header.addLayout(title_col, 1)
        header.setAlignment(title_col, Qt.AlignVCenter)
        root.addLayout(header)

        # -- Orígenes de datos -------------------------------------------
        sources = self._group('Orígenes de datos')
        grid = QGridLayout(sources)
        grid.setContentsMargins(10, 14, 10, 10)
        self.btn_load_gdb = self._button('📦 Cargar GDB comprimida (.zip)…', COLORS['primary'])
        self.btn_load_gdb_folder = self._button('📂 Usar carpeta .gdb…', COLORS['secondary'])
        self.lbl_gdb = QLabel('Sin Geodatabase cargada.')
        self.cbo_gdb_layer = QComboBox()
        self.cbo_gdb_layer.addItem('Se creará al procesar los cuatro terrenos…')
        self.cbo_gdb_layer.setEnabled(False)
        self.cbo_gdb_layer.setToolTip(
            'Muestra únicamente la capa resultante de la unión espacial y alfanumérica.'
        )
        self.btn_load_r1 = self._button('📂 Cargar R1…', COLORS['secondary'])
        self.lbl_r1 = QLabel('Sin R1 cargado.')
        self.cbo_r1_table = QComboBox()
        self.btn_load_r2 = self._button('📂 Cargar R2…', COLORS['secondary'])
        self.lbl_r2 = QLabel('Sin R2 cargado.')
        self.cbo_r2_table = QComboBox()
        self.btn_load_cartera = self._button('📂 Cargar cartera…', COLORS['deuda'])
        self.lbl_cartera = QLabel('Sin reporte de cartera cargado.')
        self.cbo_cartera_table = QComboBox()
        for button in (
            self.btn_load_gdb, self.btn_load_gdb_folder,
            self.btn_load_r1, self.btn_load_r2, self.btn_load_cartera,
        ):
            button.setMinimumWidth(145)
        for combo in (
            self.cbo_gdb_layer, self.cbo_r1_table,
            self.cbo_r2_table, self.cbo_cartera_table,
        ):
            combo.setMinimumWidth(240)

        def source_row(button, status, combo=None, secondary=None):
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(8)
            row.addWidget(button)
            if secondary is not None:
                row.addWidget(secondary)
            row.addWidget(status, 2)
            if combo is not None:
                sheet_label = QLabel('Hoja:')
                sheet_label.setStyleSheet('color:#607D8B;font-weight:bold;')
                row.addWidget(sheet_label)
                row.addWidget(combo, 2)
            return row

        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        grid.setColumnMinimumWidth(0, 155)
        grid.setColumnStretch(1, 1)
        grid.addWidget(QLabel('Geodatabase'), 0, 0)
        grid.addLayout(
            source_row(
                self.btn_load_gdb, self.lbl_gdb,
                secondary=self.btn_load_gdb_folder,
            ),
            0, 1,
        )
        grid.addWidget(QLabel('Capa unificada resultante'), 1, 0)
        grid.addWidget(self.cbo_gdb_layer, 1, 1)
        grid.addWidget(QLabel('Registro R1'), 2, 0)
        grid.addLayout(source_row(self.btn_load_r1, self.lbl_r1, self.cbo_r1_table), 2, 1)
        grid.addWidget(QLabel('Registro R2'), 3, 0)
        grid.addLayout(source_row(self.btn_load_r2, self.lbl_r2, self.cbo_r2_table), 3, 1)
        grid.addWidget(QLabel('Reporte de cartera'), 4, 0)
        grid.addLayout(
            source_row(self.btn_load_cartera, self.lbl_cartera, self.cbo_cartera_table),
            4, 1,
        )
        root.addWidget(sources)

        # -- Campos de código predial (uno o varios concatenados) --------
        keys = self._group('Cruce por código predial (uno o varios campos concatenados)')
        kgrid = QGridLayout(keys)
        kgrid.setContentsMargins(10, 14, 10, 10)
        self.btn_pick_gdb = self._button('🛠 Código en capa GDB…', COLORS['secondary'])
        self.lbl_pick_gdb = QLabel('—')
        self.btn_pick_r1 = self._button('🛠 Código en R1…', COLORS['secondary'])
        self.lbl_pick_r1 = QLabel('—')
        self.btn_pick_r2 = self._button('🛠 Código en R2…', COLORS['secondary'])
        self.lbl_pick_r2 = QLabel('—')
        self.btn_pick_cartera = self._button('🛠 Código en cartera…', COLORS['secondary'])
        self.lbl_pick_cartera = QLabel('—')
        for button in (
            self.btn_pick_gdb, self.btn_pick_r1,
            self.btn_pick_r2, self.btn_pick_cartera,
        ):
            button.setMinimumWidth(205)

        def key_row(button, label):
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(8)
            row.addWidget(button)
            label.setStyleSheet(
                'background:#F7FAFC;border:1px solid #E2E8F0;'
                'border-radius:4px;padding:6px;color:#334E68;'
            )
            row.addWidget(label, 1)
            return row

        kgrid.setHorizontalSpacing(14)
        kgrid.setVerticalSpacing(8)
        kgrid.setColumnStretch(0, 1)
        kgrid.setColumnStretch(1, 1)
        kgrid.addLayout(key_row(self.btn_pick_gdb, self.lbl_pick_gdb), 0, 0)
        kgrid.addLayout(key_row(self.btn_pick_r1, self.lbl_pick_r1), 0, 1)
        kgrid.addLayout(key_row(self.btn_pick_r2, self.lbl_pick_r2), 1, 0)
        kgrid.addLayout(key_row(self.btn_pick_cartera, self.lbl_pick_cartera), 1, 1)
        root.addWidget(keys)

        action_group = self._group('Procesamiento y herramientas')
        actions = QGridLayout(action_group)
        actions.setContentsMargins(10, 14, 10, 10)
        actions.setHorizontalSpacing(8)
        self.btn_join = self._button('🚦 Crear capa unificada y semáforo', COLORS['paz'])
        self.btn_join.setToolTip('Integra GDB, R1, R2 y cartera por el número predial.')
        self.btn_sql = self._button('🗄 Consulta SQL…', COLORS['secondary'])
        self.btn_export = self._button('📊 Exportar resultado…', COLORS['primary'])
        self.btn_export.setToolTip(
            'Crea el resumen ejecutivo, las tablas automáticas y el balance '
            'financiero filtrable por vereda y clasificación.'
        )
        self.btn_export.setEnabled(False)
        self.btn_add_all_gdb = self._button(
            '➕ Añadir 4 terrenos originales', COLORS['secondary']
        )
        for column, button in enumerate((
            self.btn_join, self.btn_sql, self.btn_export, self.btn_add_all_gdb,
        )):
            actions.addWidget(button, 0, column)
            actions.setColumnStretch(column, 1)
        root.addWidget(action_group)

        self.lbl_summary = QLabel(
            'Carga 1) la GDB, 2) R1 y R2, y 3) la cartera. El plugin creará una '
            'sola capa espacial con el semáforo.'
        )
        self.lbl_summary.setStyleSheet(
            f'background:white;border:1px solid {COLORS["border"]};'
            'border-radius:4px;padding:6px;font-weight:bold;'
        )
        self.lbl_summary.setWordWrap(True)
        result_group = self._group('Resultado y filtros')
        result_layout = QVBoxLayout(result_group)
        result_layout.setContentsMargins(10, 14, 10, 10)
        result_layout.setSpacing(8)
        class_buttons = QHBoxLayout()
        class_buttons.setContentsMargins(0, 0, 0, 0)
        class_buttons.setSpacing(8)
        self.btn_class_all = self._button('📋 Todos: 0', COLORS['primary'])
        self.btn_class_debt = self._button('🔴 En deuda: 0', COLORS['deuda'])
        self.btn_class_clear = self._button('🟢 Paz y salvo: 0', COLORS['paz'])
        self.btn_invalid_codes = self._button(
            '⚠ Códigos ilegibles: 0', COLORS['warning']
        )
        self.btn_class_unlocated = self._button(
            '📍 Sin geometría: 0', COLORS['warning']
        )
        self.btn_class_all.setToolTip(
            'Muestra todos los registros y recupera la vista completa del mapa.'
        )
        self.btn_class_debt.setToolTip(
            'Filtra los deudores, los selecciona y acerca sus polígonos en el mapa.'
        )
        self.btn_class_clear.setToolTip(
            'Filtra los predios a paz y salvo, los selecciona y acerca el mapa.'
        )
        self.btn_invalid_codes.setToolTip(
            'Genera un Excel con los códigos no vacíos que no cumplen el formato predial.'
        )
        self.btn_class_unlocated.setToolTip(
            'Muestra deudores conservados en la tabla que no tienen polígono en la GDB.'
        )
        self._classification_buttons = (
            self.btn_class_all, self.btn_class_debt, self.btn_class_clear,
            self.btn_invalid_codes, self.btn_class_unlocated,
        )
        for button in self._classification_buttons:
            button.setEnabled(False)
            class_buttons.addWidget(button, 1)
        filt = QHBoxLayout()
        filt.setContentsMargins(0, 0, 0, 0)
        filt.setSpacing(8)
        self.cbo_filter = QComboBox()
        self.cbo_filter.addItem('Todos los registros', ('', ''))
        self.cbo_filter.addItem('🔴 En deuda', ('CART_ESTADO', 'EN DEUDA'))
        self.cbo_filter.addItem('🟢 Paz y salvo', ('CART_ESTADO', 'PAZ Y SALVO'))
        self.cbo_filter.addItem('⚪ Sin geometría', ('PRED_LOCALIZADO', 'NO'))
        self.cbo_filter.addItem('Rural formal', ('PRED_CLASE', 'RURAL FORMAL'))
        self.cbo_filter.addItem('Urbano formal', ('PRED_CLASE', 'URBANO FORMAL'))
        self.cbo_filter.addItem('Rural informal', ('PRED_CLASE', 'RURAL INFORMAL'))
        self.cbo_filter.addItem('Urbano informal', ('PRED_CLASE', 'URBANO INFORMAL'))
        self.inp_filter = QLineEdit()
        self.inp_filter.setPlaceholderText('Filtrar por código predial, nombre, valor…')
        self.cbo_filter.setMinimumWidth(210)
        self.inp_filter.setMinimumWidth(360)
        result_layout.addWidget(self.lbl_summary)
        result_layout.addLayout(class_buttons)
        filter_label = QLabel('Vista rápida:')
        filter_label.setStyleSheet('font-weight:bold;color:#526472;')
        filt.addWidget(filter_label)
        filt.addWidget(self.cbo_filter)
        search_label = QLabel('Buscar:')
        search_label.setStyleSheet('font-weight:bold;color:#526472;')
        filt.addWidget(search_label)
        filt.addWidget(self.inp_filter, 1)
        result_layout.addLayout(filt)
        root.addWidget(result_group)

        self.table = QTableView()
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        root.addWidget(self.table, 1)

        footer = QHBoxLayout()
        footer.setContentsMargins(2, 0, 0, 0)
        footer.setSpacing(8)
        self.lbl_status = QLabel('Listo.')
        self.lbl_status.setStyleSheet('color:#526472;padding:4px;')
        self.btn_zoom_all = self._button('🔍 Ver capa completa', COLORS['secondary'])
        self.btn_zoom_all.setEnabled(False)
        self.btn_clear = self._button('Limpiar', COLORS['sin_info'])
        footer.addWidget(self.lbl_status, 1)
        footer.addWidget(self.btn_zoom_all)
        footer.addWidget(self.btn_clear)
        root.addLayout(footer)

    def _connect_signals(self):
        self.btn_load_gdb.clicked.connect(self.load_gdb)
        self.btn_load_gdb_folder.clicked.connect(self.load_gdb_folder)
        self.btn_load_r1.clicked.connect(lambda: self.load_report('r1'))
        self.btn_load_r2.clicked.connect(lambda: self.load_report('r2'))
        self.btn_load_cartera.clicked.connect(lambda: self.load_report('cartera'))
        self.cbo_r1_table.currentIndexChanged.connect(self._refresh_r_fields)
        self.cbo_r2_table.currentIndexChanged.connect(self._refresh_r_fields)
        self.cbo_cartera_table.currentIndexChanged.connect(self._refresh_r_fields)
        self.btn_pick_gdb.clicked.connect(lambda: self.pick_code_fields('gdb'))
        self.btn_pick_r1.clicked.connect(lambda: self.pick_code_fields('r1'))
        self.btn_pick_r2.clicked.connect(lambda: self.pick_code_fields('r2'))
        self.btn_pick_cartera.clicked.connect(lambda: self.pick_code_fields('cartera'))
        self.btn_join.clicked.connect(self.run_join)
        self.btn_add_all_gdb.clicked.connect(self.add_all_gdb_layers)
        self.btn_sql.clicked.connect(self.open_sql)
        self.btn_export.clicked.connect(self.export_result)
        self.btn_zoom_all.clicked.connect(self.zoom_full_layer)
        self.btn_class_all.clicked.connect(
            lambda: self.set_classification_filter('', '')
        )
        self.btn_class_debt.clicked.connect(
            lambda: self.set_classification_filter('CART_ESTADO', 'EN DEUDA')
        )
        self.btn_class_clear.clicked.connect(
            lambda: self.set_classification_filter('CART_ESTADO', 'PAZ Y SALVO')
        )
        self.btn_invalid_codes.clicked.connect(self.export_invalid_codes)
        self.btn_class_unlocated.clicked.connect(
            lambda: self.set_classification_filter('PRED_LOCALIZADO', 'NO')
        )
        self.btn_clear.clicked.connect(self.clear_result)
        self.inp_filter.textChanged.connect(self._schedule_filter)
        self.cbo_filter.currentIndexChanged.connect(self._schedule_filter)

    # ------------------------------------------------------------- helpers
    def _string_option(self, path):
        if Path(path).suffix.lower() in ('.xlsx', '.xls', '.ods'):
            return '|option:FIELD_TYPES=STRING'
        return ''

    def _auto_code_fields(self, field_names):
        """Campos candidatos a código predial: un campo con nombre de clave, o
        varios campos cuyo nombre sugiere un segmento del código."""
        singles = []
        for hint in KEY_HINTS:
            for name in field_names:
                normalized = name.casefold().replace(' ', '_')
                if hint == normalized or hint in normalized:
                    if name not in singles:
                        singles.append(name)
        if singles:
            return singles[:1]  # se prefiere UN campo de código completo
        segments = [name for name in field_names if is_code_segment_name(name)]
        return segments

    def _set_pick_label(self, which):
        names = self._code_fields[which]
        label = {
            'gdb': self.lbl_pick_gdb,
            'r1': self.lbl_pick_r1,
            'r2': self.lbl_pick_r2,
            'cartera': self.lbl_pick_cartera,
        }[which]
        if not names:
            label.setText('— (pulsa para elegir)')
            label.setStyleSheet('color:#D73027;font-weight:bold;')
        else:
            label.setText(' + '.join(names))
            label.setStyleSheet('color:#174A7E;font-weight:bold;')

    def pick_code_fields(self, which):
        layer = self._code_source_layer(which)
        names = []
        if _valid_layer(layer):
            names = [f.name() for f in layer.fields()]
        elif which == 'gdb':
            names = [f.name() for f in (self._gdb_layer().fields() if self._gdb_layer() else [])]
        if not names:
            QMessageBox.information(self, 'Sin campos', 'Carga primero la fuente correspondiente.')
            return
        current = list(self._code_fields[which])
        if not current:
            current = self._auto_code_fields(names)
        dialog = FieldPickerDialog(self, f'Campo(s) de código predial — {which.upper()}', names, current)
        if dialog.exec_() == QDialog.Accepted:
            self._code_fields[which] = dialog.accepted_selection()
            self._set_pick_label(which)
            self.lbl_status.setText(
                f'Código {which.upper()}: {", ".join(self._code_fields[which]) or "no definido"}.'
            )

    def _code_source_layer(self, which):
        if which in ('r1', 'r2', 'cartera'):
            return self._report_layer(which)
        return self._gdb_layer()

    # ------------------------------------------------------------ load GDB
    def load_gdb(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            'Seleccionar la Geodatabase comprimida',
            '',
            'Geodatabase comprimida (*.gdb.zip *.zip);;Todos los archivos (*)',
        )
        if not path:
            return
        temporary = TemporaryDirectory(prefix='semaforo_cartera_gdb_')
        try:
            with ZipFile(path) as archive:
                for member in archive.infolist():
                    member_path = Path(member.filename)
                    if member_path.is_absolute() or '..' in member_path.parts:
                        raise ValueError('El ZIP contiene una ruta no segura.')
                archive.extractall(temporary.name)
            geodatabases = sorted(
                item for item in Path(temporary.name).rglob('*')
                if item.is_dir() and item.name.lower().endswith('.gdb')
            )
            if not geodatabases:
                raise ValueError('El ZIP no contiene una carpeta terminada en .gdb.')
            self._gdb_temps.append(temporary)
            self._load_gdb_path(str(geodatabases[0]), Path(path).name)
        except (BadZipFile, OSError, ValueError) as error:
            temporary.cleanup()
            QMessageBox.critical(self, 'No se pudo abrir la GDB', str(error))

    def load_gdb_folder(self):
        path = QFileDialog.getExistingDirectory(self, 'Seleccionar la carpeta .gdb')
        if not path:
            return
        if not Path(path).name.lower().endswith('.gdb'):
            QMessageBox.warning(self, 'Carpeta inválida', 'La carpeta debe terminar en “.gdb”.')
            return
        self._load_gdb_path(path, Path(path).name)

    def _load_gdb_path(self, path, display_name):
        self._gdb_path = path
        self._code_fields['gdb'] = []
        try:
            details = QgsProviderRegistry.instance().providerMetadata('ogr').querySublayers(path)
        except (AttributeError, RuntimeError):
            details = []
        self._gdb_layers = []
        self.cbo_gdb_layer.blockSignals(True)
        self.cbo_gdb_layer.clear()
        self.cbo_gdb_layer.addItem('Se creará al procesar los cuatro terrenos…')
        self.cbo_gdb_layer.setEnabled(False)
        for detail in details:
            uri = detail.uri()
            name = detail.name()
            normalized_name = normalize_words(name).replace(' ', '_')
            if normalized_name not in TERRAIN_LAYER_ORDER:
                continue
            layer = QgsVectorLayer(uri, name, 'ogr')
            if not layer.isValid() or not layer.isSpatial():
                continue
            self._gdb_layers.append(layer)
        self.cbo_gdb_layer.blockSignals(False)
        self._vereda_lookup = self._build_vereda_lookup(details)
        parcels = self._parcel_gdb_layers()
        total = sum(max(0, layer.featureCount()) for layer in parcels)
        self.lbl_gdb.setText(
            f'{display_name}: {len(parcels)} terrenos · {total:,} polígonos'
        )
        self._refresh_gdb_fields()
        veredas_msg = (
            f' · {len(set(self._vereda_lookup.values()))} nombres de vereda'
            if self._vereda_lookup else ''
        )
        detected, ratio = self._sample_gdb_municipality(parcels)
        if detected and not municipality_matches_license(detected):
            # Aviso temprano; el bloqueo real ocurre al crear la capa unificada.
            self.lbl_gdb.setText(
                f'{display_name}: municipio {detected} — NO habilitado'
            )
            self.lbl_status.setText(
                f'⛔ GDB del municipio {detected}. El aplicativo solo procesa '
                f'{LICENSED_MUNICIPALITY_NAME} ({LICENSED_MUNICIPALITY_CODE}).'
            )
            QMessageBox.warning(
                self, 'Municipio no habilitado',
                'Esta Geodatabase corresponde al municipio '
                f'{detected}, y el aplicativo está habilitado únicamente para '
                f'{LICENSED_MUNICIPALITY_NAME}, código catastral '
                f'{LICENSED_MUNICIPALITY_CODE}.\n\n'
                'Podrás revisar las capas, pero el cruce y la exportación se '
                'detendrán.',
            )
            return
        self.lbl_status.setText(
            f'GDB lista: solo {len(parcels)} capas de terreno '
            f'({total:,} polígonos){veredas_msg}.'
        )

    def _sample_gdb_municipality(self, parcels, limit=600):
        """Municipio predominante en una muestra de los terrenos de la GDB.

        Da un aviso temprano de habilitación sin recorrer toda la GDB; el
        control definitivo se hace sobre todos los códigos al crear la capa.
        """
        counter = {}
        collected = 0
        for layer in parcels:
            names = [field.name() for field in layer.fields()]
            code_names = self._code_fields.get('gdb') or self._auto_code_fields(names)
            indexes = [names.index(name) for name in code_names if name in names]
            if not indexes:
                continue
            for feature in layer.getFeatures():
                attributes = feature.attributes()
                for index in indexes:
                    if index < len(attributes):
                        municipality = municipality_of_code(attributes[index])
                        if municipality:
                            counter[municipality] = counter.get(municipality, 0) + 1
                            break
                collected += 1
                if collected >= limit:
                    break
            if collected >= limit:
                break
        if not counter:
            return '', 0.0
        total = sum(counter.values())
        code = max(counter, key=counter.get)
        return code, counter[code] / total

    def _build_vereda_lookup(self, details):
        """Diccionario ``código de vereda -> nombre`` tomado de la GDB.

        El nombre de la vereda no existe en las capas de terreno: vive en una
        capa aparte (típicamente ``R_VEREDA`` con campos ``CODIGO`` y
        ``NOMBRE``). Se detecta por el nombre de la capa y de sus campos, sin
        depender de un esquema fijo; si no aparece, el análisis sigue mostrando
        el código de la vereda.
        """
        lookup = {}
        for detail in details:
            normalized = normalize_words(detail.name()).replace(' ', '_')
            if 'vereda' not in normalized or 'terreno' in normalized:
                continue
            layer = QgsVectorLayer(detail.uri(), detail.name(), 'ogr')
            if not layer.isValid():
                continue
            names = [field.name() for field in layer.fields()]
            code_pos = self._find_field_index(names, ('codigo', 'cod_vereda'))
            name_pos = self._find_field_index(
                names, ('nombre', 'nom_vereda', 'vereda'),
            )
            if code_pos is None or name_pos is None:
                continue
            code_field, name_field = names[code_pos], names[name_pos]
            for feature in layer.getFeatures():
                code = _text(feature[code_field])
                label = _text(feature[name_field])
                if not code or not label:
                    continue
                lookup[code] = label
                for variant in key_variants(code):
                    lookup.setdefault(variant, label)
            if lookup:
                break
        return lookup

    def _vereda_name_for(self, code):
        """Nombre de la vereda para un código, tolerante a texto/número."""
        if not self._vereda_lookup:
            return ''
        text = _text(code)
        if not text or text.upper() == 'NULL':
            return ''
        if text in self._vereda_lookup:
            return self._vereda_lookup[text]
        for variant in key_variants(text):
            if variant in self._vereda_lookup:
                return self._vereda_lookup[variant]
        return ''

    def _cleanup_gdb_temps(self, *_):
        for temporary in self._gdb_temps:
            try:
                temporary.cleanup()
            except OSError:
                pass
        self._gdb_temps = []

    def _parcel_gdb_layers(self):
        """Capas que representan predios: rural, urbano, formal e informal."""
        layers = [
            layer for layer in self._gdb_layers
            if 'terreno' in normalize_words(layer.name())
        ]
        return sorted(
            layers,
            key=lambda layer: (
                TERRAIN_LAYER_ORDER.get(
                    normalize_words(layer.name()).replace(' ', '_'), 99,
                ),
                normalize_words(layer.name()),
            ),
        )

    def add_all_gdb_layers(self):
        if not self._gdb_layers:
            QMessageBox.information(self, 'Sin Geodatabase', 'Primero carga una Geodatabase.')
            return
        for layer in self._gdb_layers:
            if not QgsProject.instance().mapLayersByName(layer.name()):
                QgsProject.instance().addMapLayer(layer)
        self.lbl_status.setText(
            f'{len(self._gdb_layers)} capas originales de terreno añadidas al proyecto.'
        )

    def _gdb_layer(self):
        parcels = self._parcel_gdb_layers()
        return parcels[0] if parcels else None

    def _refresh_gdb_fields(self, *_):
        layer = self._gdb_layer()
        if _valid_layer(layer):
            names = [f.name() for f in layer.fields()]
            if not self._code_fields['gdb'] or any(
                name not in names for name in self._code_fields['gdb']
            ):
                self._code_fields['gdb'] = self._auto_code_fields(names)
                self._set_pick_label('gdb')

    # ---------------------------------------------------------- load R1/R2
    def load_report(self, which):
        path, _ = QFileDialog.getOpenFileName(
            self,
            f'Cargar reporte {which.upper()}',
            '',
            'Reportes (*.xlsx *.xls *.csv *.ods);;Todos los archivos (*)',
        )
        if not path:
            return
        self._code_fields[which] = []
        name = Path(path).stem
        uri = path
        option = self._string_option(path)
        try:
            details = QgsProviderRegistry.instance().providerMetadata('ogr').querySublayers(path)
        except (AttributeError, RuntimeError):
            details = []
        combo = {
            'r1': self.cbo_r1_table,
            'r2': self.cbo_r2_table,
            'cartera': self.cbo_cartera_table,
        }[which]
        label = {
            'r1': self.lbl_r1,
            'r2': self.lbl_r2,
            'cartera': self.lbl_cartera,
        }[which]
        combo.blockSignals(True)
        combo.clear()
        if len(details) > 1:
            for index, detail in enumerate(details):
                combo.addItem(detail.name() or f'Hoja {index + 1}', detail.uri() + option)
        elif details:
            combo.addItem(details[0].name() or name, details[0].uri() + option)
        else:
            combo.addItem(name, uri + option)
        combo.blockSignals(False)
        label.setText(f'{Path(path).name} ({max(1, combo.count())} hoja(s))')
        self._refresh_r_fields()
        self.lbl_status.setText(f'Reporte {which.upper()} cargado: {Path(path).name}.')

    def _report_layer(self, which):
        combo = {
            'r1': self.cbo_r1_table,
            'r2': self.cbo_r2_table,
            'cartera': self.cbo_cartera_table,
        }[which]
        uri = combo.currentData()
        if not uri:
            return None
        layer = QgsVectorLayer(uri, combo.currentText(), 'ogr')
        return layer if _valid_layer(layer) else None

    def _refresh_r_fields(self, *_):
        for which in ('r1', 'r2', 'cartera'):
            layer = self._report_layer(which)
            if _valid_layer(layer):
                names = [f.name() for f in layer.fields()]
                if not self._code_fields[which] or any(
                    name not in names for name in self._code_fields[which]
                ):
                    self._code_fields[which] = self._auto_code_fields(names)
                    self._set_pick_label(which)

    # --------------------------------------------------------------- join
    def run_join(self):
        gdb_sources = self._parcel_gdb_layers()
        if not gdb_sources:
            QMessageBox.information(
                self, 'Sin terrenos',
                'La GDB debe contener R_TERRENO, U_TERRENO y/o sus capas informales.',
            )
            return

        r1_layer = self._report_layer('r1')
        r2_layer = self._report_layer('r2')
        cartera_layer = self._report_layer('cartera')
        missing = [
            label for label, layer in (
                ('R1', r1_layer), ('R2', r2_layer), ('cartera', cartera_layer),
            )
            if not _valid_layer(layer)
        ]
        if missing:
            QMessageBox.information(
                self, 'Faltan insumos',
                f'Carga primero: {", ".join(missing)}.'
            )
            return

        progress = QProgressDialog('Preparando el join…', 'Cancelar', 0, 0, self)
        progress.setWindowTitle('GDB + R1 + R2 + cartera')
        progress.setWindowIcon(self._app_icon())
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        try:
            result = self._perform_full_join(
                gdb_sources, r1_layer, r2_layer, cartera_layer, progress,
            )
        except JoinCanceled:
            progress.close()
            self.lbl_status.setText('Proceso cancelado.')
            return
        except Exception as error:
            progress.close()
            QMessageBox.critical(self, 'Error en el join', str(error))
            return
        progress.close()
        if result is None:
            self.lbl_status.setText('Join cancelado.')
            return
        (
            layer, features, fields, join_stats, status_counts, coverage,
            validation,
        ) = result
        previous_layer = self._joined_layer
        self._joined_layer = layer
        if (
            previous_layer is not None and previous_layer.isValid()
            and previous_layer.id() != layer.id()
        ):
            QgsProject.instance().removeMapLayer(previous_layer.id())
        self.cbo_gdb_layer.blockSignals(True)
        self.cbo_gdb_layer.clear()
        self.cbo_gdb_layer.addItem(
            f'{layer.name()} — {coverage["located"]:,} polígonos', layer.id(),
        )
        self.cbo_gdb_layer.setEnabled(True)
        self.cbo_gdb_layer.blockSignals(False)
        self._last_fields = fields
        self._last_status_counts = status_counts
        self._last_coverage = coverage
        self._last_code_issues = validation['issues']
        self._last_empty_code_counts = validation['empty_counts']
        self.btn_export.setEnabled(True)
        self.btn_zoom_all.setEnabled(True)
        self._update_classification_buttons(
            len(features), status_counts, coverage,
            len(validation['issues']),
        )
        self._populate_table(features, fields)
        detail = ' · '.join(
            f'{item["source"]}: {item["matched"]:,} por {item["left_key"]} ↔ {item["right_key"]}'
            if item['matched'] else f'{item["source"]}: sin coincidencias'
            for item in join_stats
        )
        summary = (
            f'Capa lista: {len(features):,} registros · '
            f'{coverage["located"]:,} predios con geometría · '
            f'{status_counts.get(STATUS_DEBT, 0):,} en deuda '
            f'({coverage["located_debt"]:,} localizados + '
            f'{coverage["unlocated_debt"]:,} sin geometría) · '
            f'{status_counts.get(STATUS_CLEAR, 0):,} paz y salvo · '
            f'{len(validation["issues"]):,} códigos ilegibles reportables · '
            f'{validation["empty_total"]:,} códigos vacíos omitidos'
        )
        class_detail = ' · '.join(
            f'{name.lower()}: {count:,}'
            for name, count in coverage['classes'].items()
        )
        full_summary = f'{summary}\nPolígonos incluidos: {class_detail}'
        self.lbl_summary.setText(full_summary)
        self.lbl_summary.setToolTip(f'{full_summary} · {detail}')
        self.lbl_status.setText(
            f'Semáforo verificado: {coverage["located"]:,} polígonos y '
            f'{coverage["unlocated"]:,} registros de cartera sin geometría.'
        )
        self.iface.setActiveLayer(layer)
        self.zoom_full_layer()

    def _code_names(self, which):
        return list(self._code_fields.get(which, []))

    @staticmethod
    def _heartbeat(progress):
        QApplication.processEvents()
        if progress.wasCanceled():
            raise JoinCanceled()

    def _build_source_bundle(self, layer, prefix, origin, progress=None, label=None):
        """Lee una capa y devuelve (fields_prefixed, rows_prefixed, code_index_fields).

        ``prefix`` se antepone a cada campo para evitar colisiones en el esquema
        unificado. ``origin`` es 'gdb', 'r1' o 'r2' y determina qué campos de
        código predial usar (el código puede estar en uno o varios campos).
        """
        fields = [f.name() for f in layer.fields()]
        # Los nombres usados en el esquema y en las filas deben ser idénticos.
        # Normalizar aquí evita perder valores cuando QGIS reemplaza espacios.
        prefixed = [f'{prefix}{name}'.replace(' ', '_') for name in fields]
        code = self._code_names(origin)
        code_indexes = [fields.index(c) for c in code if c in fields]
        rows = []
        geometry = [] if layer.isSpatial() else None
        for processed, feature in enumerate(layer.getFeatures(), 1):
            rows.append([feature[f] for f in fields])
            if geometry is not None:
                geometry.append(feature.geometry())
            if progress is not None and processed % 500 == 0:
                progress.setLabelText(
                    f'Leyendo {label or layer.name()}… ({processed:,} filas)'
                )
                self._heartbeat(progress)
        return {
            'fields': prefixed,
            'code_indexes': code_indexes,
            'rows': rows,
            'geometry': geometry,
            'source': origin,
        }

    def _build_gdb_reference_bundle(self, gdb_sources, progress=None):
        """Apila las capas de terreno; cada entidad conserva su geometría."""
        sources = []
        geometries = []
        for layer in gdb_sources:
            bundle = self._build_source_bundle(
                layer, 'GDB_', 'gdb', progress, layer.name(),
            )
            sources.append((layer.name(), bundle['fields'], bundle['rows']))
            geometries.extend(bundle['geometry'] or [])
        fields, rows = stack_attribute_sources(sources)
        source_index = fields.index('GDB_CAPA_ORIGEN')
        # Nombre de la vereda: no viene en el terreno, se cruza con R_VEREDA.
        vereda_code_index = next(
            (fields.index(name) for name in (
                'GDB_VEREDA_CODIGO', 'GDB_CODIGO_VEREDA', 'GDB_VEREDA',
            ) if name in fields),
            None,
        )
        fields.append('GDB_VEREDA_NOMBRE')
        for row in rows:
            code = row[vereda_code_index] if vereda_code_index is not None else None
            row.append(self._vereda_name_for(code))
        fields.extend([
            'PRED_AMBITO', 'PRED_FORMALIDAD', 'PRED_CLASE', 'PRED_LOCALIZADO',
        ])
        for row in rows:
            area, formality, class_name = classify_terrain_source(row[source_index])
            row.extend([area, formality, class_name, 'SI'])
        preferred_names = {
            f'GDB_{name}'.replace(' ', '_') for name in self._code_names('gdb')
        }
        preferred = [
            index for index, name in enumerate(fields) if name in preferred_names
        ]
        if not preferred:
            detected = self._auto_code_fields(fields)
            preferred = [fields.index(name) for name in detected if name in fields]
        return {
            'fields': fields,
            'code_indexes': preferred,
            'rows': rows,
            'geometry': geometries,
            'source': 'gdb',
        }

    @staticmethod
    def _validate_bundle_codes(bundle, source_label):
        """Retira llaves vacías/ilegibles y conserva las ilegibles para reporte."""
        columns = bundle.get('code_indexes') or []
        if not columns:
            raise RuntimeError(
                f'No se identificó el campo de código predial en {source_label}. '
                'Selecciónalo con el botón “Código…” e intenta nuevamente.'
            )
        rows = bundle.get('rows') or []
        valid, empty, invalid = partition_predial_rows(rows, columns)
        code_fields = ', '.join(
            bundle['fields'][column]
            for column in columns if column < len(bundle['fields'])
        )
        origin_index = (
            bundle['fields'].index('GDB_CAPA_ORIGEN')
            if 'GDB_CAPA_ORIGEN' in bundle['fields'] else -1
        )
        issues = []
        for issue in invalid:
            row_index = issue['row_index']
            origin = source_label
            if origin_index >= 0 and row_index < len(rows):
                origin = _text(rows[row_index][origin_index]) or source_label
            issues.append({
                'source': origin,
                'row': row_index + 1,
                'fields': code_fields,
                'raw': issue['raw'],
                'normalized': issue['normalized'],
                'reason': issue['reason'],
            })

        bundle['rows'] = [rows[index] for index in valid]
        geometry = bundle.get('geometry')
        if geometry is not None:
            bundle['geometry'] = [geometry[index] for index in valid]
        return issues, len(empty)

    @staticmethod
    def _append_unlocated_cartera_rows(
        merged_fields, merged_rows, ref_bundle, cartera_bundle, cartera_match,
        cartera_offset,
    ):
        """Conserva en la misma capa los deudores que no tienen geometría GDB."""
        groups = unmatched_right_groups(cartera_match, cartera_bundle['rows'])
        if not groups:
            return 0
        positions = {name: index for index, name in enumerate(merged_fields)}
        for group in groups:
            row = [None] * len(merged_fields)
            ordered = sorted(group)
            for column in range(len(cartera_bundle['fields'])):
                row[cartera_offset + column] = collapse_join_values(
                    cartera_bundle['rows'], ordered, column,
                )
            for left_column, right_column in zip(
                cartera_match['left_columns'], cartera_match['right_columns'],
            ):
                row[left_column] = collapse_join_values(
                    cartera_bundle['rows'], ordered, right_column,
                )
            if 'GDB_CAPA_ORIGEN' in positions:
                row[positions['GDB_CAPA_ORIGEN']] = 'CARTERA_SIN_GEOMETRIA'
            if 'GDB_CODIGO' in positions and not row[positions['GDB_CODIGO']]:
                right_key = cartera_match['right_columns'][0]
                row[positions['GDB_CODIGO']] = collapse_join_values(
                    cartera_bundle['rows'], ordered, right_key,
                )
            classifications = {
                'PRED_AMBITO': 'NO DETERMINADO',
                'PRED_FORMALIDAD': 'NO DETERMINADA',
                'PRED_CLASE': 'CARTERA SIN GEOMETRÍA',
                'PRED_LOCALIZADO': 'NO',
            }
            for name, value in classifications.items():
                if name in positions:
                    row[positions[name]] = value
            merged_rows.append(row)
            cartera_match['matches'].append(set(group))
            if ref_bundle.get('geometry') is not None:
                ref_bundle['geometry'].append(None)
        return len(groups)

    @staticmethod
    def _coverage_summary(fields, rows):
        positions = {name: index for index, name in enumerate(fields)}
        located_index = positions['PRED_LOCALIZADO']
        class_index = positions['PRED_CLASE']
        status_index = positions['CART_ESTADO']
        coverage = {
            'located': 0,
            'unlocated': 0,
            'located_debt': 0,
            'unlocated_debt': 0,
            'classes': {},
        }
        for row in rows:
            located = row[located_index] == 'SI'
            status = row[status_index]
            if located:
                coverage['located'] += 1
                if status == STATUS_LABELS[STATUS_DEBT]:
                    coverage['located_debt'] += 1
                class_name = row[class_index]
                coverage['classes'][class_name] = (
                    coverage['classes'].get(class_name, 0) + 1
                )
            else:
                coverage['unlocated'] += 1
                if status == STATUS_LABELS[STATUS_DEBT]:
                    coverage['unlocated_debt'] += 1
        return coverage

    @staticmethod
    def _find_field_index(field_names, hints):
        normalized_hints = [normalize_words(hint).replace(' ', '_') for hint in hints]
        for exact in (True, False):
            for index, name in enumerate(field_names):
                normalized = normalize_words(name).replace(' ', '_')
                for hint in normalized_hints:
                    if (normalized.endswith(hint) if exact else hint in normalized):
                        return index
        return None

    def _append_cartera_summary(self, fields, rows, cartera_bundle, match):
        """Añade los campos CART_* que alimentan la simbología del semáforo."""
        saldo_index = self._find_field_index(cartera_bundle['fields'], VALUE_HINTS)
        owner_index = self._find_field_index(cartera_bundle['fields'], OWNER_HINTS)
        desde_index = self._find_field_index(cartera_bundle['fields'], DESDE_HINTS)
        hasta_index = self._find_field_index(cartera_bundle['fields'], HASTA_HINTS)
        summaries = summarize_presence_matches(
            rows,
            match,
            cartera_bundle['rows'],
            value_column=saldo_index,
            owner_column=owner_index,
            desde_column=desde_index,
            hasta_column=hasta_index,
            current_year=date.today().year,
        )
        status_counts = {STATUS_DEBT: 0, STATUS_CLEAR: 0, STATUS_UNKNOWN: 0}
        additions = []
        for summary in summaries:
            status = summary['status']
            status_counts[status] += 1
            additions.append([
                STATUS_LABELS[status], summary['total_debt'], summary['obligation_count'],
                summary['vig_desde'], summary['vig_hasta'], summary['period'],
                summary['detail'],
            ])
        output_fields = list(fields) + [
            'CART_ESTADO', 'CART_SALDO', 'CART_OBLIG', 'CART_VIG_DES',
            'CART_VIG_HAS', 'CART_PERIODO', 'CART_DETALLE',
        ]
        output_rows = [list(row) + extra for row, extra in zip(rows, additions)]
        return output_fields, output_rows, status_counts

    def _perform_full_join(self, gdb_sources, r1_layer, r2_layer, cartera_layer, progress):
        progress.setLabelText('Leyendo las capas de la Geodatabase…')
        QApplication.processEvents()

        ref_layer = gdb_sources[0]
        ref_bundle = self._build_gdb_reference_bundle(gdb_sources, progress)
        bundles = [
            ref_bundle,
            self._build_source_bundle(r1_layer, 'R1_', 'r1', progress, 'R1'),
            self._build_source_bundle(r2_layer, 'R2_', 'r2', progress, 'R2'),
            self._build_source_bundle(
                cartera_layer, 'CARTERA_', 'cartera', progress, 'cartera',
            ),
        ]

        validation = {'issues': [], 'empty_counts': {}}
        for source_label, bundle in zip(('GDB', 'R1', 'R2', 'CARTERA'), bundles):
            issues, empty_count = self._validate_bundle_codes(bundle, source_label)
            validation['issues'].extend(issues)
            validation['empty_counts'][source_label] = empty_count
        validation['empty_total'] = sum(validation['empty_counts'].values())
        if not ref_bundle['rows']:
            raise RuntimeError(
                'Ningún terreno tiene un código predial válido de 20 o 30 dígitos.'
            )

        # Candado por municipio: el aplicativo solo procesa datos del municipio
        # habilitado (Morelia, 18479). Se evalúa sobre los códigos de terreno.
        authorized, detected, ratio = check_municipality_license(
            ref_bundle['rows'], ref_bundle['code_indexes'],
        )
        if not authorized:
            detail = (
                f'La Geodatabase corresponde al municipio {detected} '
                f'({ratio:.0%} de los predios).'
                if detected else
                'No se pudo identificar el municipio de los predios cargados.'
            )
            raise RuntimeError(
                'Aplicativo habilitado únicamente para '
                f'{LICENSED_MUNICIPALITY_NAME}, código catastral '
                f'{LICENSED_MUNICIPALITY_CODE}. {detail} '
                'El proceso se detuvo.'
            )

        # Esquema unificado con todos los campos de todas las fuentes.
        schemas = []
        for bundle in bundles:
            schemas.append([(name, '', bundle['source']) for name in bundle['fields']])
        out_fields = merge_field_definitions(
            [[(name.replace(' ', '_'), '', src) for name, _, src in schema] for schema in schemas]
        )

        merged_fields = list(ref_bundle['fields'])
        merged_rows = list(ref_bundle['rows'])
        merged_preferred = list(ref_bundle['code_indexes'])
        join_stats = []
        cartera_match = None
        cartera_offset = None
        for bundle in bundles[1:]:
            progress.setLabelText(f'Cruzando {bundle["source"].upper()} por código predial…')
            self._heartbeat(progress)
            merged_rows, match = left_join_rows_automatic(
                merged_fields,
                merged_rows,
                bundle['fields'],
                bundle['rows'],
                left_preferred=merged_preferred,
                right_preferred=bundle['code_indexes'],
                heartbeat=lambda: self._heartbeat(progress),
            )
            if match:
                left_key = ' + '.join(merged_fields[i] for i in match['left_columns'])
                right_key = ' + '.join(bundle['fields'][i] for i in match['right_columns'])
                matched = match['matched_left']
            else:
                left_key = right_key = '—'
                matched = 0
            join_stats.append({
                'source': bundle['source'].upper(),
                'matched': matched,
                'left_key': left_key,
                'right_key': right_key,
            })
            if bundle['source'] == 'cartera':
                cartera_match = match
            offset = len(merged_fields)
            if bundle['source'] == 'cartera':
                cartera_offset = offset
            merged_fields.extend(bundle['fields'])
            merged_preferred.extend(offset + index for index in bundle['code_indexes'])

        if cartera_match is not None and cartera_offset is not None:
            progress.setLabelText('Conservando deudores sin geometría…')
            self._append_unlocated_cartera_rows(
                merged_fields, merged_rows, ref_bundle, bundles[-1],
                cartera_match, cartera_offset,
            )

        merged_fields, merged_rows, status_counts = self._append_cartera_summary(
            merged_fields, merged_rows, bundles[-1], cartera_match,
        )
        self._heartbeat(progress)
        out_fields.extend([
            ('CART_ESTADO', 'String'), ('CART_SALDO', 'Double'),
            ('CART_OBLIG', 'Integer'), ('CART_VIG_DES', 'Integer'),
            ('CART_VIG_HAS', 'Integer'), ('CART_PERIODO', 'String'),
            ('CART_DETALLE', 'String'),
        ])
        coverage = self._coverage_summary(merged_fields, merged_rows)

        qgs_fields = QgsFields()
        for name, type_name in out_fields:
            if type_name == 'Double':
                field = QgsField(name, QVariant.Double, len=20, prec=2)
            elif type_name == 'Integer':
                field = QgsField(name, QVariant.Int)
            else:
                # Longitud libre: propietarios u obligaciones duplicadas se
                # consolidan con " | " y pueden superar 254 caracteres.
                field = QgsField(name, QVariant.String)
            qgs_fields.append(field)

        geometry_type = (
            ref_layer.wkbType() if ref_layer and ref_layer.isSpatial() else 100
        )
        output_crs = ref_layer.crs() if ref_layer else None

        def create_output_layer():
            return QgsMemoryProviderUtils.createMemoryLayer(
                'Semáforo cartera — GDB-R1-R2', qgs_fields,
                geometry_type, output_crs,
            )

        def safe_attribute(value, type_name):
            if value is None or value is NULL:
                return NULL
            if type_name == 'Double':
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return NULL
            if type_name == 'Integer':
                try:
                    return int(float(value))
                except (TypeError, ValueError):
                    return NULL
            # QDate/QDateTime y otros QVariant necesitan serialización antes
            # de entrar en un campo String del proveedor de memoria.
            if hasattr(value, 'toString'):
                try:
                    return value.toString(Qt.ISODate)
                except (TypeError, AttributeError):
                    pass
            return str(value)

        output = create_output_layer()
        provider = output.dataProvider()

        new_features = []
        total = len(merged_rows)
        field_positions = {name: index for index, name in enumerate(merged_fields)}
        for row_index in range(total):
            merged_row = merged_rows[row_index]
            feature = QgsFeature(qgs_fields)
            geom = None
            if (
                ref_bundle.get('geometry') is not None
                and row_index < len(ref_bundle['geometry'])
            ):
                geom = ref_bundle['geometry'][row_index]
            # Las filas de cartera sin correspondencia espacial permanecen en
            # la tabla con geometría vacía. QGIS no acepta ``None`` en
            # setGeometry(), por eso solo se asigna cuando existe geometría.
            if geom is not None:
                feature.setGeometry(geom)
            feature.setAttributes([
                safe_attribute(merged_row[field_positions[name]], type_name)
                if name in field_positions and merged_row[field_positions[name]] is not None
                else NULL
                for name, type_name in out_fields
            ])
            new_features.append(feature)
            if row_index % 500 == 0:
                progress.setLabelText(f'Unificando… ({row_index:,} / {total:,})')
                QApplication.processEvents()
                if progress.wasCanceled():
                    return None

        progress.setLabelText('Guardando la capa temporal…')
        self._heartbeat(progress)
        provider.addFeatures(new_features)
        output.updateExtents()

        def stored_counts(layer):
            total_count = 0
            geometry_count = 0
            for stored in layer.getFeatures():
                total_count += 1
                if stored.hasGeometry() and not stored.geometry().isEmpty():
                    geometry_count += 1
            return total_count, geometry_count

        stored_total, stored_geometries = stored_counts(output)
        expected_total = len(new_features)
        if (
            stored_total != expected_total
            or stored_geometries != coverage['located']
        ):
            # Algunos proveedores pueden rechazar un lote completo por una
            # sola entidad. Se reconstruye de forma individual para aislarla
            # sin duplicar registros que sí se hayan insertado.
            progress.setLabelText('Verificando entidades individualmente…')
            self._heartbeat(progress)
            fallback = create_output_layer()
            fallback_provider = fallback.dataProvider()
            failed_rows = []
            for row_number, source_feature in enumerate(new_features, 1):
                candidate = QgsFeature(qgs_fields)
                if source_feature.hasGeometry():
                    candidate.setGeometry(source_feature.geometry())
                candidate.setAttributes(source_feature.attributes())
                before = fallback.featureCount()
                fallback_provider.addFeatures([candidate])
                if fallback.featureCount() <= before:
                    failed_rows.append(row_number)
                if row_number % 250 == 0:
                    progress.setLabelText(
                        f'Verificando… ({row_number:,} / {expected_total:,})'
                    )
                    self._heartbeat(progress)
            fallback.updateExtents()
            fallback_total, fallback_geometries = stored_counts(fallback)
            if (
                failed_rows or fallback_total != expected_total
                or fallback_geometries != coverage['located']
            ):
                sample = ', '.join(str(row) for row in failed_rows[:10]) or '—'
                raise RuntimeError(
                    'La capa temporal quedó incompleta: '
                    f'{fallback_total:,} de {expected_total:,} registros y '
                    f'{fallback_geometries:,} de {coverage["located"]:,} polígonos. '
                    f'Filas rechazadas: {sample}.'
                )
            output = fallback
            provider = fallback_provider

        stored_total, stored_geometries = stored_counts(output)
        if stored_total != expected_total or stored_geometries != coverage['located']:
            raise RuntimeError(
                'No fue posible verificar la capa temporal completa.'
            )
        for indexed_name in ('GDB_CODIGO', 'CARTERA_Numero_Predial', 'CART_ESTADO'):
            field_index = output.fields().indexOf(indexed_name)
            if field_index >= 0:
                provider.createAttributeIndex(field_index)
        output.setCustomProperty('semaforo_cartera_join_output', True)
        output.setCustomProperty('semaforo_cartera_output', True)
        categories = []
        for status in (STATUS_DEBT, STATUS_CLEAR, STATUS_UNKNOWN):
            if not status_counts.get(status):
                continue
            symbol = QgsSymbol.defaultSymbol(output.geometryType())
            symbol.setColor(QColor(COLORS[status]))
            label = STATUS_LABELS[status]
            categories.append(QgsRendererCategory(label, symbol, label))
        if categories:
            output.setRenderer(QgsCategorizedSymbolRenderer('CART_ESTADO', categories))
        QgsProject.instance().addMapLayer(output)
        return (
            output, new_features, out_fields, join_stats, status_counts,
            coverage, validation,
        )

    # ------------------------------------------------------------ table UI
    def _populate_table(self, features, fields):
        self.table.setSortingEnabled(False)
        self._table_model = JoinedLayerTableModel(features, fields, self.table)
        self._table_proxy = JoinedLayerFilterProxyModel(self.table)
        self._table_proxy.setSourceModel(self._table_model)
        self.table.setModel(self._table_proxy)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setDefaultSectionSize(150)
        self.table.setSortingEnabled(True)
        self.apply_filter()

    def apply_filter(self, *_):
        if self._table_proxy is None:
            return
        criterion = self.cbo_filter.currentData() or ('', '')
        field_name, value = criterion
        self._table_proxy.set_criteria(
            self.inp_filter.text().strip(), field_name, value,
        )
        visible = self._table_proxy.rowCount()
        total = self._table_model.rowCount() if self._table_model else 0
        if visible < total:
            self.lbl_status.setText(f'{visible:,} de {total:,} filas visibles.')

    def _update_classification_buttons(
        self, total, counts, coverage, invalid_count=0,
    ):
        self.btn_class_all.setText(f'📋 Todos: {total:,}')
        self.btn_class_debt.setText(
            f'🔴 En deuda: {counts.get(STATUS_DEBT, 0):,}'
        )
        self.btn_class_clear.setText(
            f'🟢 Paz y salvo: {counts.get(STATUS_CLEAR, 0):,}'
        )
        self.btn_invalid_codes.setText(
            f'⚠ Códigos ilegibles: {invalid_count:,}'
        )
        self.btn_class_unlocated.setText(
            f'📍 Sin geometría: {coverage.get("unlocated", 0):,}'
        )
        for button in self._classification_buttons:
            button.setEnabled(True)
        self.btn_invalid_codes.setEnabled(invalid_count > 0)

    def set_classification_filter(self, field_name, value):
        """Filtra la tabla y selecciona la clasificación en la capa temporal."""
        selected_index = 0
        for index in range(self.cbo_filter.count()):
            criterion = self.cbo_filter.itemData(index)
            if criterion and tuple(criterion) == (field_name, value):
                selected_index = index
                break
        self.cbo_filter.setCurrentIndex(selected_index)
        self.apply_filter()

        layer = self._joined_layer
        if layer is None or not layer.isValid():
            return
        if not field_name:
            layer.removeSelection()
            self.zoom_full_layer()
            self.lbl_status.setText(
                f'{self._table_proxy.rowCount():,} registros visibles.'
            )
            return
        field_index = layer.fields().indexOf(field_name)
        if field_index < 0:
            return
        feature_ids = []
        spatial_ids = []
        for feature in layer.getFeatures():
            if _text(feature[field_index]) != value:
                continue
            feature_ids.append(feature.id())
            if feature.hasGeometry() and not feature.geometry().isEmpty():
                spatial_ids.append(feature.id())
        layer.selectByIds(feature_ids)
        if spatial_ids:
            try:
                self.iface.mapCanvas().zoomToSelected(layer)
            except (AttributeError, TypeError):
                pass
        self.iface.mapCanvas().refresh()
        self.lbl_status.setText(
            f'{len(feature_ids):,} registros en “{value}” · '
            f'{len(spatial_ids):,} con geometría seleccionada.'
        )

    def _schedule_filter(self, *_):
        """Agrupa pulsaciones para no recalcular el filtro en cada tecla."""
        self._filter_timer.start()

    def clear_result(self):
        self._table_model = JoinedLayerTableModel(parent=self.table)
        self._table_proxy = JoinedLayerFilterProxyModel(self.table)
        self._table_proxy.setSourceModel(self._table_model)
        self.table.setModel(self._table_proxy)
        self._joined_layer = None
        self._last_status_counts = {}
        self._last_coverage = {}
        self._last_code_issues = []
        self._last_empty_code_counts = {}
        self.btn_export.setEnabled(False)
        self.btn_zoom_all.setEnabled(False)
        self._update_classification_buttons(0, {}, {})
        for button in self._classification_buttons:
            button.setEnabled(False)
        self.cbo_gdb_layer.blockSignals(True)
        self.cbo_gdb_layer.clear()
        self.cbo_gdb_layer.addItem('Se creará al procesar los cuatro terrenos…')
        self.cbo_gdb_layer.setEnabled(False)
        self.cbo_gdb_layer.blockSignals(False)
        self.cbo_filter.setCurrentIndex(0)
        self.inp_filter.clear()
        self.lbl_summary.setText('Resultado limpiado. Vuelve a ejecutar el join si lo necesitas.')
        self.lbl_status.setText('Listo.')

    def zoom_full_layer(self):
        """Muestra la extensión completa de todos los polígonos consolidados."""
        layer = self._joined_layer
        if layer is None or not layer.isValid() or layer.extent().isEmpty():
            return
        self.iface.setActiveLayer(layer)
        canvas = self.iface.mapCanvas()
        canvas.setExtent(layer.extent())
        canvas.refresh()

    # -------------------------------------------------------------- export
    def export_invalid_codes(self):
        """Guarda exclusivamente los códigos no vacíos que fallaron validación."""
        issues = self._last_code_issues
        if not issues:
            QMessageBox.information(
                self, 'Sin inconsistencias',
                'No se encontraron códigos prediales ilegibles.',
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            self, 'Guardar reporte de códigos ilegibles',
            'reporte_codigos_ilegibles.xlsx', 'Excel (*.xlsx)',
        )
        if not path:
            return
        if not path.lower().endswith('.xlsx'):
            path += '.xlsx'
        try:
            import openpyxl
        except ImportError:
            QMessageBox.critical(
                self, 'No se puede exportar',
                'El entorno Python de QGIS no tiene disponible openpyxl.',
            )
            return
        workbook = openpyxl.Workbook(write_only=True)
        sheet = workbook.create_sheet('Códigos ilegibles')
        sheet.append([
            'ORIGEN', 'FILA', 'CAMPOS_CODIGO', 'VALOR_ORIGINAL',
            'CODIGO_NORMALIZADO', 'MOTIVO',
        ])
        for issue in issues:
            sheet.append([
                issue['source'], issue['row'], issue['fields'], issue['raw'],
                issue['normalized'], issue['reason'],
            ])
        try:
            workbook.save(path)
        except Exception as error:
            QMessageBox.critical(self, 'Error al exportar', str(error))
            return
        self.lbl_status.setText(f'Reporte de códigos ilegibles: {path}')
        QMessageBox.information(
            self, 'Reporte generado',
            f'Se exportaron {len(issues):,} inconsistencias en:\n{path}',
        )

    def _layer_is_licensed(self, layer, limit=1500):
        """Confirma que la capa unificada pertenece al municipio habilitado."""
        fields = [field.name() for field in layer.fields()]
        code_field = next(
            (name for name in ('GDB_CODIGO', 'CARTERA_Numero_Predial')
             if name in fields),
            None,
        )
        if code_field is None:
            return False
        rows = []
        for processed, feature in enumerate(layer.getFeatures()):
            rows.append([feature[code_field]])
            if processed + 1 >= limit:
                break
        authorized, _, _ = check_municipality_license(rows, [0])
        return authorized

    def export_result(self):
        """Exporta datos, balance financiero y resúmenes tipo tabla dinámica."""
        layer = self._joined_layer
        if layer is None or not layer.isValid():
            QMessageBox.information(
                self, 'Sin resultado', 'Primero crea la capa unificada y el semáforo.',
            )
            return
        if not self._layer_is_licensed(layer):
            QMessageBox.critical(
                self, 'Municipio no habilitado',
                'La exportación está habilitada únicamente para '
                f'{LICENSED_MUNICIPALITY_NAME}, código catastral '
                f'{LICENSED_MUNICIPALITY_CODE}.',
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            self, 'Exportar resultado unificado', 'semaforo_cartera_unificado.xlsx',
            'Excel (*.xlsx)',
        )
        if not path:
            return
        if not path.lower().endswith('.xlsx'):
            path += '.xlsx'
        try:
            import openpyxl
            from openpyxl.cell import WriteOnlyCell
            from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
            from openpyxl.chart import BarChart, Reference
            from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
            from openpyxl.utils import get_column_letter
        except ImportError:
            QMessageBox.critical(
                self, 'No se puede exportar',
                'El entorno Python de QGIS no tiene disponible openpyxl.',
            )
            return

        def clean(value):
            if _is_null(value):
                return None
            if isinstance(value, (int, float, bool)):
                return value
            return ILLEGAL_CHARACTERS_RE.sub('', str(value))

        headers = [field.name() for field in layer.fields()]
        clean_rows = (
            [clean(value) for value in feature.attributes()]
            for feature in layer.getFeatures()
        )
        analytics = build_export_analytics(headers, clean_rows)

        progress = QProgressDialog(
            'Exportando el resultado unificado…', 'Cancelar',
            0, max(1, layer.featureCount()), self,
        )
        progress.setWindowTitle('Exportar semáforo')
        progress.setWindowIcon(self._app_icon())
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)

        workbook = openpyxl.Workbook(write_only=True)
        dashboard = workbook.create_sheet('Resumen ejecutivo')
        pivots = workbook.create_sheet('Análisis financiero')
        financial = workbook.create_sheet('Balance financiero')
        complete = workbook.create_sheet('Todos los registros')
        debtors = workbook.create_sheet('Deudores')
        clear_sheet = workbook.create_sheet('Paz y salvo')
        invalid_codes = workbook.create_sheet('Códigos ilegibles')

        dark_blue = '174A7E'
        medium_blue = '2E86DE'
        pale_blue = 'EAF2F8'
        red = 'D73027'
        pale_red = 'FCE8E6'
        green = '1A9850'
        pale_green = 'E6F4EA'
        orange = 'E67E22'
        pale_orange = 'FEF3E7'
        white = 'FFFFFF'
        gray = '526472'
        thin_gray = Side(style='thin', color='D7E0E8')

        title_font = Font(name='Calibri', size=16, bold=True, color=white)
        header_font = Font(name='Calibri', size=10, bold=True, color=white)
        body_font = Font(name='Calibri', size=10, color='263238')

        def styled_row(sheet, values, fill=None, font=None, formats=None):
            cells = []
            for column, value in enumerate(values):
                cell = WriteOnlyCell(sheet, value=value)
                cell.font = font or body_font
                cell.alignment = Alignment(vertical='center')
                if fill:
                    cell.fill = PatternFill('solid', fgColor=fill)
                if formats and column in formats:
                    cell.number_format = formats[column]
                cell.border = Border(bottom=thin_gray)
                cells.append(cell)
            sheet.append(cells)

        def title_row(sheet, title):
            styled_row(sheet, [title], dark_blue, title_font)

        def header_row(sheet, values):
            styled_row(sheet, values, dark_blue, header_font)

        def set_widths(sheet, widths):
            for column, width in enumerate(widths, 1):
                sheet.column_dimensions[get_column_letter(column)].width = width

        for sheet in (
            dashboard, pivots, financial, complete, debtors, clear_sheet,
            invalid_codes,
        ):
            sheet.sheet_view.showGridLines = False
        dashboard.freeze_panes = 'A4'
        pivots.freeze_panes = 'A4'

        # ----------------------------- resumen ejecutivo y KPIs financieros
        title_row(dashboard, 'SEMÁFORO DE CARTERA PREDIAL — RESUMEN EJECUTIVO')
        styled_row(dashboard, [
            'El campo SALDO representa cartera pendiente por recaudar. '
            'Los insumos no contienen pagos recibidos; por ello no se calcula '
            'recaudo ejecutado.'
        ], pale_orange, Font(name='Calibri', size=10, italic=True, color=gray))
        dashboard.append([])
        header_row(dashboard, ['INDICADOR', 'VALOR'])
        dashboard_kpis = [
            ('Cartera pendiente por recaudar', analytics['debt_total'], '$#,##0.00'),
            ('Predios en deuda', analytics['debt_count'], '#,##0'),
            ('Predios a paz y salvo', analytics['clear_count'], '#,##0'),
            ('Saldo promedio por deudor', analytics['debt_average'], '$#,##0.00'),
            ('Deudores localizados', analytics['located_debt'], '#,##0'),
            ('Deudores sin geometría', analytics['unlocated_debt'], '#,##0'),
            ('Paz y salvo localizados', analytics.get('located_clear', 0), '#,##0'),
            ('Vigencia actual asignada a paz y salvo', date.today().year, '0'),
            ('Registros totales', analytics['total'], '#,##0'),
            ('Códigos ilegibles reportados', len(self._last_code_issues), '#,##0'),
            ('Códigos vacíos omitidos',
             sum(self._last_empty_code_counts.values()), '#,##0'),
        ]
        for label, amount, number_format in dashboard_kpis:
            styled_row(
                dashboard, [label, amount], pale_blue, body_font,
                {1: number_format},
            )
        dashboard.append([])
        styled_row(dashboard, ['MAYORES DEUDORES'], medium_blue, header_font)
        header_row(dashboard, ['TOP', 'CÓDIGO PREDIAL', 'PROPIETARIO', 'CLASE',
                               'VIGENCIA', 'LOCALIZADO', 'SALDO'])
        for rank, debtor in enumerate(analytics['top_debtors'][:15], 1):
            styled_row(dashboard, [
                rank, debtor['code'], debtor['owner'], debtor['class'],
                debtor['period'], debtor['located'], debtor['balance'],
            ], None, body_font, {6: '$#,##0.00'})

        clear_predios = analytics.get('clear_predios', [])
        if clear_predios:
            dashboard.append([])
            styled_row(
                dashboard,
                [f'PREDIOS A PAZ Y SALVO — VIGENCIA {date.today().year} '
                 f'(mayor avalúo)'],
                green, header_font,
            )
            header_row(dashboard, ['TOP', 'CÓDIGO PREDIAL', 'PROPIETARIO',
                                   'CLASE', 'VIGENCIA', 'LOCALIZADO', 'AVALÚO'])
            for rank, predio in enumerate(clear_predios[:15], 1):
                styled_row(dashboard, [
                    rank, predio['code'], predio['owner'], predio['class'],
                    predio['period'], predio['located'], predio['avaluo'],
                ], pale_green, body_font, {6: '$#,##0.00'})
        set_widths(dashboard, [22, 34, 40, 23, 18, 14, 20])

        # ---------------------------------------- tablas resumen automáticas
        pivot_row = 1

        def pivot_append(values, fill=None, font=None, formats=None):
            nonlocal pivot_row
            styled_row(pivots, values, fill, font, formats)
            pivot_row += 1

        title_row(pivots, 'TABLAS DE ANÁLISIS — ACTUALIZADAS AL EXPORTAR')
        pivot_row += 1
        pivots.append([])
        pivot_row += 1

        pivot_append(['ESTADO', 'PREDIOS', 'CARTERA', '% PREDIOS', '% CARTERA'],
                     dark_blue, header_font)
        status_start = pivot_row
        for status, values in sorted(analytics['by_status'].items()):
            row_fill = pale_red if status == 'EN DEUDA' else (
                pale_green if status == 'PAZ Y SALVO' else pale_blue
            )
            pivot_append([
                status, values['count'], values['balance'],
                values['count'] / analytics['total'] if analytics['total'] else 0,
                values['balance'] / analytics['debt_total']
                if analytics['debt_total'] else 0,
            ], row_fill, body_font, {1: '#,##0', 2: '$#,##0.00', 3: '0.0%', 4: '0.0%'})
        status_end = pivot_row - 1
        pivots.append([])
        pivot_row += 1

        pivot_append([
            'CLASE PREDIAL', 'TOTAL', 'EN DEUDA', 'PAZ Y SALVO',
            'CARTERA', 'PROMEDIO DEUDA', '% CARTERA',
        ], dark_blue, header_font)
        class_start = pivot_row
        class_items = sorted(
            analytics['by_class'].items(),
            key=lambda item: item[1]['balance'], reverse=True,
        )
        for class_name, values in class_items:
            average = values['balance'] / values['debt'] if values['debt'] else 0
            pivot_append([
                class_name, values['total'], values['debt'], values['clear'],
                values['balance'], average,
                values['balance'] / analytics['debt_total']
                if analytics['debt_total'] else 0,
            ], None, body_font, {
                1: '#,##0', 2: '#,##0', 3: '#,##0',
                4: '$#,##0.00', 5: '$#,##0.00', 6: '0.0%',
            })
        class_end = pivot_row - 1
        pivots.append([])
        pivot_row += 1

        pivot_append([
            'CÓDIGO VEREDA', 'NOMBRE VEREDA', 'TOTAL', 'EN DEUDA',
            'PAZ Y SALVO', 'CARTERA', 'PROMEDIO DEUDA', '% CARTERA',
        ], dark_blue, header_font)
        vereda_start = pivot_row
        vereda_items = sorted(
            analytics['by_vereda'].items(),
            key=lambda item: item[1]['balance'], reverse=True,
        )
        for code, values in vereda_items:
            average = values['balance'] / values['debt'] if values['debt'] else 0
            pivot_append([
                values.get('code', code), values.get('name', ''),
                values['total'], values['debt'], values['clear'],
                values['balance'], average,
                values['balance'] / analytics['debt_total']
                if analytics['debt_total'] else 0,
            ], None, body_font, {
                2: '#,##0', 3: '#,##0', 4: '#,##0',
                5: '$#,##0.00', 6: '$#,##0.00', 7: '0.0%',
            })
        vereda_end = pivot_row - 1
        pivots.append([])
        pivot_row += 1

        # Tablas por categoría (manzana urbana, estrato y destino económico).
        # Reparten deudores y paz y salvo, y aíslan la cartera pendiente.
        def category_table(header, mapping, top=None):
            pivot_append([
                header, 'TOTAL', 'EN DEUDA', 'PAZ Y SALVO', 'CARTERA',
                'PROMEDIO DEUDA', '% CARTERA',
            ], dark_blue, header_font)
            items = sorted(
                mapping.items(), key=lambda item: item[1]['balance'],
                reverse=True,
            )
            if top:
                items = items[:top]
            for key, values in items:
                average = values['balance'] / values['debt'] if values['debt'] else 0
                pivot_append([
                    key, values['total'], values['debt'], values['clear'],
                    values['balance'], average,
                    values['balance'] / analytics['debt_total']
                    if analytics['debt_total'] else 0,
                ], None, body_font, {
                    1: '#,##0', 2: '#,##0', 3: '#,##0',
                    4: '$#,##0.00', 5: '$#,##0.00', 6: '0.0%',
                })
            pivot_append([])

        if analytics.get('by_manzana'):
            category_table('MANZANA (URBANO)', analytics['by_manzana'], top=40)
        if analytics.get('by_estrato'):
            category_table('ESTRATO', analytics['by_estrato'])
        if analytics.get('by_destino'):
            category_table('DESTINO ECONÓMICO', analytics['by_destino'])

        pivot_append([
            'VIGENCIA', 'DEUDORES', 'PAZ Y SALVO', 'TOTAL PREDIOS',
            'CARTERA', 'PROMEDIO DEUDA',
        ], dark_blue, header_font)
        period_start = pivot_row
        for period, values in sorted(analytics['by_period'].items()):
            debt = values.get('debt', values.get('count', 0))
            pivot_append([
                period, debt, values.get('clear', 0),
                values.get('total', debt), values['balance'],
                values['balance'] / debt if debt else 0,
            ], None, body_font, {
                1: '#,##0', 2: '#,##0', 3: '#,##0',
                4: '$#,##0.00', 5: '$#,##0.00',
            })
        period_end = pivot_row - 1
        set_widths(pivots, [30, 26, 15, 14, 14, 20, 18, 13])

        # Los gráficos se apoyan en las tablas anteriores y se recalculan en
        # cada nueva exportación del plugin.
        if class_end >= class_start:
            class_chart = BarChart()
            class_chart.type = 'bar'
            class_chart.style = 10
            class_chart.title = 'Cartera pendiente por clase predial'
            class_chart.x_axis.title = 'Saldo pendiente'
            class_chart.y_axis.title = 'Clase'
            class_chart.height = 7.5
            class_chart.width = 14
            class_chart.add_data(
                Reference(pivots, min_col=5, min_row=class_start - 1,
                          max_row=class_end), titles_from_data=True,
            )
            class_chart.set_categories(
                Reference(pivots, min_col=1, min_row=class_start,
                          max_row=class_end)
            )
            dashboard.add_chart(class_chart, 'I2')
        if vereda_end >= vereda_start:
            chart_end = min(vereda_start + 9, vereda_end)
            vereda_chart = BarChart()
            vereda_chart.type = 'bar'
            vereda_chart.style = 10
            vereda_chart.title = 'Top 10 veredas por cartera pendiente'
            vereda_chart.x_axis.title = 'Saldo pendiente'
            vereda_chart.y_axis.title = 'Vereda'
            vereda_chart.height = 8
            vereda_chart.width = 14
            vereda_chart.add_data(
                Reference(pivots, min_col=6, min_row=vereda_start - 1,
                          max_row=chart_end), titles_from_data=True,
            )
            vereda_chart.set_categories(
                Reference(pivots, min_col=2, min_row=vereda_start,
                          max_row=chart_end)
            )
            dashboard.add_chart(vereda_chart, 'I18')

        # -------------------------------- detalle filtrable de balance predial
        financial_headers = [
            'CÓDIGO PREDIAL', 'CÓDIGO VEREDA', 'NOMBRE VEREDA', 'MANZANA',
            'ÁMBITO', 'FORMALIDAD', 'CLASE', 'ESTRATO', 'DESTINO',
            'ESTADO', 'SALDO PENDIENTE', 'VIGENCIA DESDE', 'VIGENCIA HASTA',
            'PERIODO', 'PROPIETARIO', 'IDENTIFICACIÓN', 'DIRECCIÓN',
            'AVALÚO', 'LOCALIZADO', 'CAPA ORIGEN',
        ]
        header_positions = {name.casefold(): index for index, name in enumerate(headers)}

        def source_index(*candidates):
            for candidate in candidates:
                index = header_positions.get(candidate.casefold())
                if index is not None:
                    return index
            return -1

        def source_indexes(*candidates):
            return [index for index in (
                source_index(candidate) for candidate in candidates
            ) if index >= 0]

        def is_blank(item):
            return item is None or (
                isinstance(item, str)
                and (not item.strip() or item.strip().upper() == 'NULL')
            )

        def first_nonblank(values, indexes):
            """Primer valor no vacío entre varias columnas de una fila.

            La cartera queda vacía para los predios a paz y salvo, así que su
            propietario, identificación, dirección y avalúo se toman de R1.
            """
            for index in indexes:
                if 0 <= index < len(values) and not is_blank(values[index]):
                    return values[index]
            return None

        def first_segment(item):
            """El join consolida valores repetidos con ' | '; toma el primero."""
            if isinstance(item, str) and '|' in item:
                return item.split('|')[0].strip()
            return item

        # Índices (algunos con respaldo) para armar cada columna del balance.
        idx_code = source_indexes('GDB_CODIGO', 'CARTERA_Numero_Predial')
        idx_vereda = source_indexes(
            'GDB_VEREDA_CODIGO', 'GDB_CODIGO_VEREDA', 'GDB_VEREDA',
        )
        idx_vereda_name = source_indexes('GDB_VEREDA_NOMBRE')
        idx_manzana = source_indexes(
            'GDB_MANZANA_CODIGO', 'GDB_CODIGO_MANZANA', 'GDB_MANZANA',
        )
        idx_estrato = source_indexes(
            'R2_Estrato', 'R2_Estrato_1', 'R2_Estrato_2', 'CARTERA_ESTRATO',
        )
        idx_destino = source_indexes(
            'R1_DestinoEconomico', 'R1_Destino_Economico', 'R1_Destino',
        )
        idx_owner = source_indexes(
            'CARTERA_PROPIETARIO', 'R1_Nombre', 'CART_DETALLE',
        )
        idx_ident = source_indexes('CARTERA_IDENTIFICACION', 'R1_NoDocumento')
        idx_direccion = source_indexes('CARTERA_DIRECCION', 'R1_Direccion')
        idx_avaluo = source_indexes(
            'CARTERA_AVALUO', 'R1_Avaluo_($)', 'R1_Avaluo',
        )
        idx_ambito = source_index('PRED_AMBITO')
        idx_formalidad = source_index('PRED_FORMALIDAD')
        idx_clase = source_index('PRED_CLASE')
        idx_saldo = source_index('CART_SALDO')
        idx_vdes = source_index('CART_VIG_DES')
        idx_vhas = source_index('CART_VIG_HAS')
        idx_periodo = source_index('CART_PERIODO')
        idx_localizado = source_index('PRED_LOCALIZADO')
        idx_capa = source_index('GDB_CAPA_ORIGEN')

        financial_formats = {
            10: '$#,##0.00', 11: '0', 12: '0', 17: '$#,##0.00',
        }

        financial.freeze_panes = 'A2'
        complete.freeze_panes = 'A2'
        debtors.freeze_panes = 'A2'
        clear_sheet.freeze_panes = 'A2'
        invalid_codes.freeze_panes = 'A2'
        header_row(financial, financial_headers)
        header_row(complete, headers)
        header_row(debtors, headers)
        header_row(clear_sheet, headers)
        header_row(invalid_codes, [
            'ORIGEN', 'FILA', 'CAMPOS_CODIGO', 'VALOR_ORIGINAL',
            'CODIGO_NORMALIZADO', 'MOTIVO',
        ])
        for issue in self._last_code_issues:
            styled_row(invalid_codes, [
                clean(issue['source']), issue['row'], clean(issue['fields']),
                clean(issue['raw']), clean(issue['normalized']),
                clean(issue['reason']),
            ], pale_orange)

        debt_index = source_index('CART_ESTADO')
        canceled = False
        debtor_rows = 0
        clear_rows = 0
        for processed, feature in enumerate(layer.getFeatures(), 1):
            values = [clean(value) for value in feature.attributes()]
            status = values[debt_index] if debt_index >= 0 else None
            status_fill = pale_red if status == STATUS_LABELS[STATUS_DEBT] else (
                pale_green if status == STATUS_LABELS[STATUS_CLEAR] else pale_blue
            )

            # En las tablas extensas se colorea la celda Estado para conservar
            # velocidad y tamaño de archivo sin perder la lectura del semáforo.
            complete_row = list(values)
            if debt_index >= 0:
                status_cell = WriteOnlyCell(complete, value=status)
                status_cell.fill = PatternFill('solid', fgColor=status_fill)
                status_cell.font = Font(bold=True, color=(
                    red if status == STATUS_LABELS[STATUS_DEBT] else green
                ))
                complete_row[debt_index] = status_cell
            complete.append(complete_row)

            if status == STATUS_LABELS[STATUS_DEBT]:
                debtor_rows += 1
                styled_row(debtors, values, pale_red, body_font)
            elif status == STATUS_LABELS[STATUS_CLEAR]:
                clear_rows += 1
                styled_row(clear_sheet, values, pale_green, body_font)

            financial_values = [
                first_nonblank(values, idx_code),
                first_nonblank(values, idx_vereda),
                first_nonblank(values, idx_vereda_name),
                first_nonblank(values, idx_manzana),
                values[idx_ambito] if 0 <= idx_ambito < len(values) else None,
                values[idx_formalidad] if 0 <= idx_formalidad < len(values) else None,
                values[idx_clase] if 0 <= idx_clase < len(values) else None,
                first_segment(first_nonblank(values, idx_estrato)),
                first_nonblank(values, idx_destino),
                status,
                values[idx_saldo] if 0 <= idx_saldo < len(values) else None,
                values[idx_vdes] if 0 <= idx_vdes < len(values) else None,
                values[idx_vhas] if 0 <= idx_vhas < len(values) else None,
                values[idx_periodo] if 0 <= idx_periodo < len(values) else None,
                first_nonblank(values, idx_owner),
                first_nonblank(values, idx_ident),
                first_nonblank(values, idx_direccion),
                parse_number(first_segment(first_nonblank(values, idx_avaluo))),
                values[idx_localizado] if 0 <= idx_localizado < len(values) else None,
                values[idx_capa] if 0 <= idx_capa < len(values) else None,
            ]
            styled_row(
                financial, financial_values, status_fill, body_font,
                financial_formats,
            )
            if processed % 250 == 0:
                progress.setValue(processed)
                QApplication.processEvents()
                if progress.wasCanceled():
                    canceled = True
                    break
        if canceled:
            workbook.close()
            progress.close()
            self.lbl_status.setText('Exportación cancelada.')
            return

        total_rows = layer.featureCount() + 1
        financial.auto_filter.ref = (
            f'A1:{get_column_letter(len(financial_headers))}{total_rows}'
        )
        complete.auto_filter.ref = (
            f'A1:{get_column_letter(len(headers))}{total_rows}'
        )
        debtors.auto_filter.ref = (
            f'A1:{get_column_letter(len(headers))}{debtor_rows + 1}'
        )
        clear_sheet.auto_filter.ref = (
            f'A1:{get_column_letter(len(headers))}{clear_rows + 1}'
        )
        invalid_codes.auto_filter.ref = f'A1:F{len(self._last_code_issues) + 1}'
        set_widths(financial, [
            34, 20, 26, 20, 12, 14, 22, 10, 12, 16,
            20, 12, 12, 16, 40, 20, 35, 20, 14, 25,
        ])
        set_widths(invalid_codes, [22, 10, 28, 38, 34, 45])

        try:
            progress.setLabelText('Guardando el tablero financiero en Excel…')
            QApplication.processEvents()
            workbook.save(path)
        except Exception as error:
            progress.close()
            QMessageBox.critical(self, 'Error al exportar', str(error))
            return
        progress.setValue(progress.maximum())
        progress.close()
        self.lbl_status.setText(f'Resultado y balance financiero exportados: {path}')
        QMessageBox.information(
            self, 'Exportación terminada',
            'El Excel incluye resumen ejecutivo, análisis financiero, balance '
            'filtrable y las hojas Deudores y Paz y salvo. '
            f'Los predios a paz y salvo se reportan con vigencia {date.today().year}:'
            f'\n{path}',
        )

    # ---------------------------------------------------------------- SQL
    def open_sql(self):
        if self._joined_layer is None or not self._joined_layer.isValid():
            QMessageBox.information(self, 'Sin capa unida', 'Primero ejecuta el join completo.')
            return
        dialog = SqlQueryDialog(self, self._joined_layer)
        dialog.exec_()


class SqlQueryDialog(QDialog):
    """Ventana para ejecutar consultas SQL sobre la capa unida."""

    def __init__(self, parent, layer):
        super().__init__(parent)
        self.layer = layer
        self.setWindowTitle(f'Consulta SQL — {layer.name()}')
        self.resize(760, 520)
        root = QVBoxLayout(self)
        self.lbl_info = QLabel(
            f'Capa: {layer.name()} · {layer.featureCount():,} filas · {layer.fields().count()} campos.'
        )
        root.addWidget(self.lbl_info)
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText(
            'Escribe una expresión de QgsExpression.\n\n'
            'Ejemplos:\n'
            '  "R1_SALDO" > 1000 AND "R1_SALDO" IS NOT NULL\n'
            '  "CODPREDIAL" LIKE \'18%\''
        )
        root.addWidget(self.editor, 1)
        buttons = QHBoxLayout()
        self.btn_run = QPushButton('▶ Ejecutar')
        self.btn_close = QPushButton('Cerrar')
        buttons.addWidget(self.btn_run)
        buttons.addStretch(1)
        buttons.addWidget(self.btn_close)
        root.addLayout(buttons)
        self.lbl_status = QLabel('')
        root.addWidget(self.lbl_status)
        self.btn_run.clicked.connect(self.run)
        self.btn_close.clicked.connect(self.close)

    def run(self):
        expression = self.editor.toPlainText().strip()
        if not expression:
            QMessageBox.information(self, 'Consulta vacía', 'Escribe una expresión antes de ejecutar.')
            return
        try:
            expr = QgsExpression(expression)
        except Exception as error:
            QMessageBox.critical(self, 'Expresión inválida', str(error))
            return
        if expr.hasParserError():
            QMessageBox.critical(self, 'Expresión inválida', expr.parserErrorString())
            return
        try:
            request = QgsFeatureRequest(expr)
            feature_ids = []
            for processed, feature in enumerate(self.layer.getFeatures(request), 1):
                feature_ids.append(feature.id())
                if processed % 1000 == 0:
                    QApplication.processEvents()
        except Exception as error:
            QMessageBox.critical(self, 'Error al consultar', str(error))
            return
        self.layer.selectByIds(feature_ids)
        n = len(feature_ids)
        self.lbl_status.setText(
            f'{n:,} filas coinciden con la consulta. Seleccionadas en la capa “{self.layer.name()}”.'
        )
        parent = self.parent()
        if hasattr(parent, 'iface'):
            try:
                parent.iface.mapCanvas().refresh()
            except Exception:
                pass
