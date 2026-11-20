import ast
import importlib
import io
import sys
import types
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
PACKAGE_PARENT = PROJECT_DIR.parent


class _Widget:
    pass


class _QVariant:
    Int = 1
    LongLong = 2
    UInt = 3
    ULongLong = 4
    Double = 5
    String = 6
    Date = 7
    DateTime = 8


def _install_qgis_stubs():
    """Permite probar helpers puros cuando QGIS no esta instalado."""
    qgis = types.ModuleType('qgis')
    pyqt = types.ModuleType('qgis.PyQt')
    widgets = types.ModuleType('qgis.PyQt.QtWidgets')
    core = types.ModuleType('qgis.PyQt.QtCore')
    gui = types.ModuleType('qgis.PyQt.QtGui')
    qgis_core = types.ModuleType('qgis.core')

    widget_names = (
        'QWidget', 'QVBoxLayout', 'QHBoxLayout', 'QGridLayout', 'QLabel',
        'QLineEdit', 'QComboBox', 'QPushButton', 'QTableWidget',
        'QTableWidgetItem', 'QHeaderView', 'QGroupBox', 'QAbstractItemView',
        'QScrollArea', 'QFrame', 'QSizePolicy', 'QMessageBox',
        'QStackedWidget', 'QShortcut', 'QFileDialog', 'QListWidget',
        'QListWidgetItem', 'QDialog', 'QDialogButtonBox', 'QAction',
        'QPlainTextEdit', 'QProgressBar', 'QApplication',
    )
    for name in widget_names:
        setattr(widgets, name, _Widget)

    core.Qt = type('Qt', (), {})
    core.QVariant = _QVariant
    core.QSettings = _Widget
    core.QSize = _Widget
    core.QPoint = _Widget
    core.QDate = _Widget
    core.QTimer = _Widget
    gui.QKeySequence = _Widget
    gui.QColor = _Widget
    gui.QBrush = _Widget
    gui.QIcon = _Widget

    for name in (
        'QgsProject', 'QgsVectorLayer', 'QgsFeatureRequest',
        'QgsExpression', 'QgsWkbTypes', 'QgsField', 'QgsFeature',
        'QgsSpatialIndex', 'QgsRectangle', 'QgsGeometry', 'QgsVectorLayerJoinInfo', 'QgsCoordinateTransform',
        'QgsFillSymbol', 'QgsRendererCategory', 'QgsCategorizedSymbolRenderer',
        'QgsSingleSymbolRenderer', 'QgsLinePatternFillSymbolLayer',
        'QgsSimpleLineSymbolLayer',
    ):
        setattr(qgis_core, name, _Widget)

    sys.modules.update({
        'qgis': qgis,
        'qgis.PyQt': pyqt,
        'qgis.PyQt.QtWidgets': widgets,
        'qgis.PyQt.QtCore': core,
        'qgis.PyQt.QtGui': gui,
        'qgis.core': qgis_core,
    })


_install_qgis_stubs()
sys.path.insert(0, str(PACKAGE_PARENT))
dialog = importlib.import_module('GeoCatastro_Predial.consultas_dialog')
plugin_module = importlib.import_module('GeoCatastro_Predial.consultas_prediales')
merge_module = importlib.import_module('GeoCatastro_Predial.merge_dialog')
pdf_module = importlib.import_module('GeoCatastro_Predial.map_pdf_export')


class _Field:
    def __init__(self, name, field_type=_QVariant.String):
        self._name = name
        self._type = field_type

    def name(self):
        return self._name

    def type(self):
        return self._type


class _Fields:
    def __init__(self, fields):
        self._fields = fields
        self.iterations = 0

    def __iter__(self):
        self.iterations += 1
        return iter(self._fields)

    def count(self):
        return len(self._fields)

    def indexFromName(self, name):
        for index, field in enumerate(self._fields):
            if field.name() == name:
                return index
        return -1

    def field(self, index):
        return self._fields[index]


class _Layer:
    def __init__(self, fields):
        self._fields = _Fields(fields)

    def id(self):
        return 'test-layer'

    def fields(self):
        return self._fields


class CoreHelpersTest(unittest.TestCase):
    def setUp(self):
        dialog._clear_field_index()

    def test_source_is_python_36_compatible(self):
        for path in PROJECT_DIR.glob('*.py'):
            source = path.read_text(encoding='utf-8')
            ast.parse(source, filename=str(path), feature_version=(3, 6))

    def test_currency_does_not_multiply_decimal_values(self):
        expected = '$ 164.566.000'
        self.assertEqual(dialog._fmt_currency(164566000.0), expected)
        self.assertEqual(dialog._fmt_currency('164566000.0'), expected)
        self.assertEqual(dialog._fmt_currency('164.566.000'), expected)
        self.assertEqual(dialog._fmt_currency('164.566.000,00'), expected)

    def test_null_values_are_rendered_as_empty(self):
        for value in (None, '', 'NULL', 'None'):
            self.assertEqual(dialog._value_text(value), '')
            self.assertEqual(dialog._fmt_currency(value), '')

    def test_pdf_filename_is_safe_and_keeps_predial_code(self):
        self.assertEqual(
            pdf_module.safe_pdf_filename(' 18-479 / 0001 '),
            'Ficha_Predial_18-479_0001.pdf',
        )
        self.assertEqual(
            pdf_module.selection_pdf_filename(3),
            'Fichas_Prediales_3_seleccionados.pdf',
        )

    def test_pdf_extent_expands_zero_sized_geometry(self):
        xmin, ymin, xmax, ymax = pdf_module.expanded_bounds(
            100, 200, 100, 200, fallback_span=10)
        self.assertLess(xmin, 100)
        self.assertLess(ymin, 200)
        self.assertGreater(xmax, 100)
        self.assertGreater(ymax, 200)

    def test_pdf_uses_all_selected_query_features(self):
        class Feature:
            def __init__(self, feature_id):
                self._feature_id = feature_id

            def id(self):
                return self._feature_id

        class Layer:
            def selectedFeatureIds(self):
                return [3, 1]

            def getFeature(self, feature_id):
                return Feature(feature_id)

        instance = object.__new__(dialog.ConsultasPredialesDialog)
        instance.current_features = [Feature(1), Feature(2), Feature(3)]
        instance._nav_index = 0

        selected = instance._pdf_selected_features(Layer())

        self.assertEqual([feature.id() for feature in selected], [1, 3])

    def test_pdf_details_includes_predio_condition(self):
        class FeatureValues:
            def __init__(self, values):
                self._values = values

            def __getitem__(self, name):
                return self._values.get(name)

        # NOMBRE_VEREDA con valor evita que _pdf_details caiga al fallback
        # _buscar_nombre_vereda (que usa QgsProject, no disponible en este stub).
        layer = _Layer([_Field('CODIGO'), _Field('ORIGEN'), _Field('NOMBRE_VEREDA')])
        instance = object.__new__(dialog.ConsultasPredialesDialog)

        informal = FeatureValues({
            'CODIGO': '000123', 'ORIGEN': 'RURAL_INFORMAL', 'NOMBRE_VEREDA': 'Vereda Test'})
        details = dict(instance._pdf_details(informal, layer))
        self.assertEqual(details['Condicion del predio'], 'Informal')

        formal = FeatureValues({
            'CODIGO': '000124', 'ORIGEN': 'URBANO', 'NOMBRE_VEREDA': 'Vereda Test'})
        details = dict(instance._pdf_details(formal, layer))
        self.assertEqual(details['Condicion del predio'], 'Formal')

        sin_origen = FeatureValues({'CODIGO': '000125', 'NOMBRE_VEREDA': 'Vereda Test'})
        details = dict(instance._pdf_details(sin_origen, layer))
        self.assertEqual(details['Condicion del predio'], '')

    def test_field_resolution_reuses_schema_index(self):
        layer = _Layer([
            _Field('CODIGO'),
            _Field('18479-Morelia_R1_Nombre'),
            _Field('18479-Morelia_R2_Matricula Inmobiliaria'),
        ])
        for _ in range(100):
            self.assertEqual(dialog.resolve_field(layer, 'CODIGO'), 'CODIGO')
            self.assertEqual(
                dialog.resolve_field(layer, 'Nombre'),
                '18479-Morelia_R1_Nombre',
            )
            self.assertIsNone(dialog.resolve_field(layer, 'Puntaje'))
        self.assertEqual(layer.fields().iterations, 1)

    def test_expression_escapes_field_names_and_values(self):
        layer = _Layer([_Field('Owner"Name')])
        expression = dialog.build_like(layer, 'Owner"Name', "O'Brien")
        self.assertEqual(expression, '"Owner""Name" ILIKE \'%O\'\'Brien%\'')

    def test_visible_fields_prioritizes_tipo_unidad_and_origen(self):
        layer = _Layer([
            _Field('CODIGO'),
            _Field('CODIGO_ANTERIOR'),
            _Field('ORIGEN'),
            _Field('TIPO_UNIDAD'),
            _Field('CLASE'),
            _Field('NOMBRE_VEREDA'),
            _Field('R1_Nombre'),
        ])
        instance = object.__new__(dialog.ConsultasPredialesDialog)
        result = instance._visible_fields(layer)
        names = [fn for fn, _label in result]
        self.assertEqual(names[:3], ['CODIGO', 'TIPO_UNIDAD', 'ORIGEN'])
        labels = dict(result)
        self.assertEqual(labels['TIPO_UNIDAD'], 'Tipo de unidad')
        self.assertEqual(labels['ORIGEN'], 'Origen')
        self.assertEqual(labels['CLASE'], 'Clasificación')

    def test_visible_fields_inserts_priority_fields_first_without_codigo(self):
        layer = _Layer([
            _Field('ORIGEN'),
            _Field('TIPO_UNIDAD'),
            _Field('NOMBRE_VEREDA'),
        ])
        instance = object.__new__(dialog.ConsultasPredialesDialog)
        result = instance._visible_fields(layer)
        names = [fn for fn, _label in result]
        self.assertEqual(names[:2], ['TIPO_UNIDAD', 'ORIGEN'])

    def test_direct_merge_detects_standard_gdb_layers(self):
        names = [
            'Catastro_Urbano.U_TERRENO',
            'Catastro_Rural.R_TERRENO',
            'Catastro_Rural.R_VEREDA',
            'U_CONSTRUCCION',
        ]
        self.assertEqual(
            merge_module._pick_layer_name(names, 'urban'),
            'Catastro_Urbano.U_TERRENO',
        )
        self.assertEqual(
            merge_module._pick_layer_name(names, 'rural'),
            'Catastro_Rural.R_TERRENO',
        )
        self.assertEqual(
            merge_module._pick_layer_name(names, 'vereda'),
            'Catastro_Rural.R_VEREDA',
        )

    def test_direct_merge_detects_standard_manzana_layer(self):
        names = [
            'Catastro_Urbano.U_MANZANA',
            'Catastro_Rural.R_VEREDA',
            'Catastro_Urbano.U_TERRENO',
        ]
        self.assertEqual(
            merge_module._pick_layer_name(names, 'manzana'),
            'Catastro_Urbano.U_MANZANA',
        )

    def test_query_prefers_consolidated_territorial_code(self):
        layer = _Layer([
            _Field('VEREDA_CODIGO'),
            _Field('MANZANA_CODIGO'),
            _Field('MANZANA_VEREDA_CODIGO'),
        ])
        self.assertEqual(
            dialog.resolve_field(layer, 'VEREDA_CODIGO'),
            'MANZANA_VEREDA_CODIGO',
        )

    def test_direct_merge_does_not_confuse_urban_and_rural(self):
        names = ['TERRENO_RURAL', 'TERRENO_URBANO']
        self.assertEqual(
            merge_module._pick_layer_name(names, 'urban'), 'TERRENO_URBANO')
        self.assertEqual(
            merge_module._pick_layer_name(names, 'rural'), 'TERRENO_RURAL')

    def test_direct_merge_includes_informal_terrain_without_replacing_formal(self):
        names = [
            'U_TERRENO_INFORMAL', 'R_TERRENO_INFORMAL',
            'U_TERRENO', 'R_TERRENO',
        ]
        self.assertEqual(
            merge_module._pick_layer_name(names, 'urban'), 'U_TERRENO')
        self.assertEqual(
            merge_module._pick_layer_name(names, 'rural'), 'R_TERRENO')
        self.assertEqual(
            merge_module._pick_layer_name(names, 'urban_informal'),
            'U_TERRENO_INFORMAL',
        )
        self.assertEqual(
            merge_module._pick_layer_name(names, 'rural_informal'),
            'R_TERRENO_INFORMAL',
        )

    def test_direct_merge_detects_construction_layers(self):
        names = [
            'U_CONSTRUCCION', 'R_CONSTRUCCION',
            'U_CONSTRUCCION_INFORMAL', 'R_CONSTRUCCION_INFORMAL',
            'U_TERRENO', 'R_TERRENO',
        ]
        self.assertEqual(
            merge_module._pick_layer_name(names, 'urban_construction'),
            'U_CONSTRUCCION')
        self.assertEqual(
            merge_module._pick_layer_name(names, 'rural_construction'),
            'R_CONSTRUCCION')
        self.assertEqual(
            merge_module._pick_layer_name(names, 'urban_construction_informal'),
            'U_CONSTRUCCION_INFORMAL')
        self.assertEqual(
            merge_module._pick_layer_name(names, 'rural_construction_informal'),
            'R_CONSTRUCCION_INFORMAL')

    def test_bottom_merge_button_routes_ready_direct_files(self):
        instance = object.__new__(merge_module.MergeConsolidacionDialog)
        instance._direct_paths = {
            'gdb': 'catastro.gdb', 'r1': 'R1.xlsx', 'r2': 'R2.xlsx'}
        instance._direct_processing = False
        for name in (
                'cbo_urb', 'cbo_rur', 'cbo_urb_inf', 'cbo_rur_inf',
                'cbo_constr_urb', 'cbo_constr_rur',
                'cbo_constr_urb_inf', 'cbo_constr_rur_inf',
                'cbo_manz', 'cbo_ver', 'cbo_r1', 'cbo_r2'):
            setattr(instance, name, object())
        instance._layer = lambda _combo: None
        calls = []
        instance._process_direct_selection = lambda: calls.append('direct')

        merge_module.MergeConsolidacionDialog._run(instance)

        self.assertEqual(calls, ['direct'])

    def test_record_join_prioritizes_numero_predial(self):
        layer = _Layer([
            _Field('CODIGO'),
            _Field('Numero Predial'),
            _Field('NOMBRE'),
        ])
        self.assertEqual(
            merge_module._resolve(layer, merge_module._RECORD_PREDIAL_CANDS),
            'Numero Predial',
        )

    def test_predial_join_key_normalizes_format_differences(self):
        self.assertEqual(
            merge_module._norm_predial_code(' 18-479 01.00 '),
            '184790100',
        )
        self.assertEqual(merge_module._norm_predial_code(1847901.0), '1847901')

    def test_active_layer_selector_only_accepts_join_results(self):
        class Layer:
            def __init__(self, name, marker=False):
                self._name = name
                self._marker = marker

            def name(self):
                return self._name

            def customProperty(self, _key, default):
                return self._marker if self._marker is not None else default

        self.assertTrue(dialog._is_query_result_layer(
            Layer('Resultado personalizado', True)))
        self.assertTrue(dialog._is_query_result_layer(
            Layer('Predios_Consolidados')))
        self.assertFalse(dialog._is_query_result_layer(Layer('R1')))
        self.assertFalse(dialog._is_query_result_layer(Layer('Terreno Urbano')))

    def test_excel_formula_injection_is_neutralized(self):
        for value in ('=1+1', '+SUM(A1:A2)', '-2+3', '@CMD', '\t=1', '\r=1'):
            self.assertTrue(dialog._excel_safe_text(value).startswith("'"))
        self.assertEqual(dialog._excel_safe_text('123456'), '123456')

    def test_sanitized_xlsx_cell_is_not_a_formula(self):
        try:
            import openpyxl
        except ImportError:
            self.skipTest('openpyxl no esta instalado')
        workbook = openpyxl.Workbook()
        cell = workbook.active.cell(1, 1, dialog._excel_safe_text('=1+1'))
        cell.data_type = 's'
        stream = io.BytesIO()
        workbook.save(stream)
        stream.seek(0)
        loaded = openpyxl.load_workbook(stream, data_only=False)
        loaded_cell = loaded.active.cell(1, 1)
        self.assertEqual(loaded_cell.data_type, 's')
        self.assertEqual(loaded_cell.value, "'=1+1")

    def test_feature_query_is_bounded(self):
        class Request:
            NoGeometry = 1

            def __init__(self):
                self.limit = None
                self.flags = None
                self.expression = None

            def setFilterExpression(self, expression):
                self.expression = expression

            def setFlags(self, flags):
                self.flags = flags

            def setLimit(self, limit):
                self.limit = limit

        class Layer:
            def __init__(self):
                self.request = None

            def getFeatures(self, request):
                self.request = request
                return iter(range(6000))

        original_request = dialog.QgsFeatureRequest
        dialog.QgsFeatureRequest = Request
        try:
            instance = object.__new__(dialog.ConsultasPredialesDialog)
            layer = Layer()
            features, truncated = instance._fetch_features(layer, '"CODIGO" = 1')
        finally:
            dialog.QgsFeatureRequest = original_request

        self.assertTrue(truncated)
        self.assertEqual(len(features), instance.MAX_QUERY_RESULTS)
        self.assertEqual(layer.request.limit, instance.MAX_QUERY_RESULTS + 1)
        self.assertEqual(layer.request.flags, Request.NoGeometry)
        self.assertEqual(layer.request.expression, '"CODIGO" = 1')

    def test_plugin_unload_releases_dialog(self):
        class Iface:
            def __init__(self):
                self.menu_removed = False
                self.icon_removed = False

            def removePluginVectorMenu(self, _menu, _action):
                self.menu_removed = True

            def removeToolBarIcon(self, _action):
                self.icon_removed = True

        class Dialog:
            def __init__(self):
                self.stopped = False

            def shutdown(self):
                self.stopped = True

        plugin = object.__new__(plugin_module.ConsultasPrediales)
        plugin.iface = Iface()
        plugin.info_logo = None
        plugin.action = object()
        old_dialog = Dialog()
        plugin.dialog = old_dialog
        plugin.unload()

        self.assertTrue(old_dialog.stopped)
        self.assertTrue(plugin.iface.menu_removed)
        self.assertTrue(plugin.iface.icon_removed)
        self.assertIsNone(plugin.dialog)
        self.assertIsNone(plugin.action)

    def test_plugin_toggle_hides_all_windows(self):
        class Dialog:
            def __init__(self):
                self.hidden = False

            def isVisible(self):
                return True

            def hide_windows(self):
                self.hidden = True

        plugin = object.__new__(plugin_module.ConsultasPrediales)
        plugin.dialog = Dialog()
        plugin.toggle_dock()
        self.assertTrue(plugin.dialog.hidden)


if __name__ == '__main__':
    unittest.main()
