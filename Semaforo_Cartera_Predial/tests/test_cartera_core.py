import importlib
import sys
import unittest
from pathlib import Path

# El paquete del plugin toma el nombre de su carpeta raíz (ver test_gdb_join_core).
_PLUGIN_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PLUGIN_DIR.parent))
_core = importlib.import_module(_PLUGIN_DIR.name + '.cartera_core')

_EXPORTS = (
    'MODE_PRESENCE', 'aggregate_status', 'classify_value', 'count_matches',
    'key_variants', 'parse_number', 'summarize_obligations',
)
globals().update({name: getattr(_core, name) for name in _EXPORTS})


class CarteraCoreTests(unittest.TestCase):
    def test_preserves_original_and_matches_numeric_code(self):
        variants = key_variants('000123')
        self.assertIn('000123', variants)
        self.assertIn('123', variants)

    def test_matches_integer_exported_as_decimal(self):
        self.assertIn('123', key_variants('123.0'))

    def test_matches_integer_exported_as_scientific_notation(self):
        self.assertIn('123000', key_variants('1.23E+5'))

    def test_parses_colombian_currency(self):
        self.assertEqual(parse_number('$ 1.234.567,89'), 1234567.89)

    def test_parses_english_currency(self):
        self.assertEqual(parse_number('1,234,567.89'), 1234567.89)

    def test_distinguishes_decimal_and_thousands_dot(self):
        self.assertEqual(parse_number('1.234'), 1234.0)
        self.assertEqual(parse_number('12.50'), 12.5)

    def test_parses_negative_accounting_value(self):
        self.assertEqual(parse_number('($ 1.250,50)'), -1250.5)

    def test_classifies_numeric_and_text_values(self):
        self.assertEqual(classify_value('2500', 0), 'deuda')
        self.assertEqual(classify_value('0', 0), 'paz')
        self.assertEqual(classify_value('Paz y salvo', 0), 'paz')
        self.assertEqual(classify_value('En mora', 0), 'deuda')
        self.assertEqual(classify_value('AL DÍA', 0), 'paz')
        self.assertEqual(classify_value('', 0), 'sin_info')

    def test_debt_dominates_multiple_obligations(self):
        self.assertEqual(aggregate_status(['paz', 'deuda', 'paz']), 'deuda')
        self.assertEqual(aggregate_status(['paz', 'paz']), 'paz')
        self.assertEqual(aggregate_status([]), 'sin_info')

    def test_summarizes_multiple_obligations(self):
        summary = summarize_obligations(['1.000', '250,50', 'PAGADO'], 0)
        self.assertEqual(summary['status'], 'deuda')
        self.assertEqual(summary['obligation_count'], 3)
        self.assertEqual(summary['debt_count'], 2)
        self.assertEqual(summary['total_debt'], 1250.5)

    def test_presence_mode_marks_any_match_as_debt(self):
        summary = summarize_obligations(['404114'], 0, mode=MODE_PRESENCE)
        self.assertEqual(summary['status'], 'deuda')
        self.assertEqual(summary['debt_count'], 1)
        self.assertEqual(summary['total_debt'], 404114.0)

    def test_presence_mode_zero_balance_is_still_debt(self):
        # Aparecer en el reporte implica deuda aunque el saldo sea cero.
        summary = summarize_obligations(['0'], 0, mode=MODE_PRESENCE)
        self.assertEqual(summary['status'], 'deuda')
        self.assertEqual(summary['obligation_count'], 1)

    def test_presence_mode_no_match_with_code_is_clear(self):
        summary = summarize_obligations([], 0, mode=MODE_PRESENCE, has_key=True)
        self.assertEqual(summary['status'], 'paz')
        self.assertEqual(summary['total_debt'], 0.0)

    def test_presence_mode_no_match_without_code_is_unknown(self):
        summary = summarize_obligations([], 0, mode=MODE_PRESENCE, has_key=False)
        self.assertEqual(summary['status'], 'sin_info')

    def test_presence_mode_sums_every_matched_balance(self):
        summary = summarize_obligations(['1.000', '250,50'], 0, mode=MODE_PRESENCE)
        self.assertEqual(summary['debt_count'], 2)
        self.assertEqual(summary['total_debt'], 1250.5)

    def test_count_matches_finds_overlap_ignoring_format(self):
        index = set()
        for code in ('184790001000000010001000000000', '000123'):
            index |= key_variants(code)
        layer_values = [
            '184790001000000010001000000000',  # cruza exacto
            123,                                # cruza pese al formato entero
            '999999999999999999999999999999',  # no cruza
            None,                               # sin código
        ]
        self.assertEqual(count_matches(layer_values, index), 2)

    def test_count_matches_without_index_is_zero(self):
        self.assertEqual(count_matches(['123', '456'], set()), 0)


if __name__ == '__main__':
    unittest.main()
