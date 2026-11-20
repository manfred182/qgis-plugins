# GeoMigrator Pro v1.0

Plugin QGIS profesional para migracion de datos geoespaciales hacia PostgreSQL/PostGIS.
Disenado para el contexto catastral colombiano con soporte al estandar IGAC - LADM-COL.

## Formatos soportados
GDB, SHP, GeoJSON, KML, GPX, GML, Excel, CSV y XTF/INTERLIS (IGAC LADM-COL).

## Requisitos
- QGIS >= 3.22
- GDAL/OGR (`ogr2ogr` y `ogrinfo` en el PATH)
- PostgreSQL + PostGIS
- Java 8+ para importacion XTF/INTERLIS
- Modelos IGAC LADM-COL incluidos en `models/igac_ladm_col_v1_0_1`

## Instalacion
1. Abre QGIS.
2. Ve a `Complementos > Administrar e instalar complementos > Instalar desde ZIP`.
3. Selecciona `GeoMigratorPro.zip`.
4. Activa el plugin.

## Empaquetado para publicacion
El ZIP de distribucion debe contener una unica carpeta superior llamada `GeoMigratorPro`. Los archivos compilados y caches de Python (`__pycache__`, `*.pyc`, `*.pyo`) no deben incluirse en el repositorio ni en el ZIP.

## Soporte
- Repositorio: https://github.com/manfred182/qgis-plugins
- Incidencias: https://github.com/manfred182/qgis-plugins/issues
- Contacto: nanometal182@gmail.com

## Manual de usuario
Consulta la guia completa de instalacion, migracion, flujos catastrales, control de calidad y solucion de problemas en [MANUAL_USUARIO.md](MANUAL_USUARIO.md).
