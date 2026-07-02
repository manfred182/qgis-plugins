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
