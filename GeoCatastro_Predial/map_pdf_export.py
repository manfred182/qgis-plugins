"""Exportacion cartografica predial a PDF con el motor de diseno de QGIS.

La plantilla se construye en memoria para no agregar disenos temporales al
proyecto. Cada predio ocupa una hoja carta vertical (215,9 x 279,4 mm).
"""

import os
import re
import unicodedata
import math


LETTER_WIDTH_MM = 215.9
LETTER_HEIGHT_MM = 279.4


def safe_pdf_filename(code):
    """Devuelve un nombre de archivo portable a partir del codigo predial."""
    text = unicodedata.normalize('NFKD', str(code or 'predio'))
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^A-Za-z0-9._-]+', '_', text).strip('._-')
    return 'Ficha_Predial_{}.pdf'.format(text or 'predio')


def selection_pdf_filename(count):
    """Nombre sugerido para una salida de varios predios."""
    return 'Fichas_Prediales_{}_seleccionados.pdf'.format(max(1, int(count)))


def expanded_bounds(xmin, ymin, xmax, ymax, fallback_span=10.0, padding=0.25):
    """Amplia una extension y garantiza area visible para puntos o lineas."""
    width = max(0.0, float(xmax) - float(xmin))
    height = max(0.0, float(ymax) - float(ymin))
    span = max(width, height, float(fallback_span))
    margin = span * float(padding)
    if width == 0:
        xmin -= span * 0.5
        xmax += span * 0.5
    if height == 0:
        ymin -= span * 0.5
        ymax += span * 0.5
    return xmin - margin, ymin - margin, xmax + margin, ymax + margin


def _short_text(value, limit=58):
    text = ' '.join(str(value or '').split())
    if not text:
        return 'Sin informacion'
    if len(text) <= limit:
        return text
    return text[:max(1, limit - 3)].rstrip() + '...'


def _full_text(value):
    """Igual que ``_short_text`` pero sin recortar: nombres completos de
    capas/categorias y valores de la consulta, ninguno truncado con '...'
    (pedido del usuario, 2026-11-06)."""
    return ' '.join(str(value or '').split()) or 'Sin informacion'


def _dynamic_row_height(text, width_mm, font_pt, base_row_h,
                         avg_char_w_factor=0.52, line_spacing=1.35):
    """
    Calcula el alto de fila necesario para que ``text`` quepa COMPLETO (sin
    truncar), envuelto en varias lineas si hace falta dentro de un ancho de
    ``width_mm`` mm. Heuristica de ancho de caracter promedio (``font_pt`` en
    puntos; 1pt = 0.3528mm) -no mide glifos exactos- pero es suficiente para
    reservar espacio y evitar que el texto se recorte o se monte sobre la
    fila siguiente. Nunca devuelve menos que ``base_row_h``.
    """
    text = ' '.join(str(text or '').split())
    if not text:
        return base_row_h
    avg_char_w_mm = max(0.1, font_pt * avg_char_w_factor * 0.3528)
    chars_per_line = max(10, int(width_mm / avg_char_w_mm))
    lines = max(1, math.ceil(len(text) / chars_per_line))
    if lines <= 1:
        # Cabe en una sola linea: no agrandar filas de la mayoria de los
        # valores (cortos) solo por el margen de seguridad multi-linea.
        return base_row_h
    line_h_mm = font_pt * 0.3528 * line_spacing
    return max(base_row_h, lines * line_h_mm + 1.0)


def _page_header_subtitle(details, is_overview):
    """
    Texto que va bajo el titulo del encabezado de cada pagina. Reemplaza la
    marca fija "GeoCatastro Predial | IGAC Colombia" por el numero predial
    de esa pagina (pedido del usuario, 2026-11-06): identifica de un
    vistazo a que predio corresponde la pagina, en vez de repetir el nombre
    del aplicativo y el modelo de datos. En la pagina de resumen de una
    consulta por conjunto (sin un unico predio) usa una frase descriptiva.
    """
    code = next((str(value) for lbl, value in details
                 if str(lbl).lower().startswith('codigo predial')), '')
    if code:
        return code
    return 'Conjunto de resultados del buscador' if is_overview else ''


def _clean_layer_name(name):
    """Nombre de capa para texto visible en la salida grafica: sin guiones
    ni guiones bajos (p. ej. 'Zonificacion_Amenaza-Inundacion' se muestra
    como 'Zonificacion Amenaza Inundacion')."""
    text = re.sub(r'[_\-]+', ' ', str(name or '')).strip()
    return re.sub(r'\s+', ' ', text)


def _symbol_style_hex(sym):
    """Extrae (color_relleno, color_borde, ancho_borde_mm) de un simbolo de
    QGIS, para que el cuadrito de CONVENCIONES se pinte igual que la
    categoria se ve en el mapa (mismo color y mismo borde), en vez de un
    borde generico fijo para todas las categorias."""
    if sym is None:
        return '#aaaaaa', '#666666', 0.3
    fill = '#aaaaaa'
    try:
        qc = sym.color()
        fill = '#{:02x}{:02x}{:02x}'.format(qc.red(), qc.green(), qc.blue())
    except Exception:
        pass

    outline = None
    outline_w = 0.3
    try:
        layer0 = sym.symbolLayer(0) if sym.symbolLayerCount() else None
    except Exception:
        layer0 = None
    if layer0 is not None:
        stroke_fn = getattr(layer0, 'strokeColor', None)
        if callable(stroke_fn):
            try:
                sc = stroke_fn()
                if sc is not None and sc.alpha() > 0:
                    outline = '#{:02x}{:02x}{:02x}'.format(
                        sc.red(), sc.green(), sc.blue())
            except Exception:
                pass
        width_fn = getattr(layer0, 'strokeWidth', None)
        if callable(width_fn):
            try:
                outline_w = max(0.15, min(0.8, float(width_fn())))
            except Exception:
                pass

    if outline is None:
        try:
            from qgis.core import QgsLineSymbol
            if isinstance(sym, QgsLineSymbol):
                outline = fill
                try:
                    outline_w = max(0.15, min(0.8, float(sym.width())))
                except Exception:
                    pass
        except Exception:
            pass

    if outline is None:
        outline = '#666666'
    return fill, outline, outline_w


def _get_legend_entries(layers, max_entries=200):
    """Retorna lista de (etiqueta, color_relleno, color_borde, ancho_borde)
    para todas las categorias de las capas vectoriales activas y de las
    capas raster clasificadas (p. ej. una zonificacion de uso del suelo o
    de amenaza/riesgo guardada como raster). Las capas raster SIN clases
    (fotografias aereas / ortofotos u otras imagenes continuas) se omiten:
    no tienen un color unico que las represente, y mostrar un cuadro
    generico solo agregaria ruido a las convenciones."""
    entries = []
    for lyr in layers:
        try:
            if not lyr.isValid():
                continue
            name = _clean_layer_name(lyr.name())
            renderer_fn = getattr(lyr, 'renderer', None)
            renderer = renderer_fn() if callable(renderer_fn) else None
            if renderer is None:
                continue

            try:
                sym_items = renderer.legendSymbolItems()
            except Exception:
                sym_items = None
            if sym_items:
                is_multi = len(sym_items) > 1
                for si in sym_items:
                    fill, outline, outline_w = _symbol_style_hex(si.symbol())
                    label = si.label() if is_multi else name
                    entries.append((label or name, fill, outline, outline_w))
                    if len(entries) >= max_entries:
                        return entries
                continue

            try:
                raster_items = renderer.legendSymbologyItems()
            except Exception:
                raster_items = None
            if raster_items:
                for label, qcolor in raster_items:
                    fill = '#{:02x}{:02x}{:02x}'.format(
                        qcolor.red(), qcolor.green(), qcolor.blue())
                    entries.append((str(label) or name, fill, '#666666', 0.2))
                    if len(entries) >= max_entries:
                        return entries
                continue
            # Sin items de leyenda identificables: se omite la capa.
        except (AttributeError, RuntimeError):
            continue
    return entries


def _get_layer_category_unions(layers, exclude_layer, target_crs, project):
    """Retorna lista de (capa, etiqueta, QgsGeometry) con la union de cada
    capa o, si es categorizada, de cada categoria de poligonos visibles,
    reproyectada a target_crs. Excluye exclude_layer (la capa de predios
    consultada)."""
    from qgis.core import QgsWkbTypes, QgsCoordinateTransform, QgsGeometry
    results = []
    for lyr in layers:
        try:
            if lyr is None or lyr is exclude_layer or not lyr.isValid():
                continue
            if QgsWkbTypes.geometryType(lyr.wkbType()) != QgsWkbTypes.PolygonGeometry:
                continue
            name = lyr.name()
            xform = None
            try:
                if lyr.crs().authid() != target_crs.authid():
                    xform = QgsCoordinateTransform(lyr.crs(), target_crs, project)
            except Exception:
                xform = None

            cat_field = None
            try:
                renderer = lyr.renderer()
                type_fn = getattr(renderer, 'type', None)
                if renderer is not None and callable(type_fn) and \
                        type_fn() == 'categorizedSymbol' and \
                        hasattr(renderer, 'classAttribute'):
                    cat_field = renderer.classAttribute()
            except Exception:
                cat_field = None

            def _union_geoms(geoms):
                if not geoms:
                    return None
                try:
                    union = QgsGeometry.unaryUnion(geoms)
                except Exception:
                    return None
                if union is None or union.isEmpty():
                    return None
                if xform is not None:
                    try:
                        union.transform(xform)
                    except Exception:
                        return None
                return union

            if cat_field:
                buckets = {}
                for feat in lyr.getFeatures():
                    if not feat.hasGeometry() or feat.geometry().isEmpty():
                        continue
                    try:
                        key = feat[cat_field]
                    except (KeyError, TypeError):
                        key = None
                    buckets.setdefault(key, []).append(feat.geometry())
                for key, geoms in buckets.items():
                    union = _union_geoms(geoms)
                    if union is None:
                        continue
                    label = str(key) if key not in (None, '', 'NULL') else name
                    results.append((name, label, union))
            else:
                geoms = [f.geometry() for f in lyr.getFeatures()
                         if f.hasGeometry() and not f.geometry().isEmpty()]
                union = _union_geoms(geoms)
                if union is not None:
                    results.append((name, name, union))
        except Exception:
            continue
    return results


def _category_breakdown_for_geometry(geometry, layer_unions, distance_area):
    """Calcula, para cada capa y cada una de sus categorias, el area en
    hectareas y el porcentaje de traslape con geometry. Devuelve una lista
    ordenada de capas ``[(nombre_capa, [(etiqueta, area_ha, pct), ...]), ...]``,
    cada lista de categorias ordenada de mayor a menor porcentaje. Incluye
    TODAS las categorias que realmente se traslapan con geometry, sin limite
    de cantidad ni piso de porcentaje."""
    try:
        area_total = distance_area.measureArea(geometry)
    except Exception:
        area_total = 0.0
    if area_total <= 0:
        return []

    by_layer = {}
    order = []
    for layer_name, label, union in layer_unions:
        try:
            if union is None or union.isEmpty():
                continue
            if not geometry.intersects(union):
                continue
            inter = geometry.intersection(union)
            if inter is None or inter.isEmpty():
                continue
            area_inter = distance_area.measureArea(inter)
            if area_inter <= 1e-6:
                continue
            pct = area_inter / area_total * 100.0
            area_ha = area_inter / 10000.0
        except Exception:
            continue
        if layer_name not in by_layer:
            by_layer[layer_name] = []
            order.append(layer_name)
        by_layer[layer_name].append((label, area_ha, pct))

    breakdown = []
    for layer_name in order:
        entries = sorted(by_layer[layer_name], key=lambda e: e[2], reverse=True)
        breakdown.append((layer_name, entries))
    return breakdown


def _build_clipped_polygon_layers(layers, exclude_layer, predio_geometry,
                                  predio_crs, project):
    """Devuelve una copia de ``layers`` donde cada capa de poligonos (salvo
    exclude_layer) se reemplaza por una capa temporal en memoria, recortada a
    predio_geometry: solo queda la parte de cada entidad que cae dentro del
    predio. Conserva el renderer original (misma simbologia/colores que la
    leyenda) y queda con opacidad 50%. El resto de capas (lineas, puntos,
    raster) se deja igual, para dar contexto. Nada se escribe en los datos
    originales; las capas resultantes solo existen en memoria durante la
    exportacion."""
    from qgis.core import (
        QgsWkbTypes, QgsCoordinateTransform, QgsVectorLayer, QgsFeature,
        QgsGeometry,
    )
    result = []
    for lyr in layers:
        try:
            if (lyr is None or lyr is exclude_layer or not lyr.isValid()
                    or not hasattr(lyr, 'wkbType')
                    or QgsWkbTypes.geometryType(lyr.wkbType()) != QgsWkbTypes.PolygonGeometry):
                result.append(lyr)
                continue

            clip_geom = predio_geometry
            try:
                if lyr.crs().authid() != predio_crs.authid():
                    xform = QgsCoordinateTransform(predio_crs, lyr.crs(), project)
                    clip_geom = QgsGeometry(predio_geometry)
                    clip_geom.transform(xform)
            except Exception:
                clip_geom = predio_geometry

            auth_id = lyr.crs().authid()
            uri = QgsWkbTypes.displayString(lyr.wkbType())
            if auth_id:
                uri += '?crs=' + auth_id
            clipped = QgsVectorLayer(uri, lyr.name(), 'memory')
            if auth_id == '':
                clipped.setCrs(lyr.crs())
            clipped.dataProvider().addAttributes(lyr.fields())
            clipped.updateFields()

            new_features = []
            for feat in lyr.getFeatures():
                if not feat.hasGeometry() or feat.geometry().isEmpty():
                    continue
                if not feat.geometry().intersects(clip_geom):
                    continue
                inter = feat.geometry().intersection(clip_geom)
                if inter is None or inter.isEmpty():
                    continue
                new_feat = QgsFeature(clipped.fields())
                new_feat.setGeometry(inter)
                new_feat.setAttributes(feat.attributes())
                new_features.append(new_feat)

            if not new_features:
                continue
            clipped.dataProvider().addFeatures(new_features)
            clipped.updateExtents()
            try:
                clipped.setRenderer(lyr.renderer().clone())
            except Exception:
                pass
            try:
                clipped.setOpacity(0.5)
            except AttributeError:
                pass
            result.append(clipped)
        except Exception:
            result.append(lyr)
            continue
    return result


DEFAULT_THEME_COLOR = '#173f73'


def _theme_colors(base_hex):
    """Deriva el resto de la paleta (acento, fondos claros, texto legible) a
    partir de UN solo color elegido por el usuario, para que la salida
    grafica no dependa de un azul institucional fijo. Es una heuristica
    sobre HSL, no una proporcion exacta: busca que se vea coherente para
    cualquier color, no replicar un calculo de diseno preciso.
    """
    from qgis.PyQt.QtGui import QColor
    base = QColor(base_hex)
    if not base.isValid():
        base = QColor(DEFAULT_THEME_COLOR)
    h, s, l, _a = base.getHsl()
    if h < 0:
        h = 0

    def _hsl(hue, sat, light):
        return QColor.fromHsl(
            hue, max(0, min(255, int(sat))), max(0, min(255, int(light)))
        ).name()

    def _text_for(light):
        return '#ffffff' if light < 150 else '#1a1a1a'

    accent_l = max(110, min(170, l + 85))
    accent_s = max(s, 130)
    accent = _hsl(h, accent_s, accent_l)
    return {
        'dark': base.name(),
        'accent': accent,
        'wash': _hsl(h, min(s, 50), 246),
        'wash_border': _hsl(h, min(s, 90), 205),
        'subtitle': _hsl(h, min(s, 60), 225),
        'text_on_dark': _text_for(l),
        'text_on_accent': _text_for(accent_l),
    }


def _north_arrow_svg_path():
    """Ruta a un icono de rosa de los vientos incluido con QGIS, o None si
    esta instalacion no lo trae (la salida grafica sigue funcionando sin
    el icono, simplemente no se dibuja)."""
    try:
        from qgis.core import QgsApplication
        candidate = os.path.join(
            QgsApplication.pkgDataPath(), 'svg', 'arrows', 'NorthArrow_02.svg')
        return candidate if os.path.isfile(candidate) else None
    except Exception:
        return None


def export_predial_map_pdf(iface, layer, feature_id, details, output_path,
                           theme_color=DEFAULT_THEME_COLOR):
    """Compatibilidad: exporta una ficha de un solo predio."""
    return export_predial_selection_pdf(
        iface, layer, [(feature_id, details)], output_path,
        theme_color=theme_color)


def export_predial_selection_pdf(iface, layer, selected_records, output_path,
                                overview=False, theme_color=DEFAULT_THEME_COLOR):
    """Exporta un PDF multipagina, con una ficha por predio seleccionado.

    ``selected_records`` contiene pares ``(feature_id, details)``. ``details``
    es una secuencia ordenada de hasta catorce pares ``(etiqueta, valor)``.
    ``theme_color`` es el color elegido por el usuario para encabezados,
    barras de seccion, pie de pagina y borde del mapa; el resto de la
    plantilla (texto, filas alternadas, colores de la leyenda) no cambia.
    """
    from qgis.PyQt.QtCore import Qt, QDateTime, QSizeF
    from qgis.PyQt.QtGui import QColor, QFont
    from qgis.core import (
        QgsFeature, QgsFillSymbol, QgsLayoutExporter, QgsLayoutItemLabel,
        QgsLayoutItemMap, QgsLayoutItemPage, QgsLayoutItemShape,
        QgsLayoutPoint, QgsLayoutSize, QgsLineSymbol, QgsMarkerSymbol,
        QgsPrintLayout, QgsProject, QgsRectangle, QgsUnitTypes,
        QgsVectorLayer, QgsWkbTypes, QgsGeometry,
        QgsCoordinateReferenceSystem, QgsCoordinateTransform,
        QgsLayoutItemMapGrid, QgsDistanceArea, QgsTextFormat,
        QgsTextBackgroundSettings, QgsTextShadowSettings, QgsLayoutItemPicture,
    )

    theme = _theme_colors(theme_color)
    north_arrow_svg = _north_arrow_svg_path()

    records = list(selected_records or [])
    if not records:
        raise ValueError('No hay predios seleccionados para exportar.')
    if layer is None or not layer.isValid():
        raise ValueError('La capa de la consulta ya no esta disponible.')
    if not layer.crs().isValid():
        raise ValueError('Define el sistema de coordenadas de la capa antes de exportar.')
    original_records = list(records)
    if overview:
        territories = sorted({str(value) for _, details in records
                              for label, value in details
                              if label == 'Manzana o vereda' and value})
        records.insert(0, ([fid for fid, _ in records], [
            ('Tipo de salida', 'Conjunto de resultados del buscador'),
            ('Cantidad de elementos', str(len(original_records))),
            ('Veredas consultadas', ', '.join(territories)),
            ('Capa de origen', layer.name()),
            ('Contenido', 'Mapa conjunto y fichas individuales a continuacion'),
            ('Limite representado', 'Geometrias consultadas; no implica limite oficial de vereda'),
        ]))

    project = QgsProject.instance()
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName('Fichas Prediales Temporales')

    def configure_page(page):
        changed = page.setPageSize('Letter', QgsLayoutItemPage.Portrait)
        if not changed:
            page.setPageSize(QgsLayoutSize(
                LETTER_WIDTH_MM, LETTER_HEIGHT_MM,
                QgsUnitTypes.LayoutMillimeters))

    configure_page(layout.pageCollection().page(0))
    last_page_index = [0]

    def next_page_index():
        """Agrega una pagina nueva (mismo tamano carta) y devuelve su indice."""
        page = QgsLayoutItemPage(layout)
        configure_page(page)
        layout.pageCollection().addPage(page)
        last_page_index[0] += 1
        return last_page_index[0]

    def move_to_page(item, x, y, page_index):
        point = QgsLayoutPoint(x, y, QgsUnitTypes.LayoutMillimeters)
        item.attemptMove(point, True, False, page_index)

    def add_shape(x, y, width, height, fill, page_index,
                  stroke='#cbd5e1', stroke_width=0.25):
        item = QgsLayoutItemShape(layout)
        item.setShapeType(QgsLayoutItemShape.Rectangle)
        item.setSymbol(QgsFillSymbol.createSimple({
            'color': fill,
            'outline_color': stroke,
            'outline_width': str(stroke_width),
            'outline_width_unit': 'MM',
        }))
        layout.addLayoutItem(item)
        move_to_page(item, x, y, page_index)
        item.attemptResize(QgsLayoutSize(
            width, height, QgsUnitTypes.LayoutMillimeters))
        return item

    def add_label(text, x, y, width, height, page_index, size=8.0,
                  color='#243447', bold=False, align=Qt.AlignLeft,
                  valign=Qt.AlignVCenter, margin=1.2):
        item = QgsLayoutItemLabel(layout)
        item.setText(str(text))
        font = QFont('Arial')
        font.setPointSizeF(float(size))
        font.setBold(bool(bold))
        item.setFont(font)
        item.setFontColor(QColor(color))
        item.setHAlign(align)
        item.setVAlign(valign)
        item.setMargin(margin)
        layout.addLayoutItem(item)
        move_to_page(item, x, y, page_index)
        item.attemptResize(QgsLayoutSize(
            width, height, QgsUnitTypes.LayoutMillimeters))
        return item

    # ── Flujo de tablas con altura de fila fija y paginas de continuacion ──
    CONTENT_LEFT = 15.0
    CONTENT_WIDTH = 185.9
    CONTENT_BOTTOM = 264.0   # limite inferior del contenido (3mm antes del pie)
    SECTION_HDR_H = 6.0      # encabezados principales (CONVENCIONES, INFORMACION)
    LEGEND_ROW_H = 5.6
    LEGEND_SWATCH = 3.6      # lado del cuadrito de color en CONVENCIONES (mm)
    BREAKDOWN_HDR_H = 4.0
    BREAKDOWN_ROW_H = 3.6
    INFO_HDR_H = 7.0
    INFO_ROW_H = 4.2
    SECTION_GAP = 1.5

    def render_section(cursor, new_page_fn, title, header_h, header_bg,
                        header_fg, header_font_size, row_specs,
                        continuation_suffix=' (continuacion)'):
        """Dibuja un encabezado y sus filas (``row_specs``: lista de
        ``(alto, draw_fn)`` donde ``draw_fn(page_index, y)`` pinta esa fila).
        Si no caben antes de CONTENT_BOTTOM, crea una pagina de continuacion
        (via ``new_page_fn``) y repite el encabezado alli, para que ninguna
        fila quede huerfana ni se monte sobre el pie de pagina."""
        if not row_specs:
            return

        def draw_header(pi, y, label_text):
            add_shape(CONTENT_LEFT, y, CONTENT_WIDTH, header_h, header_bg,
                      pi, header_bg, 0)
            add_label(label_text, CONTENT_LEFT + 3, y, CONTENT_WIDTH - 6,
                      header_h, pi, header_font_size, header_fg, True, margin=0.6)

        first_h = row_specs[0][0]
        if cursor['y'] + header_h + first_h > CONTENT_BOTTOM:
            new_page_fn(cursor)
        draw_header(cursor['page_index'], cursor['y'], title)
        cursor['y'] += header_h
        for h, draw_fn in row_specs:
            if cursor['y'] + h > CONTENT_BOTTOM:
                new_page_fn(cursor)
                draw_header(cursor['page_index'], cursor['y'], title + continuation_suffix)
                cursor['y'] += header_h
            draw_fn(cursor['page_index'], cursor['y'])
            cursor['y'] += h
        cursor['y'] += SECTION_GAP

    canvas_layers = []
    try:
        root = QgsProject.instance().layerTreeRoot()
        for node in root.findLayers():
            if node.isVisible() and node.layer() and node.layer().isValid():
                canvas_layers.append(node.layer())
    except Exception:
        try:
            canvas_layers = list(iface.mapCanvas().layers())
        except (AttributeError, RuntimeError):
            pass
    if layer not in canvas_layers:
        canvas_layers.insert(0, layer)

    # ── Recorte/traslape automatico contra las capas activas ────────────
    distance_area = QgsDistanceArea()
    distance_area.setSourceCrs(layer.crs(), project.transformContext())
    distance_area.setEllipsoid(project.ellipsoid())
    category_unions = _get_layer_category_unions(
        canvas_layers, layer, layer.crs(), project)

    highlight_layers = []
    clipped_layers_keepalive = []
    scales = []
    page_number_labels = []  # (label_item, numero_de_pagina) a completar al final
    date_text = QDateTime.currentDateTime().toString('dd/MM/yyyy HH:mm')

    for record_index, (feature_id, details) in enumerate(records):
        main_page_index = 0 if record_index == 0 else next_page_index()
        page_index = main_page_index  # usado por el bloque de mapa/encabezado
        is_overview = isinstance(feature_id, list)
        feature = layer.getFeature(feature_id[0] if is_overview else feature_id)
        if feature is None or not feature.isValid() or not feature.hasGeometry():
            raise ValueError(
                'El predio {} no tiene una geometria valida.'.format(feature_id))
        geometry = feature.geometry()
        if is_overview:
            geometries = []
            for fid in feature_id:
                item = layer.getFeature(fid)
                if not item.isValid() or not item.hasGeometry() or item.geometry().isEmpty():
                    raise ValueError('El elemento {} no tiene geometria para el mapa conjunto.'.format(fid))
                geometries.append(item.geometry())
            geometry = QgsGeometry.unaryUnion(geometries)
        if geometry is None or geometry.isEmpty():
            raise ValueError(
                'El predio {} tiene una geometria vacia.'.format(feature_id))

        details = list(details or [])
        breakdown = []
        if not is_overview and category_unions:
            breakdown = _category_breakdown_for_geometry(
                geometry, category_unions, distance_area)

        # Numero predial de esta pagina: se reutiliza en el encabezado, en
        # el de las paginas de continuacion y en el pie de pagina.
        code = next((str(value) for lbl, value in details
                     if str(lbl).lower().startswith('codigo predial')), '')
        header_subtitle = _page_header_subtitle(details, is_overview)

        add_shape(10, 9, 195.9, 15, theme['dark'], page_index,
                  theme['dark'], 0)
        if is_overview:
            # Sin un unico predio que identificar, se conserva el titulo.
            add_label('CONSULTA / VEREDA', 14, 10, 130, 8, page_index,
                      15, theme['text_on_dark'], True)
            add_label(header_subtitle, 14, 18, 130, 5,
                      page_index, 7.5, theme['subtitle'])
        else:
            # Ficha de un predio: sin titulo "FICHA CATASTRAL PREDIAL", solo
            # el numero predial, mas grande (pedido del usuario, 2026-11-09).
            add_label(header_subtitle, 14, 11, 170, 13, page_index,
                      17, theme['text_on_dark'], True)
        add_label(date_text, 150, 11, 51, 10, page_index, 8, theme['text_on_dark'],
                  False, Qt.AlignRight)

        map_item = QgsLayoutItemMap(layout)
        layout.addLayoutItem(map_item)
        move_to_page(map_item, 15, 31, page_index)
        map_item.attemptResize(QgsLayoutSize(
            185.9, 116, QgsUnitTypes.LayoutMillimeters))
        map_item.setFrameEnabled(True)
        map_item.setFrameStrokeColor(QColor(theme['dark']))
        try:
            map_item.setCrs(layer.crs())
        except AttributeError:
            pass

        highlight_layer = None
        try:
            geometry_name = QgsWkbTypes.displayString(geometry.wkbType())
            auth_id = layer.crs().authid()
            uri = geometry_name + ('?crs=' + auth_id if auth_id else '')
            highlight_layer = QgsVectorLayer(
                uri, 'Predio consultado {}'.format(page_index + 1), 'memory')
            if auth_id == '':
                highlight_layer.setCrs(layer.crs())
            highlight_feature = QgsFeature()
            highlight_feature.setGeometry(geometry)
            highlight_layer.dataProvider().addFeature(highlight_feature)
            geometry_type = QgsWkbTypes.geometryType(layer.wkbType())
            if geometry_type == QgsWkbTypes.PolygonGeometry:
                symbol = QgsFillSymbol.createSimple({
                    'color': '255,193,7,70',
                    'outline_color': '220,53,69,255',
                    'outline_width': '1.1',
                })
            elif geometry_type == QgsWkbTypes.LineGeometry:
                symbol = QgsLineSymbol.createSimple({
                    'color': '220,53,69,255', 'width': '1.5'})
            else:
                symbol = QgsMarkerSymbol.createSimple({
                    'color': '255,193,7,255',
                    'outline_color': '220,53,69,255', 'size': '4.5'})
            highlight_layer.renderer().setSymbol(symbol)
            try:
                highlight_layer.setOpacity(0.5)
            except AttributeError:
                pass
            highlight_layers.append(highlight_layer)
        except Exception:
            highlight_layer = None

        clipped_layers = _build_clipped_polygon_layers(
            canvas_layers, layer, geometry, layer.crs(), project)
        clipped_layers_keepalive.extend(clipped_layers)

        map_layers = ([highlight_layer]
                      if highlight_layer and highlight_layer.isValid()
                      else []) + clipped_layers
        map_item.setLayers(map_layers)
        map_item.setKeepLayerSet(True)

        bounds = geometry.boundingBox()
        fallback = 0.001 if layer.crs().isGeographic() else 10.0
        xmin, ymin, xmax, ymax = expanded_bounds(
            bounds.xMinimum(), bounds.yMinimum(),
            bounds.xMaximum(), bounds.yMaximum(), fallback_span=fallback)
        extent = QgsRectangle(xmin, ymin, xmax, ymax)
        try:
            map_item.zoomToExtent(extent)
        except AttributeError:
            map_item.setExtent(extent)
        map_item.refresh()

        geographic = QgsCoordinateReferenceSystem('EPSG:4326')
        geo_extent = QgsCoordinateTransform(layer.crs(), geographic, project).transformBoundingBox(map_item.extent())
        span = max(geo_extent.width(), geo_extent.height()) / 4.0
        if not math.isfinite(span) or span <= 0:
            raise ValueError('No se pudo calcular la grilla geografica de la seleccion.')
        magnitude = 10 ** math.floor(math.log10(span))
        interval = next(step * magnitude for step in (1, 2, 5, 10) if step * magnitude >= span)
        grid = map_item.grid()
        grid.setEnabled(True)
        grid.setCrs(geographic)
        grid.setIntervalX(interval)
        grid.setIntervalY(interval)
        grid.setStyle(QgsLayoutItemMapGrid.Solid)
        grid.setLineSymbol(QgsLineSymbol.createSimple({'line_color': '60,80,100,110', 'line_width': '0.15'}))

        # Coordenadas geograficas en grados/minutos/segundos (no decimales).
        grid.setAnnotationEnabled(True)
        grid.setAnnotationFormat(QgsLayoutItemMapGrid.DegreeMinuteSecond)
        grid.setAnnotationPrecision(0)
        grid.setAnnotationFont(QFont('Arial', 6))
        grid.setAnnotationFrameDistance(1.0)

        # Cada etiqueta de grados/minutos/segundos queda encuadrada en su
        # propia caja blanca (con sombra), para que se lea sin importar que
        # haya debajo (foto aerea, bosque, zonas oscuras, etc.).
        annotation_format = QgsTextFormat()
        annotation_format.setFont(QFont('Arial', 6))
        annotation_format.setSize(6)
        annotation_format.setSizeUnit(QgsUnitTypes.RenderPoints)
        annotation_format.setColor(QColor(theme['dark']))

        background = QgsTextBackgroundSettings()
        background.setEnabled(True)
        background.setType(QgsTextBackgroundSettings.ShapeRectangle)
        background.setSizeType(QgsTextBackgroundSettings.SizeBuffer)
        background.setSize(QSizeF(1.2, 0.8))
        background.setSizeUnit(QgsUnitTypes.RenderMillimeters)
        background.setFillColor(QColor(255, 255, 255, 235))
        background.setStrokeColor(QColor(theme['wash_border']))
        background.setStrokeWidth(0.15)
        background.setStrokeWidthUnit(QgsUnitTypes.RenderMillimeters)
        background.setRadii(QSizeF(0.6, 0.6))
        background.setRadiiUnit(QgsUnitTypes.RenderMillimeters)
        annotation_format.setBackground(background)

        shadow = QgsTextShadowSettings()
        shadow.setEnabled(True)
        shadow.setOffsetAngle(135)
        shadow.setOffsetDistance(1.0)
        shadow.setOffsetUnit(QgsUnitTypes.RenderMillimeters)
        shadow.setBlurRadius(1.0)
        shadow.setBlurRadiusUnit(QgsUnitTypes.RenderMillimeters)
        shadow.setColor(QColor('#000000'))
        shadow.setOpacity(0.45)
        annotation_format.setShadow(shadow)

        grid.setAnnotationTextFormat(annotation_format)

        for side in (QgsLayoutItemMapGrid.Left, QgsLayoutItemMapGrid.Right,
                     QgsLayoutItemMapGrid.Top, QgsLayoutItemMapGrid.Bottom):
            grid.setAnnotationPosition(QgsLayoutItemMapGrid.InsideMapFrame, side)
        map_item.refresh()

        add_shape(15, 148.5, 185.9, 8, theme['wash'], page_index,
                  theme['wash_border'], 0.25)
        scale = max(1, int(round(map_item.scale(), -1)))
        scales.append(scale)
        add_label('Escala aproximada 1:{:,}'.format(scale).replace(',', '.'),
                  18, 149, 78, 7, page_index, 7.5, theme['dark'], True)
        crs_text = 'Grilla WGS 84 (geograficas) | EPSG:4326'
        add_label(crs_text, 100, 149, 95, 7, page_index, 7.5,
                  theme['dark'], False, Qt.AlignCenter)

        # Rosa de los vientos en la esquina superior derecha del mapa.
        if north_arrow_svg:
            compass_size = 11.0
            compass_margin = 2.0
            compass_x = 15 + 185.9 - compass_size - compass_margin
            compass_y = 31 + compass_margin
            add_shape(compass_x - 1.2, compass_y - 1.2,
                      compass_size + 2.4, compass_size + 2.4,
                      '#ffffff', page_index, theme['wash_border'], 0.2)
            north_item = QgsLayoutItemPicture(layout)
            north_item.setPicturePath(north_arrow_svg)
            layout.addLayoutItem(north_item)
            move_to_page(north_item, compass_x, compass_y, page_index)
            north_item.attemptResize(QgsLayoutSize(
                compass_size, compass_size, QgsUnitTypes.LayoutMillimeters))

        # ── Convenciones / distribucion por capa / info, en paginas ──────
        # que fluyen: cada fila tiene altura fija y legible; si el contenido
        # no cabe antes del pie de pagina, continua en pagina(s) nuevas para
        # este mismo predio, repitiendo el encabezado de la tabla.

        def draw_footer(pi):
            add_label('Documento informativo generado desde la seleccion activa '
                      'de QGIS. Verifique contra las fuentes catastrales oficiales.',
                      15, 267, 185.9, 7, pi, 6.8, '#607487', False,
                      Qt.AlignJustify)
            add_shape(15, 274.5, 185.9, 0.7, theme['dark'], pi, theme['dark'], 0)
            add_label('GeoCatastro Predial', 15, 275.5, 55, 3.5, pi,
                      7, theme['dark'], True, margin=0)
            page_label = add_label('Pagina {} de ?'.format(pi + 1), 72, 275.5,
                                   48, 3.5, pi, 7, '#607487', False,
                                   Qt.AlignCenter, margin=0)
            page_number_labels.append((page_label, pi + 1))
            add_label('Resultados: {}'.format(len(original_records)) if is_overview
                      else 'Predio: ' + _short_text(code, 34),
                      120, 275.5, 80.9, 3.5, pi, 7, '#607487', False,
                      Qt.AlignRight, margin=0)

        def new_continuation_page(cursor):
            pi = next_page_index()
            cursor['page_index'] = pi
            cursor['y'] = 27.0  # deja libre el banner superior (termina en y=24)
            add_shape(10, 9, 195.9, 15, theme['dark'], pi, theme['dark'], 0)
            if is_overview:
                add_label('CONSULTA / VEREDA (continuacion)', 14, 10, 170, 8, pi, 12,
                          theme['text_on_dark'], True)
                add_label(header_subtitle, 14, 18, 130, 5,
                          pi, 7.5, theme['subtitle'])
            else:
                add_label(header_subtitle + ' (continuacion)', 14, 11, 170, 13, pi,
                          15, theme['text_on_dark'], True)
            add_label(date_text, 150, 11, 51, 10, pi, 8, theme['text_on_dark'],
                      False, Qt.AlignRight)
            draw_footer(pi)

        draw_footer(main_page_index)
        cursor = {'page_index': main_page_index, 'y': 157.0}

        # CONVENCIONES
        legend_entries = _get_legend_entries(canvas_layers, max_entries=200)
        if legend_entries:
            n_leg_rows = math.ceil(len(legend_entries) / 2)
            legend_col_w = 92.95
            legend_swatch_x = 1.8
            legend_label_x = legend_swatch_x + LEGEND_SWATCH + 1.4
            legend_label_w = legend_col_w - legend_label_x - 0.5
            legend_rows = []
            for ri in range(n_leg_rows):
                pair = legend_entries[ri * 2: ri * 2 + 2]
                row_h = max(
                    _dynamic_row_height(name, legend_label_w, 6.3, LEGEND_ROW_H)
                    for name, *_rest in pair)

                def make_legend_draw(pair=pair, ri=ri, row_h=row_h):
                    def draw(pi, y):
                        row_bg = '#ffffff' if ri % 2 == 0 else '#f1f5f9'
                        for ci, (entry_name, fill, outline, outline_w) in enumerate(pair):
                            lx = CONTENT_LEFT + ci * legend_col_w
                            add_shape(lx, y, legend_col_w, row_h, row_bg,
                                      pi, '#d7e0e8', 0.15)
                            add_shape(lx + legend_swatch_x,
                                      y + row_h / 2 - LEGEND_SWATCH / 2,
                                      LEGEND_SWATCH, LEGEND_SWATCH,
                                      fill, pi, outline, outline_w)
                            add_label(_full_text(entry_name), lx + legend_label_x, y,
                                      legend_label_w, row_h, pi, 6.3,
                                      '#203040', align=Qt.AlignJustify, margin=0)
                    return draw
                legend_rows.append((row_h, make_legend_draw()))
        else:
            def draw_no_legend(pi, y):
                add_label('Sin capas activas visibles en el mapa.',
                          CONTENT_LEFT + 3, y, CONTENT_WIDTH - 6, LEGEND_ROW_H,
                          pi, 7, '#607487', margin=1)
            legend_rows = [(LEGEND_ROW_H, draw_no_legend)]

        render_section(cursor, new_continuation_page, 'CONVENCIONES',
                       SECTION_HDR_H, theme['accent'], theme['text_on_accent'],
                       8.5, legend_rows)

        # DISTRIBUCION POR CAPA: una seccion (con su propio encabezado) por
        # cada capa activa con categorias, para que nunca quede un
        # encabezado huerfano sin sus filas.
        BREAKDOWN_LABEL_W = 120.0
        for layer_name, entries in breakdown:
            if not entries:
                continue
            cat_rows = []
            for ei, (cat_label, area_ha, pct) in enumerate(entries):
                row_h = _dynamic_row_height(
                    cat_label, BREAKDOWN_LABEL_W - 2, 6.0, BREAKDOWN_ROW_H)

                def make_cat_draw(cat_label=cat_label, area_ha=area_ha, pct=pct,
                                   ei=ei, row_h=row_h):
                    def draw(pi, y):
                        row_bg = '#ffffff' if ei % 2 == 0 else '#f1f5f9'
                        add_shape(CONTENT_LEFT, y, CONTENT_WIDTH, row_h,
                                  row_bg, pi, '#d7e0e8', 0.15)
                        add_label(_full_text(cat_label), CONTENT_LEFT + 2, y,
                                  BREAKDOWN_LABEL_W, row_h, pi, 6.0, '#203040',
                                  align=Qt.AlignJustify, margin=0)
                        add_label('{:.2f} ha ({:.1f}%)'.format(area_ha, pct),
                                  CONTENT_LEFT + 122, y, 61.9, row_h,
                                  pi, 6.0, '#203040', True, Qt.AlignRight, margin=0.6)
                    return draw
                cat_rows.append((row_h, make_cat_draw()))
            render_section(cursor, new_continuation_page,
                           _short_text(_clean_layer_name(layer_name), 110),
                           BREAKDOWN_HDR_H, theme['dark'], theme['text_on_dark'],
                           6.5, cat_rows)

        # INFORMACION DEL PREDIO
        INFO_VALUE_W = 131.0
        info_rows = []
        for index, (lbl, value) in enumerate(details):
            if not lbl:
                continue
            row_h = _dynamic_row_height(value, INFO_VALUE_W - 2, 7.0, INFO_ROW_H)

            def make_info_draw(lbl=lbl, value=value, index=index, row_h=row_h):
                def draw(pi, y):
                    add_shape(CONTENT_LEFT, y, CONTENT_WIDTH, row_h,
                              '#ffffff' if index % 2 == 0 else '#f6f9fc',
                              pi, '#d7e0e8', 0.2)
                    add_label(lbl, CONTENT_LEFT + 1, y, 51, row_h, pi, 7,
                              '#607487', True, margin=0)
                    add_label(_full_text(value), CONTENT_LEFT + 53, y, INFO_VALUE_W,
                              row_h, pi, 7, '#203040', align=Qt.AlignJustify, margin=0)
                return draw
            info_rows.append((row_h, make_info_draw()))

        render_section(cursor, new_continuation_page,
                       'INFORMACION DE LA CONSULTA' if is_overview else 'INFORMACION DEL PREDIO',
                       INFO_HDR_H, theme['accent'], theme['text_on_accent'], 9,
                       info_rows)

    page_count = last_page_index[0] + 1
    for label_item, page_num in page_number_labels:
        label_item.setText('Pagina {} de {}'.format(page_num, page_count))

    output_path = os.path.abspath(output_path)
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    settings = QgsLayoutExporter.PdfExportSettings()
    settings.dpi = 300
    exporter = QgsLayoutExporter(layout)
    result = exporter.exportToPdf(output_path, settings)
    if result != QgsLayoutExporter.Success:
        message = 'No fue posible exportar el PDF (codigo {}).'.format(result)
        try:
            if exporter.errorMessage():
                message += ' ' + exporter.errorMessage()
        except AttributeError:
            pass
        raise RuntimeError(message)
    if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError('QGIS no creo un archivo PDF valido.')
    return {
        'path': output_path,
        'scale': scales[0],
        'scales': scales,
        'feature_id': original_records[0][0],
        'feature_ids': [record[0] for record in original_records],
        'page_count': page_count,
    }
