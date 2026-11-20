# -*- coding: utf-8 -*-
"""
ProjectGIS - Plugin principal para QGIS
Convierte tablas de coordenadas Excel a Shapefile/GeoPackage
"""
import os
import unicodedata
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.PyQt.QtGui import QIcon
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsPointXY,
    QgsCoordinateReferenceSystem,
    QgsVectorFileWriter,
    QgsWkbTypes,
    QgsMessageLog,
)
from qgis.PyQt.QtCore import QVariant, QCoreApplication

from .core.excel_reader import ExcelReader
from .core.coordinate_parser import CoordinateParser, CoordinateFormat
from .core.geometry_calculator import GeometryCalculator
from .core.shapefile_exporter import ShapefileExporter
from .core.geopackage_exporter import GeoPackageExporter
from .core.csv_exporter import CSVExporter
from .utils.crs_utils import (
    CRS_PRESETS,
    AUTO_DETECT_CRS_LABEL,
    get_epsg_from_name,
    utm_epsg_from_lon_lat,
)
from .utils.compatibility import log_info, log_error, log_warning


class ProjectGIS:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.action = None
        self.dialog = None

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
        else:
            icon = QIcon.fromTheme("applications-gis", QIcon())

        self.action = QAction(
            icon,
            "ProjectGIS",
            self.iface.mainWindow()
        )
        self.action.setText("ProjectGIS - Excel a Shapefile")
        self.action.setToolTip(
            "Convierte tablas de coordenadas Excel a Shapefile/GeoPackage"
        )
        self.action.triggered.connect(self.run)

        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("ProjectGIS", self.action)

    def unload(self):
        if self.action:
            self.iface.removeToolBarIcon(self.action)
            self.iface.removePluginMenu("ProjectGIS", self.action)

    def run(self):
        from .dialogs.main_dialog import ProjectGISDialog

        self.dialog = ProjectGISDialog(self.iface.mainWindow())
        self.dialog.set_crs_list(list(CRS_PRESETS.keys()))
        self.dialog.file_selected.connect(self._on_file_selected)
        self.dialog.process_complete.connect(self._on_process)
        self.dialog.show()

    def _on_file_selected(self, file_path):
        try:
            reader = ExcelReader(file_path)
            reader.open()

            sheets = reader.get_sheet_names()
            self.dialog.set_sheets(sheets)

            headers, rows = reader.read_sheet(sheets[0] if sheets else None)
            self.dialog.set_column_names(headers)
            self.dialog.set_preview_data(headers, rows)

            x_col, y_col, z_col = reader.detect_coordinate_columns(headers, rows)
            if x_col is not None and x_col < len(headers):
                self.dialog.cmb_x_col.setCurrentIndex(x_col)
            if y_col is not None and y_col < len(headers):
                self.dialog.cmb_y_col.setCurrentIndex(y_col)
            if z_col is not None and z_col < len(headers):
                self.dialog.cmb_z_col.setCurrentIndex(z_col + 1)

            reader.close()
            log_info(f"Archivo cargado: {len(sheets)} hojas, {len(rows)} filas")

        except Exception as e:
            log_error(f"Error al cargar archivo: {str(e)}")
            self.dialog.set_error(f"Error al cargar el archivo:\n{str(e)}")

    def _on_process(self, success, message):
        if not success:
            return

        config = self.dialog.get_config()
        self.dialog.progress_bar.setRange(0, 0)

        try:
            reader = ExcelReader(config["file_path"])
            reader.open()

            all_features = []
            sheets = config["sheets"]
            type_counts = {"decimal": 0, "utm": 0}
            zone_hint = None

            for sheet_name in sheets:
                headers, rows = reader.read_sheet(sheet_name)
                features, sheet_stats = self._process_sheet(
                    headers, rows, config
                )
                all_features.extend(features)
                type_counts["decimal"] += sheet_stats["decimal"]
                type_counts["utm"] += sheet_stats["utm"]
                if zone_hint is None and sheet_stats["zone_hint"]:
                    zone_hint = sheet_stats["zone_hint"]

            reader.close()

            if not all_features:
                self.dialog.set_error("No se pudieron procesar las coordenadas.")
                return

            crs_name = config["crs"]
            if crs_name == AUTO_DETECT_CRS_LABEL:
                crs_epsg, crs_label, detect_error = self._detect_crs(
                    type_counts, zone_hint
                )
                if detect_error:
                    self.dialog.set_error(detect_error)
                    return
            else:
                crs_epsg = get_epsg_from_name(crs_name)
                crs_label = crs_name

            mismatch_error = self._validate_crs_matches_data(crs_epsg, all_features)
            if mismatch_error:
                self.dialog.set_error(mismatch_error)
                return

            output_dir = config["output_dir"]
            layer_name = config["layer_name"]

            exported = []
            failed = []
            if config["export_shp"]:
                shp_path = os.path.join(output_dir, f"{layer_name}.shp")
                if ShapefileExporter.export(
                    all_features, shp_path, crs_epsg, layer_name
                ):
                    exported.append("Shapefile")
                else:
                    failed.append("Shapefile")

            if config["export_gpkg"]:
                gpkg_path = os.path.join(output_dir, f"{layer_name}.gpkg")
                if GeoPackageExporter.export(
                    all_features, gpkg_path, crs_epsg, layer_name
                ):
                    exported.append("GeoPackage")
                else:
                    failed.append("GeoPackage")

            if config["export_csv"]:
                csv_path = os.path.join(output_dir, f"{layer_name}.csv")
                if CSVExporter.export(all_features, csv_path):
                    exported.append("CSV")
                else:
                    failed.append("CSV")

            self.dialog.progress_bar.setRange(0, 100)
            self.dialog.progress_bar.setValue(100)

            if exported:
                if any(fmt in exported for fmt in ("Shapefile", "GeoPackage")):
                    self._zoom_to_layer(layer_name)

                message = (
                    f"Procesamiento completado!\n\n"
                    f"Archivos generados:\n"
                    f"- {len(all_features)} registros procesados\n"
                    f"- Formatos: {', '.join(exported)}\n"
                    f"- Sistema de coordenadas usado: {crs_label}\n"
                    f"- Carpeta: {output_dir}"
                )
                if failed:
                    message += (
                        f"\n\nATENCION: fallaron estos formatos: {', '.join(failed)}."
                        f"\nRevise el panel de mensajes de QGIS "
                        f"(pestaña 'ProjectGIS') para ver el detalle del error."
                    )
                self.dialog.set_success(message)
            else:
                self.dialog.set_error(
                    "No se pudieron generar los archivos de salida.\n\n"
                    "Revise el panel de mensajes de QGIS "
                    "(pestaña 'ProjectGIS') para ver el detalle del error."
                )

        except Exception as e:
            log_error(f"Error en procesamiento: {str(e)}")
            self.dialog.set_error(f"Error durante el procesamiento:\n{str(e)}")

    def _detect_crs(self, type_counts, zone_hint):
        decimal_n = type_counts["decimal"]
        utm_n = type_counts["utm"]

        if decimal_n >= utm_n:
            return (
                4326,
                "WGS 84 (EPSG:4326) - detectado: coordenadas geograficas decimales",
                None,
            )

        if zone_hint:
            zone, hemisphere = zone_hint
            epsg = 32600 + zone if hemisphere == "N" else 32700 + zone
            label = (
                f"WGS 84 / UTM Zona {zone}{hemisphere} (EPSG:{epsg}) "
                f"- detectado desde columna de zona"
            )
            return epsg, label, None

        return None, None, (
            "Sus coordenadas parecen estar en un sistema plano/proyectado "
            "(valores grandes, no son grados decimales validos), pero el Excel "
            "no incluye una columna de zona (ej. 'Zona_UTM') para detectar "
            "automaticamente el EPSG exacto.\n\n"
            "Vaya a la pestaña 'Configuracion' y seleccione manualmente el CRS "
            "de origen correcto (UTM o MAGNA-SIRGAS) en 'CRS de salida', luego "
            "procese de nuevo."
        )

    def _validate_crs_matches_data(self, crs_epsg, all_features):
        if crs_epsg != 4326:
            return None

        bad = [
            f for f in all_features
            if not CoordinateParser.is_valid_geographic_degrees(
                f["point"].x(), f["point"].y()
            )
        ]
        if bad:
            return (
                f"El CRS de salida es geografico (EPSG:4326) pero {len(bad)} de "
                f"{len(all_features)} puntos tienen valores fuera del rango de "
                "grados decimales validos (longitud +-180, latitud +-90).\n\n"
                "Esto indica que sus datos son coordenadas planas/proyectadas "
                "(ej. UTM o MAGNA-SIRGAS), no geograficas. Seleccione manualmente "
                "el CRS de origen correcto (proyectado) en la pestaña "
                "'Configuracion' antes de procesar."
            )
        return None

    def _zoom_to_layer(self, layer_name):
        if not self.iface:
            return
        layers = QgsProject.instance().mapLayersByName(layer_name)
        if not layers:
            return

        extent = None
        for layer in layers:
            ext = layer.extent()
            if ext.isEmpty():
                continue
            if extent is None:
                extent = ext
            else:
                extent.combineExtentWith(ext)

        if extent and not extent.isEmpty():
            canvas = self.iface.mapCanvas()
            canvas.setExtent(extent)
            canvas.refresh()

    def _process_sheet(self, headers, rows, config):
        features = []
        stats = {"decimal": 0, "utm": 0, "zone_hint": None}
        format_map = {
            0: CoordinateFormat.AUTO,
            1: CoordinateFormat.DECIMAL,
            2: CoordinateFormat.UTM,
            3: CoordinateFormat.DMS,
        }
        source_format = format_map.get(config["format"], CoordinateFormat.AUTO)

        x_col = config["x_column"]
        y_col = config["y_column"]
        z_col = config["z_column"]

        exclude_cols = {x_col, y_col}
        if z_col is not None:
            exclude_cols.add(z_col)
        zone_col = CoordinateParser.find_zone_column(headers, exclude_cols)

        for row_idx, row in enumerate(rows):
            try:
                x_val = row[x_col] if x_col < len(row) else None
                y_val = row[y_col] if y_col < len(row) else None
                z_val = row[z_col] if z_col is not None and z_col < len(row) else None

                coord = CoordinateParser.parse_coordinate_pair(
                    x_val, y_val, z_val, source_format
                )

                if coord is None:
                    log_warning(
                        f"Fila {row_idx + 1}: No se pudo parsear coordenada "
                        f"X={x_val}, Y={y_val}"
                    )
                    continue

                attributes = {}
                for i, h in enumerate(headers):
                    if i < len(row) and i != x_col and i != y_col and i != z_col:
                        val = row[i]
                        key = ''.join(c for c in unicodedata.normalize('NFKD', str(h).lower()) if not unicodedata.combining(c)).strip()
                        identifier = any(word in key for word in ('cedula', 'telefono', 'celular', 'documento', 'identificacion'))
                        if val is not None and identifier:
                            attributes[h] = str(int(val)) if isinstance(val, float) and val.is_integer() else str(val)
                        elif val is not None:
                            try:
                                val_float = float(str(val).replace(',', '.'))
                                if val_float == int(val_float):
                                    attributes[h] = int(val_float)
                                else:
                                    attributes[h] = val_float
                            except (ValueError, TypeError):
                                attributes[h] = str(val)
                        else:
                            attributes[h] = None

                x = coord["x"]
                y = coord["y"]

                if coord["type"] == CoordinateFormat.DECIMAL:
                    stats["decimal"] += 1
                    if config["calculate_utm_zone"]:
                        attributes["utm_zone"] = GeometryCalculator.get_utm_zone(x)
                        attributes["utm_epsg"] = utm_epsg_from_lon_lat(x, y)

                    point = QgsPointXY(x, y)
                    geometry = QgsGeometry.fromPointXY(point)

                elif coord["type"] == CoordinateFormat.UTM:
                    stats["utm"] += 1
                    if coord.get("zone"):
                        attributes["utm_zone"] = coord["zone"]
                    elif (stats["zone_hint"] is None and zone_col is not None
                            and zone_col < len(row)):
                        parsed_zone = CoordinateParser.parse_zone_value(row[zone_col])
                        if parsed_zone:
                            stats["zone_hint"] = parsed_zone
                    point = QgsPointXY(x, y)
                    geometry = QgsGeometry.fromPointXY(point)

                else:
                    stats["decimal"] += 1
                    point = QgsPointXY(x, y)
                    geometry = QgsGeometry.fromPointXY(point)

                if config["calculate_centroid"]:
                    attributes["centroid_x"] = point.x()
                    attributes["centroid_y"] = point.y()

                features.append({
                    "attributes": attributes,
                    "geometry": geometry,
                    "point": point,
                })

            except Exception as e:
                log_warning(f"Fila {row_idx + 1}: Error - {str(e)}")
                continue

        if config["calculate_distance"] and len(features) > 1:
            total_distance = 0.0
            for i in range(1, len(features)):
                p1 = features[i - 1]["point"]
                p2 = features[i]["point"]
                dist = CoordinateParser.euclidean_distance(
                    p1.x(), p1.y(), p2.x(), p2.y()
                )
                total_distance += dist
                features[i]["attributes"]["dist_from_prev"] = round(dist, 4)
                features[i]["attributes"]["dist_cumulative"] = round(total_distance, 4)

            features[0]["attributes"]["dist_from_prev"] = 0.0
            features[0]["attributes"]["dist_cumulative"] = 0.0

        if config["calculate_area"] and len(features) >= 3:
            points = [f["point"] for f in features]
            area, perimeter = GeometryCalculator.calculate_polygon_area_perimeter(points)
            for f in features:
                f["attributes"]["polygon_area"] = round(area, 6)
                f["attributes"]["polygon_perimeter"] = round(perimeter, 6)

        return features, stats
