"""Guarda el merge en shapefile, materializando los campos de R1/R2."""
import os


def save_consolidated(layer, shapefile_path, omissions=None):
    from qgis.core import QgsVectorFileWriter, QgsVectorLayer, QgsProject
    path = os.path.abspath(shapefile_path)
    if not path.lower().endswith('.shp'):
        path += '.shp'
    base = os.path.splitext(path)[0]
    omission_path = base + '_omisiones.dbf'
    for stem in (base, base + '_omisiones'):
        for extension in ('.shp', '.shx', '.dbf', '.prj', '.cpg', '.qix', '.qml'):
            if os.path.exists(stem + extension):
                raise ValueError('Ya existe {}. Elige otro nombre de salida.'.format(stem + extension))

    def write(source, target):
        writer_target = os.path.splitext(target)[0] + '.shp'
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = 'ESRI Shapefile'
        options.fileEncoding = 'UTF-8'
        options.onlySelectedFeatures = False
        if hasattr(QgsVectorFileWriter, 'writeAsVectorFormatV3'):
            result = QgsVectorFileWriter.writeAsVectorFormatV3(
                source, writer_target, QgsProject.instance().transformContext(), options)
        else:
            result = QgsVectorFileWriter.writeAsVectorFormatV2(
                source, writer_target, QgsProject.instance().transformContext(), options)
        if result[0] != QgsVectorFileWriter.NoError:
            raise RuntimeError('No se pudo guardar {}: {}'.format(target, result))
        saved = QgsVectorLayer(target, source.name(), 'ogr')
        if not saved.isValid() or saved.featureCount() != source.featureCount():
            raise RuntimeError('El archivo guardado no supero la verificacion; se conserva la capa temporal.')
        if len(saved.fields()) != len(source.fields()):
            raise RuntimeError('El shapefile no conservo todos los campos; se mantiene la capa temporal.')
        # DBF limita los nombres a 10 caracteres: conservar los nombres originales
        # como alias, tanto para la interfaz como para el buscador del complemento.
        for index, field in enumerate(source.fields()):
            saved.setFieldAlias(index, field.name())
        if source.renderer():
            saved.setRenderer(source.renderer().clone())
        for key in source.customPropertyKeys():
            saved.setCustomProperty(key, source.customProperty(key))
        return saved

    saved = write(layer, path)
    saved_omissions = write(omissions, omission_path) if omissions is not None and omissions.isValid() else None
    return saved, saved_omissions, path
