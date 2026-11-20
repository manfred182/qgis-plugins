"""Lógica pura para unir capas de una Geodatabase con tablas externas (R1/R2).

Este módulo no importa QGIS. Mantener aquí las reglas permite probarlas con
Python estándar y separa la decisión de "qué cruzar y cómo juntar" de la
interfaz. La apertura real de GDB/Excel la hace la capa del diálogo con el
proveedor OGR de QGIS.
"""

from collections import Counter
from decimal import Decimal, InvalidOperation
import hashlib
import hmac
import re

from .cartera_core import (
    MODE_PRESENCE,
    STATUS_CLEAR,
    key_variants,
    normalize_text,
    normalize_words,
    parse_number,
    summarize_obligations,
)


# Proveniencia de las columnas: ayuda a prefijar campos y evitar colisiones
# cuando la capa de la GDB, R1 y R2 comparten nombres (p. ej. "FICHA").
SRC_GDB = 'gdb'
SRC_R1 = 'r1'
SRC_R2 = 'r2'
SOURCE_LABELS = {
    SRC_GDB: 'GDB',
    SRC_R1: 'R1',
    SRC_R2: 'R2',
    None: '?',
}

# El catastro colombiano utiliza el número predial anterior de 20 dígitos y
# el número predial nacional de 30 dígitos. Ambos son llaves legibles.
VALID_PREDIAL_LENGTHS = (20, 30)

# ---------------------------------------------------------------------------
# Candado por municipio (habilitación territorial)
#
# El aplicativo está habilitado únicamente para un municipio. Los cinco primeros
# dígitos del número predial son el departamento (2) + municipio (3); para
# Morelia, Caquetá corresponden a "18479". Para que ese código no quede como un
# literal fácil de reemplazar, no se guarda en claro: se conserva el hash SHA-256
# de la combinación (sal + código) y la verificación recalcula ese hash. Es un
# disuasivo (Python es código fuente y no puede cifrarse de forma irreversible),
# no un control criptográfico infalible.
_LICENSE_SALT = 'SMCP-v1::'
LICENSED_MUNICIPALITY_HASH = (
    '4fa1b95e604891e94ec47494fcaa8209221c723a36513154a24bc7c57c850f7c'
)
# Proporción mínima de predios que deben pertenecer al municipio habilitado.
LICENSE_MIN_RATIO = 0.6


def municipality_of_code(code, valid_lengths=VALID_PREDIAL_LENGTHS):
    """Departamento+municipio (5 dígitos) de un número predial legible."""
    digits = ''.join(character for character in normalize_text(code)
                     if character.isdigit())
    if len(digits) in valid_lengths:
        return digits[:5]
    return ''


def municipality_matches_license(municipality_code):
    """Verifica un código de municipio de 5 dígitos contra la habilitación."""
    code = normalize_text(municipality_code)
    if not code:
        return False
    digest = hashlib.sha256((_LICENSE_SALT + code).encode('utf-8')).hexdigest()
    return hmac.compare_digest(digest, LICENSED_MUNICIPALITY_HASH)


def dominant_municipality(rows, code_columns):
    """Municipio predominante entre los predios con código legible.

    Devuelve ``(codigo5, coincidencias, total_legible)``. Se usa para decidir si
    la Geodatabase cargada pertenece al municipio habilitado.
    """
    counter = Counter()
    for row in rows:
        for column in code_columns:
            if 0 <= column < len(row):
                municipality = municipality_of_code(row[column])
                if municipality:
                    counter[municipality] += 1
                    break
    if not counter:
        return '', 0, 0
    total = sum(counter.values())
    code, count = counter.most_common(1)[0]
    return code, count, total


def check_municipality_license(rows, code_columns, min_ratio=LICENSE_MIN_RATIO):
    """Evalúa la habilitación territorial de un conjunto de predios.

    Devuelve ``(autorizado, codigo_detectado, proporcion)``. Autoriza cuando el
    municipio predominante es el habilitado y concentra al menos ``min_ratio`` de
    los predios legibles, de modo que unos pocos códigos vecinos no habiliten por
    error una Geodatabase de otro municipio.
    """
    code, count, total = dominant_municipality(rows, code_columns)
    ratio = (count / total) if total else 0.0
    authorized = bool(code) and municipality_matches_license(code) and \
        ratio >= min_ratio
    return authorized, code, ratio


def type_rank(type_name):
    """Ordena los tipos de campo para elegir uno dominante al unir esquemas.

    Tipos más capaces (doble/entero/texto) dominan sobre otros más restrictivos
    (booleano/fecha). Se devuelve un número; mayor = más capacidad.
    """
    if not type_name:
        return 0
    name = type_name.lower()
    if 'double' in name or 'float' in name or 'real' in name:
        return 40
    if 'int' in name and 'unsigned' not in name:
        return 30
    if 'unsigned' in name:
        return 29
    if 'string' in name or 'text' in name or 'char' in name or 'varchar' in name:
        return 20
    if 'date' in name or 'datetime' in name or 'time' in name:
        return 15
    if 'bool' in name:
        return 10
    return 5


def merge_field_definitions(column_sets):
    """Une varios esquemas (listas de {name, type, source}) en un solo orden.

    ``column_sets`` es una lista de esquemas; cada uno es una secuencia de
    tuplas ``(name, type_name, source)``. Se devuelve una lista ordenada de
    ``(name, type_name)`` donde el nombre gana el tipo dominante y las
    colisiones se desambiguan quedándose la de mayor capacidad. Se conserva la
    primera aparición de cada campo para un orden estable.
    """
    order = []
    best_type = {}
    for column_set in column_sets:
        for name, type_name, _source in column_set:
            key = name.casefold()
            if key not in best_type:
                order.append(name)
                best_type[key] = (name, type_name)
            else:
                stored_name, stored_type = best_type[key]
                if type_rank(type_name) > type_rank(stored_type):
                    best_type[key] = (stored_name, type_name)
    return [best_type[name.casefold()] for name in order]


def ensure_unique_prefixes(rows_with_sources):
    """Dada una fila que mezcla columnas de varias procedencias, desambigua
    nombres iguales prefijándolos con R1_/R2_/GDB_.

    ``rows_with_sources`` es una lista de (source, {campo: valor_acumulado}).
    Se devuelve la fila combinada (dict nombre -> valor).
    """
    # Registrar cuántas veces aparece cada campo (mayúsculas/espacios ignorados).
    normalized_counts = {}
    normalized_owner = {}
    for source, mapping in rows_with_sources:
        for name in mapping:
            key = name.casefold().replace(' ', '_')
            if key not in normalized_counts:
                normalized_counts[key] = 0
                normalized_owner[key] = (source, name)
            normalized_counts[key] += 1
    # Solo se prefija lo que se repite; el resto conserva su nombre original.
    combined = {}
    for source, mapping in rows_with_sources:
        label = SOURCE_LABELS.get(source, '')
        for name, value in mapping.items():
            key = name.casefold().replace(' ', '_')
            if normalized_counts[key] > 1:
                combined[f'{label}_{name}'] = value
            else:
                combined[name] = value
    return combined


def build_key_index(rows, key_fields):
    """Índice código -> conjunto de índices de fila.

    ``rows`` es una lista de listas/tuplas de valores (una fila por registro).
    ``key_fields`` son los índices de columna que forman la llave. Devuelve un
    dict con las variantes normalizadas como llave y los índices de fila como
    valor.
    """
    index = {}
    for row_index, row in enumerate(rows):
        variants = set()
        for field in key_fields:
            if field is None or field >= len(row):
                continue
            variants |= key_variants(normalize_text(row[field]))
        for variant in variants:
            index.setdefault(variant, set()).add(row_index)
    return index


def match_indexes(rows, key_fields, index):
    """Lista (por fila) de los índices de fila con los que cruza en ``index``.

    Devuelve una lista paralela a ``rows``; cada elemento es un conjunto de
    índices de fila de la tabla que construyó ``index``.
    """
    matched = []
    for row in rows:
        variants = set()
        for field in key_fields:
            if field is None or field >= len(row):
                continue
            variants |= key_variants(normalize_text(row[field]))
        cids = set()
        for variant in variants:
            cids |= index.get(variant, set())
        matched.append(cids)
    return matched


# Pistas para reconocer un campo que es un segmento del código predial nacional
# (30 dígitos) cuando aparece partido en varias columnas.
CODE_SEGMENT_HINTS = (
    'municipio', 'municip', 'vereda', 'sector', 'zona', 'manzana',
    'lote', 'predio', 'parcela', 'numero_predial', 'numero predial',
    'codigo', 'cod_predial', 'ficha', 'departamento', 'certificado', 'segmento',
)


def is_code_segment_name(name):
    """True si el nombre del campo sugiere que forma parte del código predial."""
    normalized = normalize_words(name)
    if not normalized:
        return False
    return any(hint in normalized for hint in CODE_SEGMENT_HINTS)


def concat_key_variants(values):
    """Código formado por la concatenación (sin separadores) de varios campos.

    El número predial nacional tiene 30 dígitos repartidos en segmentos. Al
    unirlos hay que conservar los ceros a la izquierda de cada segmento, así
    que se concatenan como TEXTO (sin parsear números). Se devuelven las
    variantes normalizadas igual que para un código en un solo campo.
    """
    # Se descartan vacíos y espacios; se conserva el orden de los segmentos.
    parts = [normalize_text(value) for value in values]
    parts = [part.replace(' ', '') for part in parts if part]
    if not parts:
        return set()
    return key_variants(''.join(parts))


def build_combined_index(rows, key_columns):
    """Índice código -> índices de fila, concatenando varios campos como clave.

    ``rows`` es una lista de filas (listas/tuplas). ``key_columns`` son los
    índices de las columnas que se concatenan (en ese orden) para formar la
    clave. Se usa cuando el código predial está partido en varios campos.
    """
    index = {}
    for row_index, row in enumerate(rows):
        values = [row[c] for c in key_columns if c is not None and c < len(row)]
        variants = concat_key_variants(values)
        for variant in variants:
            index.setdefault(variant, set()).add(row_index)
    return index


def combined_matches(rows, key_columns, index):
    """Índices de fila cruzados por fila, concatenando ``key_columns``."""
    matched = []
    for row in rows:
        values = [row[c] for c in key_columns if c is not None and c < len(row)]
        variants = concat_key_variants(values)
        cids = set()
        for variant in variants:
            cids |= index.get(variant, set())
        matched.append(cids)
    return matched


def _row_key_variants(row, columns):
    """Variantes de la llave de una fila para uno o varios campos."""
    valid = [column for column in columns if column is not None and column < len(row)]
    if not valid:
        return set()
    if len(valid) == 1:
        return key_variants(normalize_text(row[valid[0]]))
    return concat_key_variants([row[column] for column in valid])


def row_has_key(row, columns):
    """Indica si una fila tiene una llave legible en las columnas dadas."""
    return bool(_row_key_variants(row, columns))


def inspect_predial_key(row, columns, valid_lengths=VALID_PREDIAL_LENGTHS):
    """Valida la llave predial y explica por qué una fila no es utilizable.

    Un código vacío se identifica por separado para poder omitirlo sin
    incluirlo en el reporte de inconsistencias. Los códigos no vacíos deben
    contener solamente dígitos y medir 20 o 30 posiciones. Se toleran espacios
    y separadores visuales, así como los enteros que Excel expone con ``.0`` o
    en notación científica.
    """
    valid_columns = [
        column for column in columns
        if column is not None and 0 <= column < len(row)
    ]
    raw_parts = [normalize_text(row[column]) for column in valid_columns]
    nonempty_parts = [part for part in raw_parts if part]
    raw = ' + '.join(nonempty_parts)
    if not nonempty_parts:
        return {
            'state': 'empty', 'raw': '', 'normalized': '',
            'reason': 'Código vacío',
        }

    normalized_parts = []
    for part in nonempty_parts:
        text = part.strip()
        if re.fullmatch(r'[+]?[0-9]+[.,]0+', text):
            text = re.split(r'[.,]', text, maxsplit=1)[0]
        elif re.fullmatch(r'[+]?[0-9]+(?:[.,][0-9]+)?e[+]?[0-9]+', text, re.I):
            try:
                number = Decimal(text.replace(',', '.'))
                if number == number.to_integral_value():
                    text = format(number, 'f').split('.')[0]
            except InvalidOperation:
                pass
        text = re.sub(r'[\s.\-_/]+', '', text)
        if text.startswith('+'):
            text = text[1:]
        normalized_parts.append(text)
    normalized = ''.join(normalized_parts)

    if not normalized or not normalized.isdigit():
        return {
            'state': 'invalid', 'raw': raw, 'normalized': normalized,
            'reason': 'Contiene caracteres distintos de dígitos',
        }
    if valid_lengths and len(normalized) not in valid_lengths:
        expected = ' o '.join(str(length) for length in valid_lengths)
        return {
            'state': 'invalid', 'raw': raw, 'normalized': normalized,
            'reason': (
                f'Longitud de {len(normalized)} dígitos; se esperaban '
                f'{expected}'
            ),
        }
    return {
        'state': 'valid', 'raw': raw, 'normalized': normalized, 'reason': '',
    }


def partition_predial_rows(rows, columns, valid_lengths=VALID_PREDIAL_LENGTHS):
    """Separa índices de filas válidas, vacías e ilegibles."""
    valid = []
    empty = []
    invalid = []
    for row_index, row in enumerate(rows):
        inspection = inspect_predial_key(row, columns, valid_lengths)
        if inspection['state'] == 'valid':
            valid.append(row_index)
        elif inspection['state'] == 'empty':
            empty.append(row_index)
        else:
            issue = dict(inspection)
            issue['row_index'] = row_index
            invalid.append(issue)
    return valid, empty, invalid


def _is_blank_key(value):
    """Los códigos catastrales exportados a veces llegan como el texto ``NULL``.

    Ese valor equivale a "sin dato" para agrupar (vereda, manzana, estrato…); si
    no se filtra, una vereda inexistente se convertiría en la categoría más
    grande del análisis.
    """
    text = normalize_text(value)
    return not text or text.upper() == 'NULL'


def build_export_analytics(field_names, rows, top_limit=25):
    """Resume el resultado para el tablero y las tablas tipo dinámica.

    ``CART_SALDO`` se interpreta como cartera pendiente por recaudar. El
    insumo no contiene pagos recibidos, por lo que no se presenta como recaudo
    ejecutado.

    Los predios a paz y salvo se resumen con el mismo nivel de detalle que los
    deudores: se cuentan por vereda (con su nombre), manzana, estrato, destino
    económico, vigencia y localización, y se listan en ``clear_predios`` igual
    que los deudores en ``top_debtors``.
    """
    positions = {name.casefold(): index for index, name in enumerate(field_names)}

    def field_index(*names):
        for name in names:
            index = positions.get(name.casefold())
            if index is not None:
                return index
        return -1

    def value(row, index, default=''):
        if index < 0 or index >= len(row):
            return default
        item = row[index]
        return default if item is None else item

    def first_present(row, indexes):
        for index in indexes:
            item = value(row, index)
            if not _is_blank_key(item):
                return normalize_text(item)
        return ''

    status_index = field_index('CART_ESTADO')
    balance_index = field_index('CART_SALDO')
    class_index = field_index('PRED_CLASE')
    area_index = field_index('PRED_AMBITO')
    formality_index = field_index('PRED_FORMALIDAD')
    vereda_index = field_index(
        'GDB_VEREDA_CODIGO', 'GDB_CODIGO_VEREDA', 'GDB_VEREDA',
        'R1_Comuna',
    )
    vereda_name_index = field_index('GDB_VEREDA_NOMBRE', 'GDB_NOMBRE_VEREDA')
    manzana_index = field_index(
        'GDB_MANZANA_CODIGO', 'GDB_CODIGO_MANZANA', 'GDB_MANZANA',
    )
    estrato_indexes = [
        index for index in (
            field_index('R2_Estrato'), field_index('R2_Estrato_1'),
            field_index('R2_Estrato_2'), field_index('CARTERA_ESTRATO'),
        ) if index >= 0
    ]
    destino_index = field_index(
        'R1_DestinoEconomico', 'R1_Destino_Economico', 'R1_Destino',
    )
    period_index = field_index('CART_PERIODO')
    located_index = field_index('PRED_LOCALIZADO')
    code_index = field_index('GDB_CODIGO', 'CARTERA_Numero_Predial')
    # El propietario y el avalúo se toman del primer origen con dato real: la
    # cartera para los deudores y R1 para los predios a paz y salvo (que no
    # figuran en la cartera y por eso traen esas columnas vacías).
    owner_indexes = [
        index for index in (
            field_index('CARTERA_PROPIETARIO'), field_index('R1_Nombre'),
            field_index('CART_DETALLE'),
        ) if index >= 0
    ]
    avaluo_indexes = [
        index for index in (
            field_index('CARTERA_AVALUO'), field_index('R1_Avaluo_($)'),
            field_index('R1_Avaluo'),
        ) if index >= 0
    ]

    result = {
        'total': 0,
        'debt_count': 0,
        'clear_count': 0,
        'unknown_count': 0,
        'debt_total': 0.0,
        'located_debt': 0,
        'unlocated_debt': 0,
        'located_clear': 0,
        'unlocated_clear': 0,
        'by_status': {},
        'by_class': {},
        'by_vereda': {},
        'by_manzana': {},
        'by_estrato': {},
        'by_destino': {},
        'by_territory': {},
        'by_period': {},
        'top_debtors': [],
        'clear_predios': [],
    }

    def bump(mapping, key, status, balance, located, extra=None):
        """Acumula un predio en una categoría (vereda, manzana, estrato…)."""
        group = mapping.get(key)
        if group is None:
            group = {
                'total': 0, 'debt': 0, 'clear': 0, 'unknown': 0,
                'balance': 0.0, 'located': 0, 'unlocated': 0,
            }
            if extra:
                group.update(extra)
            mapping[key] = group
        group['total'] += 1
        if status == 'EN DEUDA':
            group['debt'] += 1
            group['balance'] += balance
        elif status == 'PAZ Y SALVO':
            group['clear'] += 1
        else:
            group['unknown'] += 1
        group['located' if located else 'unlocated'] += 1
        return group

    def period_group(period):
        return result['by_period'].setdefault(period, {
            'debt': 0, 'clear': 0, 'total': 0, 'balance': 0.0, 'count': 0,
        })

    debtors = []
    clear_predios = []
    for row in rows:
        result['total'] += 1
        status = normalize_text(value(row, status_index)) or 'SIN ESTADO'
        balance = parse_number(value(row, balance_index)) or 0.0
        class_name = normalize_text(value(row, class_index)) or 'NO DETERMINADO'
        area = normalize_text(value(row, area_index)) or 'NO DETERMINADO'
        formality = normalize_text(value(row, formality_index)) or 'NO DETERMINADA'
        vereda_code = '' if _is_blank_key(value(row, vereda_index)) else \
            normalize_text(value(row, vereda_index))
        vereda_name = '' if vereda_name_index < 0 or _is_blank_key(
            value(row, vereda_name_index)
        ) else normalize_text(value(row, vereda_name_index))
        vereda_label = vereda_name or vereda_code
        manzana_code = '' if _is_blank_key(value(row, manzana_index)) else \
            normalize_text(value(row, manzana_index))
        # El estrato de R2 puede venir consolidado ("3 | 0"); se toma el primero.
        estrato = first_present(row, estrato_indexes).split('|')[0].strip() \
            or 'SIN ESTRATO'
        destino_raw = first_present(row, [destino_index] if destino_index >= 0 else [])
        destino = destino_raw or 'SIN DESTINO'
        period = normalize_text(value(row, period_index)) or 'SIN VIGENCIA'
        located = normalize_text(value(row, located_index)).upper() == 'SI'
        code = normalize_text(value(row, code_index))
        owner = first_present(row, owner_indexes)
        # El avalúo también puede venir consolidado ("120000 | 98000"); se toma
        # el primero para no concatenar cifras en un número irreal.
        avaluo = parse_number(
            first_present(row, avaluo_indexes).split('|')[0]
        ) or 0.0

        status_group = result['by_status'].setdefault(
            status, {'count': 0, 'balance': 0.0},
        )
        status_group['count'] += 1
        status_group['balance'] += balance

        class_group = result['by_class'].setdefault(class_name, {
            'total': 0, 'debt': 0, 'clear': 0, 'balance': 0.0,
        })
        class_group['total'] += 1

        # Clave territorial unificada: vereda para lo rural, manzana para lo
        # urbano y la clase predial para lo que no tiene ninguna de las dos.
        if vereda_code:
            territory = vereda_label
        elif manzana_code:
            territory = f'MZ {manzana_code}'
        else:
            territory = class_name
        bump(result['by_territory'], territory, status, balance, located)

        if vereda_code:
            bump(result['by_vereda'], vereda_code, status, balance, located, {
                'name': vereda_name, 'code': vereda_code,
                'area': area, 'formality': formality,
            })
        if manzana_code:
            bump(result['by_manzana'], manzana_code, status, balance, located, {
                'code': manzana_code, 'area': area,
            })
        bump(result['by_estrato'], estrato, status, balance, located)
        bump(result['by_destino'], destino, status, balance, located)

        if status == 'EN DEUDA':
            result['debt_count'] += 1
            result['debt_total'] += balance
            result['located_debt' if located else 'unlocated_debt'] += 1
            class_group['debt'] += 1
            class_group['balance'] += balance
            group = period_group(period)
            group['debt'] += 1
            group['count'] += 1
            group['total'] += 1
            group['balance'] += balance
            debtors.append({
                'code': code, 'owner': owner, 'class': class_name,
                'vereda': vereda_label, 'manzana': manzana_code,
                'period': period, 'located': 'SI' if located else 'NO',
                'balance': balance,
            })
        elif status == 'PAZ Y SALVO':
            result['clear_count'] += 1
            result['located_clear' if located else 'unlocated_clear'] += 1
            class_group['clear'] += 1
            group = period_group(period)
            group['clear'] += 1
            group['total'] += 1
            clear_predios.append({
                'code': code, 'owner': owner, 'class': class_name,
                'vereda': vereda_label, 'manzana': manzana_code,
                'period': period, 'located': 'SI' if located else 'NO',
                'avaluo': avaluo,
            })
        else:
            result['unknown_count'] += 1

    result['debt_average'] = (
        result['debt_total'] / result['debt_count']
        if result['debt_count'] else 0.0
    )
    result['top_debtors'] = sorted(
        debtors, key=lambda item: item['balance'], reverse=True,
    )[:max(0, top_limit)]
    result['clear_predios'] = sorted(
        clear_predios, key=lambda item: item['avaluo'], reverse=True,
    )
    return result


def build_index_for_columns(rows, columns):
    """Índice reutilizable para una llave simple o concatenada."""
    index = {}
    for row_index, row in enumerate(rows):
        for variant in _row_key_variants(row, columns):
            index.setdefault(variant, set()).add(row_index)
    return index


def match_rows_to_index(rows, columns, index, heartbeat=None):
    """Cruza filas contra ``index`` usando una llave simple o concatenada."""
    matches = []
    for row_number, row in enumerate(rows, 1):
        row_matches = set()
        for variant in _row_key_variants(row, columns):
            row_matches.update(index.get(variant, ()))
        matches.append(row_matches)
        if heartbeat is not None and row_number % 500 == 0:
            heartbeat()
    return matches


def _field_key_score(name):
    """Prioridad de un campo como posible llave catastral.

    Los prefijos de procedencia (por ejemplo ``R1_`` o ``Terreno_``) no
    afectan porque se buscan las expresiones dentro del nombre normalizado.
    """
    normalized = normalize_words(name)
    compact = ''.join(character for character in normalized if character.isalnum())
    if not compact:
        return 0
    if 'codigopredial' in compact or 'numeropredial' in compact:
        return 100
    if 'nupre' in compact or 'codpredial' in compact:
        return 95
    if 'nopredial' in compact:
        return 90
    if compact.endswith('codigo'):
        return 80
    if 'ficha' in compact:
        return 70
    if is_code_segment_name(name):
        return 40
    return 0


def _candidate_key_specs(field_names, preferred_columns=None):
    """Llaves candidatas como tuplas de índices de columna.

    Cada campo con aspecto de código se prueba por separado. Una selección
    manual de varios campos también se prueba concatenada, conservando soporte
    para números prediales divididos en segmentos sin impedir que un archivo
    intermedio tenga a la vez ``CODIGO`` y ``CODIGO_PREDIAL``.
    """
    preferred = tuple(
        column for column in (preferred_columns or ())
        if column is not None and 0 <= column < len(field_names)
    )
    specs = []
    if len(preferred) > 1:
        specs.append(preferred)
    specs.extend((column,) for column in preferred)

    ranked = sorted(
        (
            (_field_key_score(name), index)
            for index, name in enumerate(field_names)
            if _field_key_score(name) >= 70
        ),
        reverse=True,
    )
    specs.extend((index,) for _score, index in ranked)

    # Si solo hay segmentos débiles, su combinación en orden de columnas puede
    # formar el número predial nacional completo.
    segment_columns = tuple(
        index for index, name in enumerate(field_names)
        if is_code_segment_name(name) and _field_key_score(name) < 70
    )
    if len(segment_columns) > 1:
        specs.append(segment_columns)

    unique = []
    seen = set()
    for spec in specs:
        if spec and spec not in seen:
            unique.append(spec)
            seen.add(spec)
    return unique


def find_best_join_keys(
    left_field_names,
    left_rows,
    right_field_names,
    right_rows,
    left_preferred=None,
    right_preferred=None,
    heartbeat=None,
):
    """Descubre automáticamente la mejor pareja de llaves entre dos fuentes.

    La decisión se basa primero en cuántas filas cruzan realmente y después en
    la calidad semántica de los nombres. Esto permite tanto un cruce directo
    por código predial como uno encadenado ``CODIGO -> CODIGO_PREDIAL``.
    Devuelve un diccionario con columnas y coincidencias, o ``None``.
    """
    if not left_rows or not right_rows:
        return None
    left_specs = _candidate_key_specs(left_field_names, left_preferred)
    right_specs = _candidate_key_specs(right_field_names, right_preferred)
    best = None

    # Ruta rápida para plantillas conocidas: prueba primero cada llave elegida
    # automáticamente/manualmente sin combinarla con las demás. Si cubre una
    # parte sustancial de la capa, no hace falta explorar todas las parejas.
    preferred_left_specs = [(column,) for column in (left_preferred or ())]
    preferred_right_specs = [(column,) for column in (right_preferred or ())]
    for right_columns in preferred_right_specs:
        index = build_index_for_columns(right_rows, right_columns)
        if not index:
            continue
        for left_columns in preferred_left_specs:
            matches = match_rows_to_index(
                left_rows, left_columns, index, heartbeat=heartbeat,
            )
            matched_left = sum(bool(item) for item in matches)
            if matched_left > (best['matched_left'] if best else 0):
                matched_right_ids = set().union(*(item for item in matches if item))
                best = {
                    'left_columns': left_columns,
                    'right_columns': right_columns,
                    'matches': matches,
                    'matched_left': matched_left,
                    'matched_right': len(matched_right_ids),
                    'rank': (matched_left, len(matched_right_ids), 0, -2),
                }
    fast_threshold = min(25, max(1, int(len(left_rows) * 0.25)))
    if best is not None and best['matched_left'] >= fast_threshold:
        return best

    for right_columns in right_specs:
        index = build_index_for_columns(right_rows, right_columns)
        if not index:
            continue
        for left_columns in left_specs:
            matches = match_rows_to_index(
                left_rows, left_columns, index, heartbeat=heartbeat,
            )
            matched_left = sum(bool(item) for item in matches)
            if not matched_left:
                continue
            matched_right_ids = set().union(*(item for item in matches if item))
            name_score = sum(
                _field_key_score(left_field_names[column]) for column in left_columns
            ) + sum(
                _field_key_score(right_field_names[column]) for column in right_columns
            )
            # El número de filas que cruza es la evidencia principal. Ante
            # empates se prefiere una llave de nombre más específico y simple.
            rank = (matched_left, len(matched_right_ids), name_score,
                    -len(left_columns) - len(right_columns))
            if best is None or rank > best['rank']:
                best = {
                    'left_columns': left_columns,
                    'right_columns': right_columns,
                    'matches': matches,
                    'matched_left': matched_left,
                    'matched_right': len(matched_right_ids),
                    'rank': rank,
                }
            if heartbeat is not None:
                heartbeat()
    return best


def collapse_join_values(rows, row_indexes, column):
    """Consolida valores de varias coincidencias sin perder información."""
    values = []
    seen = set()
    for row_index in row_indexes:
        if row_index >= len(rows) or column >= len(rows[row_index]):
            continue
        value = rows[row_index][column]
        text = normalize_text(value)
        if not text or text in seen:
            continue
        values.append(value)
        seen.add(text)
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    return ' | '.join(normalize_text(value) for value in values)


def left_join_rows_automatic(
    left_field_names,
    left_rows,
    right_field_names,
    right_rows,
    left_preferred=None,
    right_preferred=None,
    heartbeat=None,
):
    """Left join automático y estable; conserva exactamente las filas izquierdas.

    Cuando la tabla derecha tiene varias filas para un código, sus valores se
    consolidan con `` | `` para que la capa final siga teniendo una sola
    geometría por predio sin descartar silenciosamente obligaciones o titulares.
    """
    result = find_best_join_keys(
        left_field_names, left_rows, right_field_names, right_rows,
        left_preferred, right_preferred, heartbeat,
    )
    width = len(right_field_names)
    if result is None:
        return [list(row) + [None] * width for row in left_rows], None

    joined = []
    for row_number, (left_row, row_indexes) in enumerate(
        zip(left_rows, result['matches']), 1
    ):
        ordered_indexes = sorted(row_indexes)
        additions = [
            collapse_join_values(right_rows, ordered_indexes, column)
            for column in range(width)
        ]
        joined.append(list(left_row) + additions)
        if heartbeat is not None and row_number % 250 == 0:
            heartbeat()
    return joined, result


def stack_attribute_sources(sources, source_field='GDB_CAPA_ORIGEN'):
    """Apila fuentes equivalentes conservando la unión de sus columnas.

    ``sources`` contiene tuplas ``(nombre, campos, filas)``. A diferencia de un
    join, cada fila de cada fuente se agrega verticalmente. Es la operación
    correcta para consolidar R_TERRENO, U_TERRENO y los terrenos informales en
    una sola capa espacial.
    """
    output_fields = [source_field]
    canonical_positions = {source_field.casefold(): 0}
    source_maps = []
    for source_name, field_names, rows in sources:
        positions = []
        for field_name in field_names:
            canonical = field_name.casefold()
            if canonical not in canonical_positions:
                canonical_positions[canonical] = len(output_fields)
                output_fields.append(field_name)
            positions.append(canonical_positions[canonical])
        source_maps.append((source_name, positions, rows))

    output_rows = []
    for source_name, positions, rows in source_maps:
        for row in rows:
            output = [None] * len(output_fields)
            output[0] = source_name
            for source_column, output_column in enumerate(positions):
                if source_column < len(row):
                    output[output_column] = row[source_column]
            output_rows.append(output)
    return output_fields, output_rows


def classify_terrain_source(source_name):
    """Describe una capa de terreno como ámbito y formalidad.

    Las GDB catastrales suelen usar ``R_TERRENO`` / ``U_TERRENO`` y sus
    variantes ``*_INFORMAL``. Mantener esta clasificación como atributos
    permite comprobar que el semáforo cubre las cuatro poblaciones sin cambiar
    la simbología principal (rojo/verde).
    """
    normalized = normalize_words(source_name).replace(' ', '_')
    if normalized.startswith('r_') or 'rural' in normalized:
        area = 'RURAL'
    elif normalized.startswith('u_') or 'urbano' in normalized:
        area = 'URBANO'
    else:
        area = 'NO DETERMINADO'
    formality = 'INFORMAL' if 'informal' in normalized else 'FORMAL'
    if area == 'NO DETERMINADO':
        class_name = area
    else:
        class_name = f'{area} {formality}'
    return area, formality, class_name


def unmatched_right_groups(match, right_rows):
    """Agrupa las filas derechas válidas que no cruzaron con la capa espacial.

    Cada grupo representa una llave predial única. Así es posible conservar en
    la capa final los registros de cartera no localizados sin crear una entidad
    adicional por cada obligación repetida.
    """
    if not match or not right_rows:
        return []
    right_columns = match.get('right_columns') or ()
    if not right_columns:
        return []
    matched_indexes = set()
    for indexes in match.get('matches', ()):
        matched_indexes.update(indexes)
    index = build_index_for_columns(right_rows, right_columns)
    groups = []
    seen = set()
    for row_index, row in enumerate(right_rows):
        if row_index in matched_indexes:
            continue
        related = set()
        for variant in _row_key_variants(row, right_columns):
            related.update(index.get(variant, ()))
        related.difference_update(matched_indexes)
        group = frozenset(related)
        if not group or group in seen:
            continue
        seen.add(group)
        groups.append(set(group))
    groups.sort(key=lambda item: min(item))
    return groups


def _year(value):
    try:
        return int(float(normalize_text(value).replace(',', '.')))
    except (TypeError, ValueError):
        return None


def _period_text(desde, hasta):
    if desde is None and hasta is None:
        return ''
    if desde is not None and hasta is not None:
        return str(desde) if desde == hasta else f'{desde}-{hasta}'
    return str(desde if desde is not None else hasta)


def summarize_presence_matches(
    left_rows,
    match,
    report_rows,
    value_column=None,
    owner_column=None,
    desde_column=None,
    hasta_column=None,
    current_year=None,
):
    """Resume cartera por predio a partir del resultado de un join automático.

    ``current_year`` (opcional) es el año en que se elabora el reporte del
    ejercicio. Los predios a paz y salvo no figuran en la cartera y por eso no
    traen vigencia; cuando se recibe ``current_year`` se les asigna esa vigencia
    actual para que aparezcan, con sus datos, junto a los deudores en los
    análisis por vigencia.
    """
    matches = match['matches'] if match else [set() for _ in left_rows]
    left_columns = match['left_columns'] if match else ()
    summaries = []
    for left_row, row_matches in zip(left_rows, matches):
        ordered = sorted(row_matches)
        values = [
            report_rows[index][value_column] if value_column is not None else 1
            for index in ordered
        ]
        summary = summarize_obligations(
            values,
            mode=MODE_PRESENCE,
            has_key=bool(match) and row_has_key(left_row, left_columns),
        )
        years_from = [
            _year(report_rows[index][desde_column]) for index in ordered
        ] if desde_column is not None else []
        years_to = [
            _year(report_rows[index][hasta_column]) for index in ordered
        ] if hasta_column is not None else []
        years_from = [value for value in years_from if value is not None]
        years_to = [value for value in years_to if value is not None]
        desde = min(years_from) if years_from else None
        hasta = max(years_to) if years_to else None
        # Vigencia actual para los predios a paz y salvo: sin obligaciones en la
        # cartera no hay años que resumir, así que se toma el año del ejercicio.
        if (
            current_year is not None
            and summary['status'] == STATUS_CLEAR
            and desde is None
            and hasta is None
        ):
            desde = hasta = current_year
        owners = []
        if owner_column is not None:
            for index in ordered:
                owner = normalize_text(report_rows[index][owner_column])
                if owner and owner not in owners:
                    owners.append(owner)
        period = _period_text(desde, hasta)
        detail = ' | '.join(owners)
        if period:
            detail = f'{detail} · vig. {period}' if detail else f'vig. {period}'
        summaries.append({
            **summary,
            'obligation_count': len(ordered),
            'vig_desde': desde,
            'vig_hasta': hasta,
            'period': period,
            'detail': detail,
        })
    return summaries
