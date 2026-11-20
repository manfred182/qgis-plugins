import importlib
import sys
import unittest
from pathlib import Path

# El paquete del plugin toma el nombre de su carpeta raíz, sea cual sea
# ("semaforo_cartera_qgis", "Semaforo_Cartera_Predial", etc.). Se resuelve de
# forma dinámica para que las pruebas no dependan de cómo se llame la carpeta.
_PLUGIN_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PLUGIN_DIR.parent))
_core = importlib.import_module(_PLUGIN_DIR.name + '.gdb_join_core')

_EXPORTS = (
    'SRC_GDB', 'SRC_R1', 'SRC_R2', 'build_combined_index',
    'build_export_analytics', 'check_municipality_license',
    'dominant_municipality', 'municipality_matches_license',
    'municipality_of_code', 'build_key_index', 'classify_terrain_source',
    'combined_matches', 'concat_key_variants', 'ensure_unique_prefixes',
    'is_code_segment_name', 'inspect_predial_key', 'find_best_join_keys',
    'left_join_rows_automatic', 'row_has_key', 'partition_predial_rows',
    'stack_attribute_sources', 'summarize_presence_matches', 'match_indexes',
    'merge_field_definitions', 'type_rank', 'unmatched_right_groups',
)
globals().update({name: getattr(_core, name) for name in _EXPORTS})


class FieldMergeTests(unittest.TestCase):
    def test_merge_picks_dominant_type(self):
        gdb = [('FICHA', 'Integer', SRC_GDB)]
        r1 = [('FICHA', 'String', SRC_R1)]
        merged = merge_field_definitions([gdb, r1])
        # Integer es más capaz que String para un código numérico.
        self.assertEqual(merged, [('FICHA', 'Integer')])

    def test_merge_keeps_first_order_and_union(self):
        gdb = [('CODPREDIAL', 'String', SRC_GDB), ('AREA', 'Double', SRC_GDB)]
        r1 = [('PROPIETARIO', 'String', SRC_R1)]
        merged = merge_field_definitions([gdb, r1])
        names = [name for name, _ in merged]
        self.assertEqual(names, ['CODPREDIAL', 'AREA', 'PROPIETARIO'])

    def test_type_rank_prefers_numeric_over_text(self):
        self.assertGreater(type_rank('Double'), type_rank('String'))
        self.assertGreater(type_rank('Integer'), type_rank('String'))
        self.assertGreater(type_rank('String'), type_rank('Boolean'))


class PrefixTests(unittest.TestCase):
    def test_collisions_are_prefixed_but_singles_keep_name(self):
        combined = ensure_unique_prefixes([
            (SRC_GDB, {'FICHA': 1, 'NOMBRE': 'terreno'}),
            (SRC_R1, {'FICHA': 2, 'SALDO': 100}),
        ])
        # 'FICHA' aparece dos veces -> se desambigua con prefijo.
        self.assertNotIn('FICHA', combined)
        self.assertIn('GDB_FICHA', combined)
        self.assertIn('R1_FICHA', combined)
        # Singles conservan su nombre.
        self.assertEqual(combined['NOMBRE'], 'terreno')
        self.assertEqual(combined['SALDO'], 100)


class IndexTests(unittest.TestCase):
    def test_build_and_match_by_code_predial(self):
        # La llave es el código predial (30 dígitos), tolerando formato texto.
        gdb_rows = [
            ['184790001000000010001000000000', 'Predio A'],
            ['000123', 'Predio B'],
            ['999999999999999999999999999999', 'Predio C'],
        ]
        r1_rows = [
            ['184790001000000010001000000000', 500],
            ['123', 700],  # 000123 == 123 (cero a la izquierda)
            ['777', 0],
        ]
        index = build_key_index(r1_rows, [0])
        matched = match_indexes(gdb_rows, [0], index)
        # Predio A cruza con R1 fila 0; Predio B con R1 fila 1; Predio C no cruza.
        self.assertEqual(matched[0], {0})
        self.assertEqual(matched[1], {1})
        self.assertEqual(matched[2], set())

    def test_ignores_empty_keys(self):
        index = build_key_index([['', 1]], [0])
        self.assertEqual(index, {})


class ConcatTests(unittest.TestCase):
    def test_concat_joins_segments_without_separators(self):
        # Número predial de 30 dígitos repartido: municipio(5)+vereda(4)+... 
        variants = concat_key_variants(['18479', '0001', '000000001', '0001000000'])
        self.assertIn('1847900010000000010001000000', variants)

    def test_concat_preserves_leading_zeros(self):
        variants = concat_key_variants(['0001', '02', '0003'])
        self.assertIn('0001020003', variants)

    def test_concat_strips_spaces_but_not_zeros(self):
        variants = concat_key_variants(['18 479', '0001'])
        self.assertIn('184790001', variants)

    def test_concat_empty_is_empty_set(self):
        self.assertEqual(concat_key_variants(['', None, '  ']), set())


class PredialCodeValidationTests(unittest.TestCase):
    def test_accepts_20_and_30_digit_predial_codes(self):
        code_20 = '18479010000059001002'
        code_30 = '184790100000000090038200000001'
        self.assertEqual(inspect_predial_key([code_20], [0])['state'], 'valid')
        self.assertEqual(inspect_predial_key([code_30], [0])['state'], 'valid')

    def test_accepts_visual_separators(self):
        result = inspect_predial_key(['18479-01000-0059001002'], [0])
        self.assertEqual(result['state'], 'valid')
        self.assertEqual(result['normalized'], '18479010000059001002')

    def test_distinguishes_empty_from_illegible(self):
        self.assertEqual(inspect_predial_key(['  '], [0])['state'], 'empty')
        result = inspect_predial_key(['18479ABC'], [0])
        self.assertEqual(result['state'], 'invalid')
        self.assertIn('caracteres', result['reason'])

    def test_reports_an_invalid_length(self):
        result = inspect_predial_key(['12345'], [0])
        self.assertEqual(result['state'], 'invalid')
        self.assertIn('Longitud', result['reason'])

    def test_partitions_rows_without_reporting_empty_codes(self):
        valid, empty, invalid = partition_predial_rows([
            ['18479010000059001002'], [''], ['CODIGO-ROTO'],
        ], [0])
        self.assertEqual(valid, [0])
        self.assertEqual(empty, [1])
        self.assertEqual([item['row_index'] for item in invalid], [2])


class ExportAnalyticsTests(unittest.TestCase):
    def test_builds_financial_balance_by_status_class_vereda_and_period(self):
        fields = [
            'GDB_CODIGO', 'GDB_VEREDA_CODIGO', 'PRED_AMBITO',
            'PRED_FORMALIDAD', 'PRED_CLASE', 'PRED_LOCALIZADO',
            'CART_ESTADO', 'CART_SALDO', 'CART_PERIODO',
            'CARTERA_PROPIETARIO',
        ]
        rows = [
            ['001', 'V01', 'RURAL', 'FORMAL', 'RURAL FORMAL', 'SI',
             'EN DEUDA', 1000, '2020-2024', 'Ana'],
            ['002', 'V01', 'RURAL', 'FORMAL', 'RURAL FORMAL', 'SI',
             'PAZ Y SALVO', None, '', 'Luis'],
            ['003', 'V02', 'RURAL', 'INFORMAL', 'RURAL INFORMAL', 'NO',
             'EN DEUDA', 500, '2024', 'Marta'],
        ]
        result = build_export_analytics(fields, rows)
        self.assertEqual(result['total'], 3)
        self.assertEqual(result['debt_count'], 2)
        self.assertEqual(result['clear_count'], 1)
        self.assertEqual(result['debt_total'], 1500)
        self.assertEqual(result['debt_average'], 750)
        self.assertEqual(result['by_vereda']['V01']['debt'], 1)
        self.assertEqual(result['by_vereda']['V01']['clear'], 1)
        self.assertEqual(result['by_vereda']['V01']['balance'], 1000)
        self.assertEqual(result['by_period']['2024']['balance'], 500)
        self.assertEqual(result['top_debtors'][0]['owner'], 'Ana')

    def test_summarizes_clear_predios_veredas_manzanas_and_dimensions(self):
        fields = [
            'GDB_CODIGO', 'GDB_VEREDA_CODIGO', 'GDB_VEREDA_NOMBRE',
            'GDB_MANZANA_CODIGO', 'PRED_AMBITO', 'PRED_FORMALIDAD',
            'PRED_CLASE', 'PRED_LOCALIZADO', 'R2_Estrato',
            'R1_DestinoEconomico', 'CART_ESTADO', 'CART_SALDO',
            'CART_PERIODO', 'CARTERA_PROPIETARIO', 'R1_Nombre', 'R1_Avaluo_($)',
        ]
        rows = [
            ['001', 'V01', 'Buenavista', 'NULL', 'RURAL', 'FORMAL',
             'RURAL FORMAL', 'SI', '0', 'A', 'EN DEUDA', 1000, '2026',
             'Ana', 'Ana', 5000],
            ['002', 'V01', 'Buenavista', 'NULL', 'RURAL', 'FORMAL',
             'RURAL FORMAL', 'SI', '0', 'A', 'PAZ Y SALVO', 0, '2026',
             'NULL', 'Luis', 9000],
            ['003', 'NULL', '', 'M07', 'URBANO', 'FORMAL', 'URBANO FORMAL',
             'SI', '3', 'L', 'PAZ Y SALVO', 0, '2026', 'NULL', 'Marta', 12000],
        ]
        result = build_export_analytics(fields, rows)
        self.assertEqual(result['clear_count'], 2)
        self.assertEqual(len(result['clear_predios']), 2)
        # El propietario del paz y salvo se toma de R1, no de la cartera vacía.
        self.assertEqual({p['owner'] for p in result['clear_predios']},
                         {'Luis', 'Marta'})
        # Vereda con nombre; la manzana urbana se cuenta aparte.
        self.assertEqual(result['by_vereda']['V01']['name'], 'Buenavista')
        self.assertEqual(result['by_vereda']['V01']['clear'], 1)
        self.assertEqual(result['by_manzana']['M07']['clear'], 1)
        self.assertNotIn('NULL', result['by_manzana'])
        # La vigencia actual agrupa deudores y paz y salvo del ejercicio.
        self.assertEqual(result['by_period']['2026']['debt'], 1)
        self.assertEqual(result['by_period']['2026']['clear'], 2)
        # Estrato y destino económico desglosados.
        self.assertIn('3', result['by_estrato'])
        self.assertEqual(result['by_destino']['A']['total'], 2)
        # Territorio unificado: vereda por nombre + manzana urbana.
        self.assertIn('Buenavista', result['by_territory'])
        self.assertIn('MZ M07', result['by_territory'])

    def test_combined_index_matches_by_code(self):
        gdb = [['18479', '02', 'Predio A'], ['99999', '99', 'Predio B']]
        r1 = [['18479', '02', 500], ['12345', '00', 0]]
        index = build_combined_index(r1, [0, 1])
        self.assertEqual(combined_matches(gdb, [0, 1], index)[0], {0})
        self.assertEqual(combined_matches(gdb, [0, 1], index)[1], set())

    def test_combined_index_matches_single_field_too(self):
        # El caso mixto: en un origen el código está en UN campo y en otro en VARIOS.
        codigo = '184790020000000010001000000'  # concatenación exacta de r1
        gdb = [[codigo, 'Predio A']]
        r1 = [['18479', '002', '000000001', '0001000000', 700]]
        # Concatenar los 4 segmentos debe dar el código completo.
        index = build_combined_index(r1, [0, 1, 2, 3])
        self.assertEqual(combined_matches(gdb, [0], index)[0], {0})

    def test_code_segment_hints(self):
        self.assertTrue(is_code_segment_name('MUNICIPIO'))
        self.assertTrue(is_code_segment_name('CÓDIGO VEREDA'))
        self.assertTrue(is_code_segment_name('MANZANA'))
        self.assertFalse(is_code_segment_name('NOMBRE_PROPIETARIO'))


class AutomaticJoinTests(unittest.TestCase):
    def test_matches_reference_rows_against_right_table(self):
        left = [['001', 'Predio A'], ['002', 'Predio B']]
        right = [['002', 200], ['001', 100], ['999', 900]]
        joined, result = left_join_rows_automatic(
            ['GDB_CODIGO', 'GDB_NOMBRE'], left,
            ['R1_CODIGO', 'R1_SALDO'], right,
        )
        self.assertEqual(result['matched_left'], 2)
        self.assertEqual(joined[0][-1], 100)
        self.assertEqual(joined[1][-1], 200)

    def test_automatic_join_can_chain_codigo_to_codigo_predial(self):
        gdb_fields = ['GDB_CODIGO', 'GDB_NOMBRE']
        gdb_rows = [['A-01', 'Predio A'], ['B-02', 'Predio B']]
        r1_fields = ['R1_CODIGO', 'R1_CODIGO_PREDIAL']
        r1_rows = [
            ['A-01', '184790001000000010001000000000'],
            ['B-02', '184790001000000010002000000000'],
        ]
        first_rows, first = left_join_rows_automatic(
            gdb_fields, gdb_rows, r1_fields, r1_rows,
        )
        self.assertEqual(first['left_columns'], (0,))
        self.assertEqual(first['right_columns'], (0,))

        merged_fields = gdb_fields + r1_fields
        cartera_fields = ['R2_CODIGO_PREDIAL', 'R2_SALDO']
        cartera_rows = [['184790001000000010001000000000', 4500]]
        final_rows, second = left_join_rows_automatic(
            merged_fields, first_rows, cartera_fields, cartera_rows,
        )
        self.assertEqual(second['left_columns'], (3,))
        self.assertEqual(second['right_columns'], (0,))
        self.assertEqual(final_rows[0][-1], 4500)
        self.assertIsNone(final_rows[1][-1])

    def test_duplicate_report_rows_are_consolidated_in_one_feature(self):
        joined, result = left_join_rows_automatic(
            ['CODIGO_PREDIAL'], [['001']],
            ['CODIGO_PREDIAL', 'PROPIETARIO', 'SALDO'],
            [['001', 'Ana', 100], ['001', 'Luis', 250]],
        )
        self.assertEqual(len(joined), 1)
        self.assertEqual(result['matched_right'], 2)
        self.assertEqual(joined[0][2], 'Ana | Luis')
        self.assertEqual(joined[0][3], '100 | 250')

    def test_finds_best_keys_using_real_overlap(self):
        result = find_best_join_keys(
            ['GDB_CODIGO', 'GDB_CODIGO_PREDIAL'],
            [['A1', 'sin-cruce'], ['A2', 'sin-cruce-2']],
            ['R1_CODIGO', 'R1_CODIGO_PREDIAL'],
            [['A1', 'otro'], ['A2', 'otro-2']],
        )
        self.assertEqual(result['left_columns'], (0,))
        self.assertEqual(result['right_columns'], (0,))

    def test_does_not_join_every_predio_by_municipality(self):
        result = find_best_join_keys(
            ['GDB_CODIGO', 'GDB_CODIGO_MUNICIPIO', 'GDB_CODIGO_DEPARTAMENTO'],
            [
                ['184790001000000010001000000000', '18479', '18'],
                ['184790001000000010002000000000', '18479', '18'],
            ],
            ['R1_Numero_Predial', 'R1_Municipio', 'R1_Departamento'],
            [
                ['184790001000000010001000000000', '479', '18'],
                ['184790001000000010002000000000', '479', '18'],
                ['184790001000000019999000000000', '479', '18'],
            ],
        )
        self.assertEqual(result['left_columns'], (0,))
        self.assertEqual(result['right_columns'], (0,))
        self.assertEqual(result['matched_left'], 2)

    def test_stacks_rural_urban_and_informal_terrain(self):
        fields, rows = stack_attribute_sources([
            ('R_TERRENO', ['GDB_CODIGO', 'GDB_VEREDA'], [['R01', 'V1']]),
            ('U_TERRENO', ['GDB_CODIGO', 'GDB_MANZANA'], [
                ['U01', 'M1'], ['U02', 'M2'],
            ]),
        ])
        self.assertEqual(fields, [
            'GDB_CAPA_ORIGEN', 'GDB_CODIGO', 'GDB_VEREDA', 'GDB_MANZANA',
        ])
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0], ['R_TERRENO', 'R01', 'V1', None])
        self.assertEqual(rows[1], ['U_TERRENO', 'U01', None, 'M1'])

    def test_row_has_key_distinguishes_blank_identifier(self):
        self.assertTrue(row_has_key(['001', 'Predio'], [0]))
        self.assertFalse(row_has_key(['', 'Predio'], [0]))

    def test_cartera_summary_drives_semaphore_fields(self):
        left = [['001'], ['002'], ['']]
        report = [
            ['001', 100, 'Ana', 2020, 2022],
            ['001', 250, 'Luis', 2019, 2024],
        ]
        _, match = left_join_rows_automatic(
            ['GDB_CODIGO'], left,
            ['CARTERA_NUMERO_PREDIAL', 'SALDO', 'PROPIETARIO', 'DESDE', 'HASTA'],
            report,
        )
        summaries = summarize_presence_matches(
            left, match, report,
            value_column=1, owner_column=2, desde_column=3, hasta_column=4,
        )
        self.assertEqual(summaries[0]['status'], 'deuda')
        self.assertEqual(summaries[0]['total_debt'], 350)
        self.assertEqual(summaries[0]['obligation_count'], 2)
        self.assertEqual(summaries[0]['period'], '2019-2024')
        self.assertEqual(summaries[1]['status'], 'paz')
        self.assertEqual(summaries[2]['status'], 'sin_info')

    def test_paz_y_salvo_takes_current_report_vigencia(self):
        left = [['001'], ['002']]
        report = [['001', 100, 'Ana', 2020, 2022]]
        _, match = left_join_rows_automatic(
            ['GDB_CODIGO'], left,
            ['CARTERA_NUMERO_PREDIAL', 'SALDO', 'PROPIETARIO', 'DESDE', 'HASTA'],
            report,
        )
        summaries = summarize_presence_matches(
            left, match, report,
            value_column=1, owner_column=2, desde_column=3, hasta_column=4,
            current_year=2026,
        )
        # El deudor conserva la vigencia real que trae la cartera.
        self.assertEqual(summaries[0]['status'], 'deuda')
        self.assertEqual(summaries[0]['period'], '2020-2022')
        # El predio a paz y salvo recibe la vigencia actual del ejercicio.
        self.assertEqual(summaries[1]['status'], 'paz')
        self.assertEqual(summaries[1]['period'], '2026')
        self.assertEqual(summaries[1]['vig_desde'], 2026)
        self.assertEqual(summaries[1]['vig_hasta'], 2026)

    def test_paz_y_salvo_without_current_year_stays_blank(self):
        left = [['001'], ['002']]
        report = [['001', 100, 'Ana', 2020, 2022]]
        _, match = left_join_rows_automatic(
            ['GDB_CODIGO'], left,
            ['CARTERA_NUMERO_PREDIAL', 'SALDO', 'PROPIETARIO', 'DESDE', 'HASTA'],
            report,
        )
        summaries = summarize_presence_matches(
            left, match, report,
            value_column=1, owner_column=2, desde_column=3, hasta_column=4,
        )
        # Sin año del ejercicio, el paz y salvo sigue sin vigencia (compatible).
        self.assertEqual(summaries[1]['status'], 'paz')
        self.assertEqual(summaries[1]['period'], '')

    def test_classifies_all_four_terrain_populations(self):
        self.assertEqual(
            classify_terrain_source('R_TERRENO'),
            ('RURAL', 'FORMAL', 'RURAL FORMAL'),
        )
        self.assertEqual(
            classify_terrain_source('U_TERRENO'),
            ('URBANO', 'FORMAL', 'URBANO FORMAL'),
        )
        self.assertEqual(
            classify_terrain_source('R_TERRENO_INFORMAL'),
            ('RURAL', 'INFORMAL', 'RURAL INFORMAL'),
        )
        self.assertEqual(
            classify_terrain_source('U_TERRENO_INFORMAL'),
            ('URBANO', 'INFORMAL', 'URBANO INFORMAL'),
        )

    def test_unmatched_cartera_rows_are_grouped_by_predial_code(self):
        left = [['001'], ['002']]
        report = [
            ['001', 100],
            ['003', 200],
            ['003', 50],
            ['004', 300],
        ]
        _, match = left_join_rows_automatic(
            ['GDB_CODIGO'], left,
            ['CARTERA_NUMERO_PREDIAL', 'SALDO'], report,
        )
        groups = unmatched_right_groups(match, report)
        self.assertEqual(groups, [{1, 2}, {3}])


class MunicipalityLicenseTests(unittest.TestCase):
    # 30 dígitos: departamento 18 + municipio 479 (Morelia) + resto.
    MORELIA = '184790002000000190006000000000'
    OTRO = '180010002000000190006000000000'  # Florencia (18001)

    def test_municipality_of_code_uses_first_five_digits(self):
        self.assertEqual(municipality_of_code(self.MORELIA), '18479')
        self.assertEqual(municipality_of_code(self.OTRO), '18001')
        self.assertEqual(municipality_of_code('123'), '')  # longitud inválida
        self.assertEqual(municipality_of_code('NULL'), '')

    def test_license_authorizes_only_morelia(self):
        self.assertTrue(municipality_matches_license('18479'))
        self.assertFalse(municipality_matches_license('18001'))
        self.assertFalse(municipality_matches_license(''))

    def test_dominant_municipality_ignores_stray_codes(self):
        rows = [[self.MORELIA], [self.MORELIA], [self.OTRO]]
        code, count, total = dominant_municipality(rows, [0])
        self.assertEqual(code, '18479')
        self.assertEqual((count, total), (2, 3))

    def test_check_license_blocks_other_municipality(self):
        morelia = [[self.MORELIA] for _ in range(9)]
        ok, code, ratio = check_municipality_license(morelia, [0])
        self.assertTrue(ok)
        self.assertEqual(code, '18479')

        otro = [[self.OTRO] for _ in range(9)] + [[self.MORELIA]]
        ok, code, ratio = check_municipality_license(otro, [0])
        self.assertFalse(ok)
        self.assertEqual(code, '18001')

    def test_check_license_needs_minimum_ratio(self):
        # Mitad y mitad: no alcanza el mínimo para habilitar por Morelia.
        mixed = [[self.MORELIA], [self.OTRO]]
        ok, _, ratio = check_municipality_license(mixed, [0], min_ratio=0.6)
        self.assertFalse(ok)
        self.assertEqual(ratio, 0.5)


if __name__ == '__main__':
    unittest.main()
