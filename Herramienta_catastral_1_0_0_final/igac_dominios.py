"""
igac_dominios.py
Catálogos oficiales del modelo de datos IGAC – Catastro Multipropósito.
Fuente: Resolución 070 de 2011 IGAC y actualizaciones del catastro multipropósito.
Cada diccionario mapea código → descripción para usar en ComboBox.
"""

# ── Destino Económico ────────────────────────────────────────────────
DESTINO_ECONOMICO = {
    '':  '-- Todos --',
    'H': 'H – Habitacional',
    'D': 'D – Industrial',
    'L': 'L – Lote urbanizable no urbanizado / rural no edificado',
    'C': 'C – Comercial',
    'P': 'P – Uso público',
    'R': 'R – Recreación y deporte',
    'A': 'A – Agropecuario',
    'M': 'M – Minero',
    'B': 'B – Bodega',
    'E': 'E – Educativo',
    'S': 'S – Salubridad',
    'I': 'I – Institucional',
    'J': 'J – Industrial / comercial mixto',
    'Q': 'Q – Religioso',
    'T': 'T – Turístico',
    'O': 'O – Otro',
}

# ── Tipo de Documento ────────────────────────────────────────────────
# Fuente: DIAN, RNEC, Resolución IGAC y normativa colombiana vigente
TIPO_DOCUMENTO = {
    '':   '-- Todos --',
    'C':  'C – Cédula de ciudadanía',
    'E':  'E – Cédula de extranjería',
    'P':  'P – Pasaporte',
    'N':  'N – NIT (Número de Identificación Tributaria)',
    'T':  'T – Tarjeta de identidad',
    'R':  'R – Registro civil de nacimiento',
    'I':  'I – NUIP (Número Único de Identificación Personal)',
    'S':  'S – NIT extranjero',
    'D':  'D – Documento de identificación extranjero',
    'L':  'L – Libreta militar',
    'M':  'M – Menor sin identificación',
    'X':  'X – Fideicomiso / patrimonio autónomo',
    'U':  'U – Sucesión ilíquida',
    'G':  'G – Permiso especial de permanencia (PEP)',
    'V':  'V – Permiso de protección temporal (PPT)',
    'O':  'O – Otro documento',
}

# ── Estado Civil ─────────────────────────────────────────────────────
ESTADO_CIVIL = {
    '':  '-- Todos --',
    '1': '1 – Soltero(a)',
    '2': '2 – Casado(a)',
    '3': '3 – Unión marital de hecho',
    '4': '4 – Separado(a) / divorciado(a)',
    '5': '5 – Viudo(a)',
    '6': '6 – No aplica (persona jurídica)',
}

# ── Condición Predio ─────────────────────────────────────────────────
CONDICION_PREDIO = {
    '':   '-- Todos --',
    '0':  '0 – NPH (No Propiedad Horizontal)',
    '1':  '1 – PH – Matriz',
    '2':  '2 – PH – Unidad',
    '3':  '3 – Mejora en predio ajeno',
    '4':  '4 – Vía',
    '5':  '5 – Bien de uso público',
    '6':  '6 – Predio colectivo',
    '7':  '7 – Predio en investigación',
    '99': '99 – Sin información',
}

# ── Tipo Registro ────────────────────────────────────────────────────
TIPO_REGISTRO = {
    '':  '-- Todos --',
    '1': '1 – Registro 1 (propietarios)',
    '2': '2 – Registro 2 (construcciones)',
}

# ── Estrato socioeconómico ───────────────────────────────────────────
ESTRATO = {
    '':  '-- Todos --',
    '0': '0 – Sin estrato / rural',
    '1': '1 – Estrato 1',
    '2': '2 – Estrato 2',
    '3': '3 – Estrato 3',
    '4': '4 – Estrato 4',
    '5': '5 – Estrato 5',
    '6': '6 – Estrato 6',
}

# ── Uso construcción ─────────────────────────────────────────────────
USO_CONSTRUCCION = {
    '':   '-- Todos --',
    '1':  '1 – Casa',
    '2':  '2 – Apartamento',
    '3':  '3 – Casa-lote',
    '4':  '4 – Bodega',
    '5':  '5 – Local / comercio',
    '6':  '6 – Oficina',
    '7':  '7 – Consultorio',
    '8':  '8 – Hotel / hostal',
    '9':  '9 – Parqueadero',
    '10': '10 – Depósito',
    '11': '11 – Industria',
    '12': '12 – Educativo',
    '13': '13 – Salubridad',
    '14': '14 – Religioso',
    '15': '15 – Institucional',
    '16': '16 – Recreativo / deportivo',
    '17': '17 – Parque / zona verde',
    '18': '18 – Kiosco / caseta',
    '19': '19 – Galpón / establo / pesebre',
    '20': '20 – Silo / invernadero',
    '21': '21 – Mejora',
    '99': '99 – Otro',
}

# ── Tipo derecho ─────────────────────────────────────────────────────
TIPO_DERECHO = {
    '':   '-- Todos --',
    'PD': 'PD – Pleno dominio',
    'NU': 'NU – Nuda propiedad',
    'US': 'US – Usufructo',
    'DS': 'DS – Dominio superficie',
    'PO': 'PO – Posesión',
    'OC': 'OC – Ocupación',
    'TE': 'TE – Tenencia',
}

# ── Departamentos de Colombia ────────────────────────────────────────
DEPARTAMENTOS = {
    '':   '-- Todos --',
    '5':  '05 – Antioquia',
    '8':  '08 – Atlántico',
    '11': '11 – Bogotá D.C.',
    '13': '13 – Bolívar',
    '15': '15 – Boyacá',
    '17': '17 – Caldas',
    '18': '18 – Caquetá',
    '19': '19 – Cauca',
    '20': '20 – Cesar',
    '23': '23 – Córdoba',
    '25': '25 – Cundinamarca',
    '27': '27 – Chocó',
    '41': '41 – Huila',
    '44': '44 – La Guajira',
    '47': '47 – Magdalena',
    '50': '50 – Meta',
    '52': '52 – Nariño',
    '54': '54 – Norte de Santander',
    '63': '63 – Quindío',
    '66': '66 – Risaralda',
    '68': '68 – Santander',
    '70': '70 – Sucre',
    '73': '73 – Tolima',
    '76': '76 – Valle del Cauca',
    '81': '81 – Arauca',
    '85': '85 – Casanare',
    '86': '86 – Putumayo',
    '88': '88 – San Andrés y Providencia',
    '91': '91 – Amazonas',
    '94': '94 – Guainía',
    '95': '95 – Guaviare',
    '97': '97 – Vaupés',
    '99': '99 – Vichada',
}

# ── Reconocimiento de tipo de capa por nombre ────────────────────────
LAYER_TYPE_KEYWORDS = {
    'terreno': [
        'terreno', 'predio', 'lote', 'terrain',
        'r_terreno', 'u_terreno',
        'r_unidad', 'u_unidad',
        'unidad',
    ],
    'construccion': [
        'construccion', 'construcción', 'building', 'edificacion',
        'r_construccion', 'u_construccion',
        'r_construccion_informal', 'u_construccion_informal',
    ],
    'propietario':    ['propietario', 'titular', 'owner', 'interesado'],
    'lindero':        ['lindero', 'boundary', 'limite'],
    'punto_lindero':  ['punto_lindero', 'puntoLindero', 'vertex', 'punto_limite'],
    'punto_control':  ['punto_control', 'puntoControl', 'control_point'],
    'via':            ['via_', 'nomenclatura_vial', 'r_nomenclatura', 'u_nomenclatura'],
    'manzana':        ['manzana', 'u_manzana', 'block'],
    'vereda':         ['vereda', 'r_vereda', 'sector_rural'],
    'barrio':         ['barrio', 'u_barrio', 'sector_urbano', 'localidad'],
    'sector':         ['r_sector', 'u_sector', 'sector'],
    'zona_homogenea': [
        'zona_homogenea', 'r_zona_homogenea', 'u_zona_homogenea',
        'zhr_', 'zhu_', 'zona_homogenea_fisica', 'zona_homogenea_geoeconomica',
    ],
}

def detect_layer_type(layer_name: str) -> str:
    name_lower = layer_name.lower().replace(' ', '_').replace('-', '_')
    for ltype, keywords in LAYER_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in name_lower:
                return ltype
    return 'desconocido'
