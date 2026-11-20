"""Reglas puras de normalización y clasificación de cartera.

Este módulo no importa QGIS. Mantener aquí las reglas de negocio permite
probarlas con Python estándar y evita que la interfaz decida cómo interpretar
los datos del reporte.
"""

from decimal import Decimal, InvalidOperation
import re
import unicodedata


STATUS_DEBT = 'deuda'
STATUS_CLEAR = 'paz'
STATUS_UNKNOWN = 'sin_info'
VALID_STATUSES = (STATUS_DEBT, STATUS_CLEAR, STATUS_UNKNOWN)

# Criterios para decidir qué predio está en deuda.
#   MODE_VALUE: clasifica cada obligación por su saldo o estado textual.
#   MODE_PRESENCE: el reporte ES la lista de deudores; aparecer implica deuda y
#     no cruzar implica estar al día (paz y salvo).
MODE_VALUE = 'valor'
MODE_PRESENCE = 'presencia'
CLASSIFICATION_MODES = (MODE_VALUE, MODE_PRESENCE)


def normalize_text(value):
    return '' if value is None else str(value).strip()


def normalize_words(value):
    """Normaliza texto libre sin perder el valor original mostrado al usuario."""
    text = normalize_text(value).casefold()
    return ''.join(
        character for character in unicodedata.normalize('NFKD', text)
        if not unicodedata.combining(character)
    )


def key_variants(value):
    """Devuelve variantes seguras para cruzar códigos texto/número."""
    text = normalize_words(value)
    if not text:
        return set()
    variants = {text}
    compact = ''.join(character for character in text if character.isalnum())
    if compact:
        variants.add(compact)
    if compact.isdigit():
        variants.add(compact.lstrip('0') or '0')
    # Excel/OGR suele exponer códigos enteros como 123.0 o 123,0.
    if re.fullmatch(r'[+]?[0-9]+[.,]0+', text):
        integer = re.split(r'[.,]', text, maxsplit=1)[0]
        variants.update((integer, integer.lstrip('0') or '0'))
    # También admite notación científica únicamente cuando representa un entero.
    if re.fullmatch(r'[+]?[0-9]+(?:[.,][0-9]+)?e[+]?\d+', text):
        try:
            number = Decimal(text.replace(',', '.'))
            if number == number.to_integral_value():
                integer = format(number, 'f').split('.')[0]
                variants.update((integer, integer.lstrip('0') or '0'))
        except InvalidOperation:
            pass
    return variants


def count_matches(values, index_keys):
    """Cuenta cuántos ``values`` cruzan con el conjunto ``index_keys``.

    Se usa para descubrir, de forma empírica, qué campo de una capa espacial
    contiene el código predial que coincide con el reporte de cartera, sin
    depender del nombre del campo.
    """
    if not index_keys:
        return 0
    matched = 0
    for value in values:
        variants = key_variants(value)
        if variants and not variants.isdisjoint(index_keys):
            matched += 1
    return matched


def parse_number(value):
    """Interpreta números simples y formatos monetarios comunes ES/EN."""
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = normalize_text(value).replace('$', '').replace('€', '').replace(' ', '')
    negative_parentheses = text.startswith('(') and text.endswith(')')
    if negative_parentheses:
        text = text[1:-1]
    cleaned = ''.join(character for character in text if character.isdigit() or character in '.,-')
    if not cleaned or cleaned in ('-', '.', ','):
        return None
    try:
        if ',' in cleaned and '.' in cleaned:
            decimal = ',' if cleaned.rfind(',') > cleaned.rfind('.') else '.'
            thousands = '.' if decimal == ',' else ','
            cleaned = cleaned.replace(thousands, '').replace(decimal, '.')
        elif cleaned.count(',') == 1:
            before, after = cleaned.split(',')
            cleaned = before + ('.' + after if len(after) <= 2 else after)
        elif cleaned.count(',') > 1:
            cleaned = cleaned.replace(',', '')
        elif cleaned.count('.') == 1:
            before, after = cleaned.split('.')
            cleaned = before + ('.' + after if len(after) <= 2 else after)
        elif cleaned.count('.') > 1:
            cleaned = cleaned.replace('.', '')
        number = float(cleaned)
        return -abs(number) if negative_parentheses else number
    except ValueError:
        return None


def classify_value(value, threshold=0.0):
    """Clasifica un saldo o estado textual en deuda, paz o sin información."""
    normalized = normalize_words(value)
    peace_terms = (
        'paz y salvo', 'sin deuda', 'no debe', 'al dia', 'pagado',
        'cancelado', 'solvente', 'saldado',
    )
    debt_terms = (
        'deuda', 'mora', 'moroso', 'pendiente', 'vencid', 'cobro',
        'insolvente', 'acuerdo de pago', 'saldo a cargo',
    )
    if any(term in normalized for term in peace_terms):
        return STATUS_CLEAR
    if any(term in normalized for term in debt_terms):
        return STATUS_DEBT
    number = parse_number(value)
    if number is not None:
        return STATUS_DEBT if number > threshold else STATUS_CLEAR
    return STATUS_UNKNOWN


def aggregate_status(statuses):
    """Una obligación en deuda domina el estado consolidado del predio."""
    statuses = tuple(statuses)
    if STATUS_DEBT in statuses:
        return STATUS_DEBT
    if STATUS_CLEAR in statuses:
        return STATUS_CLEAR
    return STATUS_UNKNOWN


def summarize_obligations(values, threshold=0.0, mode=MODE_VALUE, has_key=True):
    """Consolida las obligaciones asociadas a un predio.

    En ``MODE_VALUE`` ``total_debt`` suma solo valores numéricos que superan el
    límite y un estado textual de deuda se cuenta sin inventar importe.

    En ``MODE_PRESENCE`` el reporte es la lista de deudores: cualquier obligación
    cruzada implica deuda y se suman todos los saldos numéricos. Un predio sin
    obligaciones queda en paz y salvo (``STATUS_CLEAR``) cuando tiene un código
    legible (``has_key``) o sin información (``STATUS_UNKNOWN``) cuando no lo
    tiene y, por tanto, no se pudo verificar.
    """
    values = tuple(values)
    details = []
    seen = set()
    total_debt = 0.0
    debt_count = 0
    for value in values:
        text = normalize_text(value)
        number = parse_number(value)
        if mode == MODE_PRESENCE:
            is_debt = True
        else:
            is_debt = classify_value(value, threshold) == STATUS_DEBT
        if is_debt:
            debt_count += 1
            if number is not None and (mode == MODE_PRESENCE or number > threshold):
                total_debt += number
        if text and text not in seen:
            seen.add(text)
            details.append(text)
    if mode == MODE_PRESENCE:
        if values:
            status = STATUS_DEBT
        else:
            status = STATUS_CLEAR if has_key else STATUS_UNKNOWN
    else:
        status = aggregate_status(classify_value(value, threshold) for value in values)
    return {
        'status': status,
        'obligation_count': len(values),
        'debt_count': debt_count,
        'total_debt': total_debt,
        'source': ' | '.join(details),
    }
