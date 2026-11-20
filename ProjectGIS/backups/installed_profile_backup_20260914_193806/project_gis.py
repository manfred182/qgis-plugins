# -*- coding: utf-8 -*-
"""
ProjectGIS - Plugin principal para QGIS
Convierte tablas de coordenadas Excel a Shapefile/GeoPackage
"""
import os
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
from .utils.crs_utils import CRS_PRESETS, get_epsg_from_name, utm_epsg_from_lon_lat
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

            for sheet_name in sheets:
                headers, rows = reader.read_sheet(sheet_name)
                features = self._process_sheet(
                    headers, rows, config
                )
                all_features.extend(features)

            reader.close()

            if not all_features:
                self.dialog.set_error("No se pudieron procesar las coordenadas.")
                return

            output_dir = config["output_dir"]
            layer_name = config["layer_name"]
            crs_name = config["crs"]
            crs_epsg = get_epsg_from_name(crs_name)

            exported = []
            if config["export_shp"]:
                shp_path = os.path.join(output_dir, f"{layer_name}.shp")
                if ShapefileExporter.export(
                    all_features, shp_path, crs_epsg, layer_name
                ):
                    exported.append("Shapefile")

            if config["export_gpkg"]:
                gpkg_path = os.path.join(output_dir, f"{layer_name}.gpkg")
                if GeoPackageExporter.export(
                    all_features, gpkg_path, crs_epsg, layer_name
                ):
                    exported.append("GeoPackage")

            if config["export_csv"]:
                csv_path = os.path.join(output_dir, f"{layer_name}.csv")
                if CSVExporter.export(all_features, csv_path):
                    exported.append("CSV")

            self.dialog.progress_bar.setRange(0, 100)
            self.dialog.progress_bar.setValue(100)

            if exported:
                self.dialog.set_success(
                    f"Procesamiento completado exitosamente!\n\n"
                    f"Archivos generados:\n"
                    f"- {len(all_features)} registros procesados\n"
                    f"- Formatos: {', '.join(exported)}\n"
                    f"- Carpeta: {output_dir}"
                )
            else:
                self.dialog.set_error("No se pudieron generar los archivos de salida.")

        except Exception as e:
            log_error(f"Error en procesamiento: {str(e)}")
            self.dialog.set_error(f"Error durante el procesamiento:\n{str(e)}")

    def _process_sheet(self, headers, rows, config):
        features = []
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
                        if val is not None:
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
                    if config["calculate_utm_zone"]:
                        attributes["utm_zone"] = GeometryCalculator.get_utm_zone(x)
                        attributes["utm_epsg"] = utm_epsg_from_lon_lat(x, y)

                    point = QgsPointXY(x, y)
                    geometry = QgsGeometry.fromPointXY(point)

                elif coord["type"] == CoordinateFormat.UTM:
                    if coord.get("zone"):
                        attributes["utm_zone"] = coord["zone"]
                    point = QgsPointXY(x, y)
                    geometry = QgsGeometry.fromPointXY(point)

                else:
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

        return features
