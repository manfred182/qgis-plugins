# -*- coding: utf-8 -*-
"""
Exportador a formato CSV
"""
import os
import csv
from ..utils.compatibility import log_info, log_error


class CSVExporter:

    @staticmethod
    def export(features_data, output_path, include_geometry=True):
        try:
            if not output_path.lower().endswith('.csv'):
                output_path = os.path.join(output_path, "coordenadas.csv")

            all_fieldnames = set()

            for feat_data in features_data:
                attrs = feat_data.get("attributes", {})
                all_fieldnames.update(attrs.keys())

                geom = feat_data.get("geometry")
                if geom and include_geometry:
                    if hasattr(geom, 'asPoint'):
                        all_fieldnames.update(["coord_x", "coord_y"])
                    if hasattr(geom, 'asPolyline'):
                        all_fieldnames.add("geometry_wkt")
                    if hasattr(geom, 'asPolygon'):
                        all_fieldnames.update(["area", "perimeter"])

            if "id" in all_fieldnames:
                all_fieldnames.remove("id")
            fieldnames = ["id"] + sorted(all_fieldnames)

            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for idx, feat_data in enumerate(features_data, 1):
                    row = {"id": idx}

                    for k, v in feat_data.get("attributes", {}).items():
                        if k in fieldnames:
                            row[k] = v

                    geom = feat_data.get("geometry")
                    if geom and include_geometry:
                        if hasattr(geom, 'asPoint'):
                            pt = geom.asPoint()
                            row["coord_x"] = pt.x()
                            row["coord_y"] = pt.y()
                        elif hasattr(geom, 'asWkt'):
                            row["geometry_wkt"] = geom.asWkt()

                    writer.writerow(row)

            log_info(f"CSV creado exitosamente: {output_path}")
            return True

        except Exception as e:
            log_error(f"Error al exportar CSV: {str(e)}")
            return False
