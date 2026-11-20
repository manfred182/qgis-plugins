"""Prueba de humo para ejecutar con el Python incluido en QGIS."""

import os
import sys
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from qgis.core import (  # noqa: E402
    QgsApplication,
    QgsExpression,
    QgsFeature,
    QgsField,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant  # noqa: E402


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR.parent))


def main():
    app = QgsApplication([], False)
    app.initQgis()
    try:
        from GeoCatastro_Predial.consultas_dialog import (
            ConsultasPredialesDialog,
            build_like,
            resolve_field,
        )

        layer = QgsVectorLayer('None', 'Prueba segura', 'memory')
        provider = layer.dataProvider()
        provider.addAttributes([
            QgsField('CODIGO', QVariant.String),
            QgsField('18479-Morelia_R1_Nombre', QVariant.String),
        ])
        layer.updateFields()

        feature = QgsFeature(layer.fields())
        feature.setAttributes(['001234', "O'Brien"])
        provider.addFeature(feature)

        assert resolve_field(layer, 'CODIGO') == 'CODIGO'
        assert resolve_field(layer, 'Nombre') == '18479-Morelia_R1_Nombre'
        expression = build_like(layer, 'Nombre', "O'Brien")
        parsed = QgsExpression(expression)
        assert not parsed.hasParserError(), parsed.parserErrorString()

        class Probe:
            MAX_QUERY_RESULTS = 5000

        results, truncated = ConsultasPredialesDialog._fetch_features(
            Probe(), layer, expression
        )
        assert len(results) == 1
        assert not truncated
        assert results[0]['CODIGO'] == '001234'
        assert not results[0].hasGeometry()
        print('QGIS smoke test OK')
    finally:
        app.exitQgis()


if __name__ == '__main__':
    main()
