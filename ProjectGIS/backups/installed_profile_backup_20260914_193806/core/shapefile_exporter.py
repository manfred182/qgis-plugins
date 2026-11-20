# -*- coding: utf-8 -*-
"""
Exportador a formato Shapefile (.shp)
"""
import os
from ..utils.compatibility import (
    import_qgs_feature,
    import_qgs_field,
    import_qgs_fields,
    import_qgs_geometry,
    import_qgs_point_xy,
    import_qgs_coordinate_reference_system,
    import_qgs_vector_file_writer,
    import_qgs_wkb_types,
    import_qvariant,
    log_info,
    log_error,
    add_layer_to_project,
)


class ShapefileExporter:

    @staticmethod
    def export(features_data, output_path, crs_epsg=4326,
               layer_name="coordenadas", geometry_type="Point"):
        try:
            if not output_path.lower().endswith('.shp'):
                output_path = os.path.join(output_path, f"{layer_name}.shp")

            fields = ShapefileExporter._create_fields(features_data)

            CRS = import_qgs_coordinate_reference_system()
            crs = CRS(f"EPSG:{crs_epsg}")

            WkbTypes = import_qgs_wkb_types()
            geom_type = WkbTypes.Point if geometry_type == "Point" else \
                        WkbTypes.LineString if geometry_type == "Line" else \
                        WkbTypes.Polygon

            VectorFileWriter = import_qgs_vector_file_writer()
            writer = VectorFileWriter(
                output_path,
                "UTF-8",
                fields,
                geom_type,
                crs,
                "ESRI Shapefile"
            )

            if writer.hasError() != VectorFileWriter.NoError.NoError:
                log_error(f"Error al crear Shapefile: {writer.errorMessage()}")
                del writer
                return False

            Feature = import_qgs_feature()
            for feat_data in features_data:
                feat = Feature()
                feat.setFields(fields)

                for field_name, value in feat_data.get("attributes", {}).items():
                    if field_name in [f.name() for f in fields]:
                        feat.setAttribute(field_name, value)

                geom = feat_data.get("geometry")
                if geom:
                    feat.setGeometry(geom)

                writer.addFeature(feat)

            del writer

            VectorLayer = import_qgs_vector_layer()
            layer = VectorLayer(output_path, layer_name, "ogr")
            if layer.isValid():
                add_layer_to_project(layer, layer_name)
                log_info(f"Shapefile creado exitosamente: {output_path}")
                return True
            else:
                log_error("La capa Shapefile no es valida")
                return False

        except Exception as e:
            log_error(f"Error al exportar Shapefile: {str(e)}")
            return False

    @staticmethod
    def _create_fields(features_data):
        Fields = import_qgs_fields()
        Field = import_qgs_field()
        QVariant = import_qvariant()

        fields = Fields()

        if features_data:
            first_feat = features_data[0]
            attributes = first_feat.get("attributes", {})

            for field_name, value in attributes.items():
                if isinstance(value, int):
                    fields.append(Field(field_name, QVariant.Int))
                elif isinstance(value, float):
                    fields.append(Field(field_name, QVariant.Double))
                elif isinstance(value, bool):
                    fields.append(Field(field_name, QVariant.Bool))
                else:
                    fields.append(Field(field_name, QVariant.String, "", 255))

        if "id" not in [f.name() for f in fields]:
            fields.append(Field("id", QVariant.Int))

        return fields
