# Manual de usuario de GeoMigrator Pro

**Versión del complemento:** 1.0  
**QGIS compatible:** 3.22 a 3.99  
**Autor:** Jose Orlando Castillo Ospina  
**Contacto:** nanometal182@gmail.com

GeoMigrator Pro facilita la carga de información geográfica y alfanumérica hacia PostgreSQL/PostGIS desde QGIS. Está orientado a proyectos SIG, gestión territorial y catastro colombiano, con soporte para File Geodatabase, archivos vectoriales, Excel, CSV y transferencias XTF/INTERLIS asociadas con LADM-COL.

> GeoMigrator Pro realiza procesos de migración y carga. No reemplaza los controles jurídicos, semánticos, topológicos o de calidad definidos por el IGAC, la autoridad catastral, el gestor catastral o la organización responsable de los datos.

## 1. Funciones principales

- Importación total o selectiva de capas desde una File Geodatabase (`.gdb`).
- Importación de SHP, GeoJSON, KML, KMZ, GPX, GML y MapInfo TAB.
- Importación de tablas de Excel (`.xlsx` y `.xls`).
- Importación de CSV como tabla o como capa de puntos mediante columnas X/Y.
- Carga XTF/ITF mediante ili2pg 4.4.3 y modelos IGAC LADM-COL incluidos.
- Procesamiento recursivo por lotes de carpetas con SHP, GDB, GeoJSON, JSON, KML y CSV.
- Creación asistida de bases de datos, esquemas y extensiones PostGIS.
- Reparación opcional de geometrías inválidas en cargas GDB.
- Reproyección opcional de archivos vectoriales.
- Registro de progreso, errores y comandos ejecutados, ocultando la contraseña en el log.
- Carga automática de las tablas espaciales resultantes en el proyecto QGIS.

## 2. Requisitos

### 2.1 Software

- QGIS 3.22 o superior, dentro del rango indicado en los metadatos del complemento.
- PostgreSQL con PostGIS.
- GDAL/OGR con `ogr2ogr` y `ogrinfo` disponibles para QGIS.
- Java 8 o superior para XTF/INTERLIS.
- Acceso de red hacia PostgreSQL y, si hiciera falta descargar ili2pg o modelos base, hacia `interlis.ch` y los repositorios de modelos INTERLIS.

En instalaciones oficiales de QGIS para Windows, GDAL normalmente está incluido. Si el panel de log muestra que no encuentra `ogr2ogr` u `ogrinfo`, revise la instalación o el entorno PATH desde el cual se inicia QGIS.

### 2.2 Permisos de PostgreSQL

Para cargar datos en una base existente, el usuario necesita como mínimo:

- `CONNECT` sobre la base de datos.
- `USAGE` y `CREATE` sobre el esquema de destino, según el flujo utilizado.
- Permisos para crear, reemplazar e insertar en las tablas de destino.

Para que el complemento cree automáticamente una base de datos y active extensiones, el usuario requiere privilegios adicionales para:

- Crear bases de datos.
- Ejecutar `CREATE EXTENSION postgis`.
- Ejecutar `CREATE EXTENSION "uuid-ossp"`.
- Crear esquemas.

En ambientes productivos se recomienda que el administrador cree previamente la base, las extensiones y los esquemas, y entregue al operador únicamente los privilegios necesarios para cargar datos.

## 3. Instalación

1. Cierre cualquier proceso anterior de instalación del complemento.
2. Abra QGIS.
3. Vaya a **Complementos > Administrar e instalar complementos**.
4. Abra **Instalar a partir de ZIP**.
5. Seleccione `GeoMigratorPro.zip`.
6. Acepte el aviso de instalación si QGIS lo presenta.
7. Active **GeoMigrator Pro** en la lista de complementos instalados.
8. Abra el complemento desde su acción en QGIS.
9. Revise el **Log de proceso**. Al iniciar debe informar si detectó GDAL/OGR y Java.

## 4. Recorrido por la interfaz

La ventana principal contiene las pestañas:

- **GDB:** carga de File Geodatabase.
- **SHP/GeoJSON/KML:** carga individual de formatos vectoriales compatibles con OGR.
- **Excel:** carga de hojas o tablas reconocidas por el controlador de GDAL.
- **CSV:** carga alfanumérica o creación de puntos mediante coordenadas.
- **XTF:** importación INTERLIS para flujos IGAC LADM-COL.
- **Lote:** carga recursiva de múltiples fuentes.
- **Acerca de:** versión, autor, licencia y estándares utilizados.

En la parte inferior se encuentran el progreso, el botón **Cancelar**, el log, **Limpiar log** y **Exportar log .txt**. Exporte el log cuando necesite conservar evidencia de una migración o solicitar soporte.

## 5. Configurar PostgreSQL/PostGIS

Cada flujo tiene un bloque de conexión con estos campos:

- **Host:** nombre DNS o dirección del servidor, por ejemplo `localhost`.
- **Puerto:** normalmente `5432`.
- **Base de datos:** base de destino.
- **Usuario:** rol de PostgreSQL.
- **Contraseña:** contraseña del rol.
- **Schema:** esquema de destino; por defecto `public` y para XTF normalmente `ladm_col`.
- **Usar SSL:** solicita `sslmode=require` al cliente PostgreSQL.

### 5.1 Probar la conexión

1. Diligencie los campos.
2. Pulse **Probar conexión**.
3. Confirme el mensaje de conexión correcta.
4. Si falla, revise host, puerto, base, usuario, contraseña, firewall, `pg_hba.conf`, SSL y disponibilidad del servidor.

### 5.2 Crear una base de datos

1. Ingrese host, puerto, usuario y contraseña de un rol autorizado.
2. Escriba el nombre deseado en **Base de datos**.
3. Pulse **Crear BD en PostgreSQL...**.
4. Confirme el nombre.
5. El complemento intentará crear la base en UTF-8 y activar PostGIS y `uuid-ossp`.

Los nombres de bases creadas por el complemento se convierten a minúsculas y se restringen a letras, números y guion bajo. Si comienzan por un número, reciben el prefijo `db_`.

### 5.3 Perfiles de conexión

- **Guardar:** almacena la conexión bajo un nombre.
- **Cargar:** recupera un perfil guardado.
- **Eliminar:** borra el perfil seleccionado.

Los perfiles se guardan localmente en `profiles.json` dentro del directorio instalado del complemento. La contraseña está ofuscada con XOR y Base64, no protegida por cifrado fuerte. No use esta función para credenciales de alto privilegio en computadores compartidos. Prefiera un usuario exclusivo de carga, privilegios mínimos, SSL y controles de acceso del sistema operativo.

## 6. Flujo recomendado antes de cualquier migración

1. Conserve una copia del origen y una copia de seguridad de la base de destino.
2. Identifique formato, número de capas, volumen, geometrías y sistema de referencia.
3. Defina la base, esquema y convención de nombres.
4. Verifique que no exista una tabla que deba preservarse: varios flujos usan sobrescritura.
5. Pruebe la conexión.
6. Realice primero una carga piloto en una base o esquema de pruebas.
7. Observe el log hasta que termine el proceso.
8. Compare conteos, atributos, geometrías, extensión espacial y CRS entre origen y destino.
9. Ejecute controles topológicos, semánticos y de negocio.
10. Solo después promueva o use los datos en producción.

## 7. Importar una File Geodatabase

### 7.1 Procedimiento

1. Abra **GDB**.
2. Pulse **Seleccionar GDB...** y elija la carpeta terminada en `.gdb`.
3. Pulse **Listar capas**.
4. Seleccione una o varias capas. Si no selecciona ninguna, el complemento intenta importar todas.
5. Configure:
   - **Sobreescribir tablas existentes:** reemplaza tablas con el mismo nombre.
   - **Reparar geometrías inválidas:** aplica la opción `-makevalid` de OGR.
   - **Cargar capas en QGIS al terminar:** agrega las tablas espaciales al proyecto.
6. Configure y pruebe PostgreSQL.
7. Pulse **IMPORTAR GDB**.
8. Revise cada paso en el log.

### 7.2 Comportamiento

- Las geometrías se promueven a tipos múltiples cuando corresponde.
- La columna geométrica se denomina `geom`.
- Se utiliza carga masiva de PostgreSQL mediante `PG_USE_COPY=YES`.
- Los nombres se normalizan a minúsculas, sin tildes ni caracteres especiales, con guion bajo.
- El proceso continúa ante algunos errores de entidades mediante `-skipfailures`; por eso es indispensable comparar los conteos finales.

### 7.3 Aplicación catastral

Este flujo es útil para migrar capas como predios, terrenos, construcciones, unidades de construcción, sectores, veredas, zonas homogéneas, cartografía base, linderos, puntos de levantamiento y capas administrativas. Use esquemas separados para datos recibidos, datos depurados y datos oficiales, por ejemplo:

- `staging`: copia fiel de recepción.
- `calidad`: datos en revisión y resultados de controles.
- `catastro`: información aprobada para explotación institucional.

## 8. Importar SHP, GeoJSON, KML, GPX, GML, KMZ o TAB

1. Abra **SHP/GeoJSON/KML**.
2. Pulse **Seleccionar...**.
3. Escriba el nombre de la tabla o déjelo vacío para usar el nombre del archivo.
4. En **EPSG destino**, indique solo el número, por ejemplo `9377`, o déjelo vacío para no reproyectar.
5. Elija si desea cargar el resultado en QGIS.
6. Configure PostgreSQL.
7. Pulse **IMPORTAR ARCHIVO VECTORIAL**.

La importación usa sobrescritura, `PROMOTE_TO_MULTI`, columna `geom`, carga COPY y omisión de entidades que produzcan ciertos errores.

### Precaución con el CRS

El campo **EPSG destino** reproyecta con `-t_srs`; no asigna simplemente un CRS desconocido. El origen debe tener su CRS correctamente definido. Si el archivo carece de CRS o está mal etiquetado, corríjalo antes de migrar. Para cartografía catastral colombiana actual que deba quedar en Origen Nacional, valide con la especificación del proyecto si corresponde usar EPSG:9377.

## 9. Importar Excel

1. Abra **Excel**.
2. Seleccione un archivo `.xlsx` o `.xls`.
3. Escriba un nombre de tabla de destino.
4. Configure PostgreSQL.
5. Pulse **IMPORTAR EXCEL**.

La carga crea una tabla no espacial salvo que el controlador y la estructura del origen indiquen otra cosa. La disponibilidad de hojas, rangos y tipos depende del controlador GDAL/OGR instalado. Antes de importar:

- Use una fila única de encabezados.
- Evite celdas combinadas y títulos decorativos.
- Mantenga un tipo de dato consistente por columna.
- Conserve identificadores catastrales como texto para no perder ceros iniciales.
- Normalice fechas y valores nulos.
- Evite fórmulas cuyo resultado no esté guardado en el archivo.

Después de la carga, valide nombres de columnas, tipos PostgreSQL, número de registros, nulos y duplicados.

## 10. Importar CSV

1. Abra **CSV**.
2. Seleccione `.csv`, `.tsv` o `.txt`.
3. Escriba el nombre de tabla.
4. Indique el delimitador o déjelo vacío para autodetección. Puede usar coma, punto y coma, tabulación o barra vertical.
5. Para crear puntos, indique:
   - **Longitud/X:** columna de coordenada horizontal.
   - **Latitud/Y:** columna de coordenada vertical.
   - **EPSG del CSV:** CRS de esas coordenadas.
6. Si no quiere geometría, deje vacíos X e Y.
7. Configure PostgreSQL y pulse **IMPORTAR CSV**.

Verifique que el separador decimal no entre en conflicto con el delimitador. X e Y deben ser numéricos, pertenecer al mismo CRS y no estar intercambiados. En coordenadas geográficas, X suele ser longitud e Y latitud; en coordenadas proyectadas, X es Este e Y Norte.

Usos frecuentes: puntos de control, direcciones, nomenclatura, visitas de campo, levantamientos GNSS, inventarios, avalúos, propietarios o interesados, trámites y resultados de calidad.

## 11. Importar XTF/INTERLIS para LADM-COL

### 11.1 Qué hace el flujo

El complemento:

1. Verifica Java e ili2pg.
2. Detecta modelos declarados en el encabezado y las canastas del XTF.
3. Prioriza los modelos IGAC incluidos en `models/igac_ladm_col_v1_0_1` y usa repositorios remotos como respaldo.
4. Verifica o crea la base y el esquema.
5. Intenta registrar EPSG:9377 si no existe en PostGIS.
6. Activa `uuid-ossp` cuando el usuario tiene permisos.
7. Ejecuta `schemaimport` para crear el modelo relacional.
8. Ejecuta `import` para cargar los objetos del XTF.

### 11.2 Procedimiento

1. Abra **XTF**.
2. Compruebe en pantalla que ili2pg está disponible. La distribución incluye ili2pg 4.4.3; si falta, el complemento puede intentar descargarlo.
3. Seleccione el archivo `.xtf`, `.itf` o `.xml` correspondiente.
4. Configure PostgreSQL.
5. Use normalmente el esquema `ladm_col`, salvo que su arquitectura disponga otro.
6. Pulse **CARGAR XTF → PostgreSQL (IGAC - LADM-COL)**.
7. No cierre QGIS mientras se ejecutan `schemaimport` e `import`.
8. Revise el resultado en el log.

### 11.3 Controles posteriores obligatorios

Una importación técnicamente exitosa no garantiza conformidad catastral. Compruebe al menos:

- Modelo y versión declarados por el XTF.
- Número de canastas y objetos por clase.
- Identificadores `TID`, dominios, referencias y relaciones.
- Integridad de asociaciones entre predios, terrenos, construcciones, unidades, interesados, derechos, restricciones y responsabilidades cuando apliquen al modelo.
- Geometrías vacías, inválidas, duplicadas o fuera del área de trabajo.
- Linderos, superposiciones, huecos y continuidad topológica.
- CRS y extensión espacial en EPSG:9377.
- Catálogos, dominios y valores obligatorios.
- Errores reportados por ili2pg.

Use únicamente modelos y versiones exigidos por la autoridad o por el contrato del proyecto. El complemento incluye modelos concretos y no garantiza compatibilidad automática con cualquier revisión futura de LADM-COL.

## 12. Procesamiento por lotes

1. Abra **Lote**.
2. Seleccione una carpeta raíz.
3. Marque los formatos: SHP, GDB, GeoJSON/JSON, KML y/o CSV.
4. Decida si cargará las capas en QGIS al terminar.
5. Configure PostgreSQL.
6. Pulse **PROCESAR CARPETA EN LOTE**.

La búsqueda es recursiva. Cada capa GDB se convierte en un comando independiente; los demás archivos generan normalmente una tabla por archivo. Las tablas existentes se sobrescriben.

### Riesgo de colisiones

Dos archivos con el mismo nombre ubicados en carpetas diferentes pueden producir el mismo nombre de tabla y sobrescribirse. Antes de usar lote, asegure nombres únicos o procese por carpetas y esquemas separados. Los CSV del lote se cargan sin la configuración X/Y disponible en la pestaña individual.

## 13. Nombres de tablas

El complemento normaliza los nombres:

- Convierte a minúsculas.
- Elimina tildes.
- Convierte espacios y guiones en `_`.
- Elimina caracteres distintos de letras, números y `_`.
- Reduce guiones bajos repetidos.
- Agrega `t_` si el nombre comienza por un número.

Ejemplo: `Construcción 01-A` se convierte en `construccion_01_a`.

Revise previamente posibles colisiones, por ejemplo `Área-Rural` y `Area Rural`, que podrían terminar con el mismo nombre normalizado.

## 14. Seguimiento, cancelación y logs

- La barra muestra pasos ejecutados frente al total.
- **Cancelar** detiene el proceso activo; una tabla parcialmente escrita puede permanecer en PostgreSQL.
- El proceso por cola continúa con el siguiente elemento después de ciertos errores y presenta un resumen al final.
- **Exportar log .txt** guarda evidencia útil para auditoría y soporte.
- La contraseña se reemplaza por `****` en el comando mostrado por el log.

Después de cancelar o recibir errores, inspeccione la base antes de repetir la carga. Si la siguiente ejecución usa sobrescritura, confirme que no eliminará una tabla válida.

## 15. Carga de resultados en QGIS

Cuando la opción está activa, el complemento intenta agregar las tablas usando el proveedor PostgreSQL y una columna geométrica llamada `geom`. Las tablas alfanuméricas o las geometrías con otro nombre pueden no cargarse automáticamente aunque sí existan correctamente en PostgreSQL.

Si una tabla no aparece:

1. Abra el panel **Navegador** de QGIS.
2. Cree o actualice la conexión PostgreSQL.
3. Expanda el esquema.
4. Arrastre manualmente la tabla al mapa.
5. Compruebe geometría, clave primaria y CRS.

## 16. Aplicaciones en catastro

GeoMigrator Pro puede apoyar:

- Recepción y centralización de insumos de actualización catastral.
- Migración de cartografía predial y capas temáticas a PostGIS.
- Consolidación de levantamientos de campo.
- Preparación de esquemas de staging para control de calidad.
- Carga de entregas XTF basadas en LADM-COL.
- Integración de tablas de avalúos, visitas, trámites y fuentes externas.
- Comparación temporal de versiones de información territorial.
- Publicación posterior mediante servicios OGC o plataformas corporativas, fuera del alcance directo del complemento.

### Flujo catastral sugerido

1. **Recepción:** conservar el archivo original y su trazabilidad.
2. **Staging:** importar sin alterar el original.
3. **Perfilamiento:** revisar campos, dominios, conteos, CRS y extensión.
4. **Calidad:** ejecutar reglas geométricas, topológicas, semánticas y de negocio.
5. **Corrección:** documentar cambios y responsables.
6. **Validación:** repetir controles y generar evidencias.
7. **Integración:** mover o transformar datos hacia el modelo institucional.
8. **Publicación:** exponer únicamente datos autorizados y aplicar protección de datos personales.

## 17. Otros usos SIG

El complemento también sirve para:

- Ordenamiento territorial y POT.
- Gestión ambiental, cuencas, coberturas y áreas protegidas.
- Redes de servicios públicos e infraestructura.
- Inventarios viales y equipamientos.
- Gestión del riesgo y atención de emergencias.
- Agricultura, suelos y planificación rural.
- Monitoreo de proyectos y obras.
- Consolidación de datos abiertos y observaciones de campo.
- Migración de archivos departamentales a una base SIG corporativa.

Para estos casos seleccione el CRS, esquema, nombres y reglas de calidad apropiados para cada organización; no use automáticamente `ladm_col` o EPSG:9377 si el proyecto requiere otros estándares.

## 18. Control de calidad posterior

Como mínimo, compare:

- Conteo de capas y tablas.
- Conteo de registros por tabla.
- Tipos de geometría.
- CRS/SRID.
- Extensión espacial.
- Número de geometrías nulas y vacías.
- Geometrías válidas e inválidas.
- Valores nulos en campos obligatorios.
- Identificadores únicos y duplicados.
- Longitud, precisión y tipo de los atributos.
- Relaciones y claves foráneas.
- Dominios y catálogos.
- Superposiciones, huecos, desconexiones y duplicados geométricos.

Ejemplos de consultas PostGIS:

```sql
-- Conteo de registros
SELECT count(*) FROM catastro.predios;

-- SRID y tipo geométrico
SELECT ST_SRID(geom), GeometryType(geom), count(*)
FROM catastro.predios
WHERE geom IS NOT NULL
GROUP BY ST_SRID(geom), GeometryType(geom);

-- Geometrías inválidas
SELECT id, ST_IsValidReason(geom)
FROM catastro.predios
WHERE geom IS NOT NULL AND NOT ST_IsValid(geom);

-- Geometrías vacías
SELECT count(*)
FROM catastro.predios
WHERE geom IS NULL OR ST_IsEmpty(geom);

-- Identificadores duplicados
SELECT numero_predial, count(*)
FROM catastro.predios
GROUP BY numero_predial
HAVING count(*) > 1;
```

Adapte nombres de esquema, tabla, geometría e identificador a su modelo real.

## 19. Solución de problemas

### `ogr2ogr` u `ogrinfo` no encontrado

- Compruebe que QGIS/GDAL esté instalado correctamente.
- Inicie QGIS desde un entorno que incluya GDAL en PATH.
- En Windows, repare QGIS u OSGeo4W si faltan los ejecutables.

### Conexión rechazada

- Confirme servidor, puerto, usuario y contraseña.
- Revise que PostgreSQL esté activo y acepte conexiones remotas.
- Verifique firewall, DNS y `pg_hba.conf`.
- Active SSL si el servidor lo exige.

### No se puede crear la base, extensión o esquema

- El usuario no tiene privilegios suficientes.
- Solicite al administrador que prepare la base y otorgue permisos mínimos.
- No use un superusuario de forma cotidiana solo para evitar este control.

### Una capa no se carga en QGIS

- Compruebe que la tabla existe.
- Verifique que la geometría se llame `geom`.
- Revise geometría, SRID y clave primaria.
- Cárguela manualmente desde el Navegador.

### Faltan entidades después de migrar

El complemento usa `-skipfailures` en varios flujos. Revise el log, compare conteos e identifique registros inválidos o incompatibles con el tipo de destino.

### Error en Excel

- Simplifique encabezados y estructura.
- Guarde nuevamente como `.xlsx`.
- Verifique que el controlador GDAL reconozca el archivo.
- Como alternativa, exporte la hoja a CSV y use la pestaña CSV.

### Error en XTF

- Confirme Java.
- Confirme versión y validez del XTF.
- Revise modelos declarados y modelos incluidos.
- Verifique acceso a repositorios remotos si falta un modelo base.
- Revise privilegios para extensiones, esquema y tablas.
- Exporte el log completo para diagnóstico.

### Caracteres extraños

Los procesos solicitan texto UTF-8, pero la codificación real del origen puede diferir. Convierta o declare correctamente la codificación del archivo antes de importar.

## 20. Seguridad y protección de información

- Use cuentas de PostgreSQL con privilegios mínimos.
- Active SSL cuando el servidor sea remoto.
- No comparta perfiles, `profiles.json`, logs ni capturas con credenciales o datos sensibles.
- Restrinja el acceso a información de propietarios, interesados, documentos, avalúos y trámites según las normas aplicables.
- Mantenga copias de seguridad y registros de auditoría.
- No publique capas catastrales o personales sin autorización.
- Verifique el origen e integridad de archivos XTF, GDB y otros insumos antes de procesarlos.
- Mantenga QGIS, PostgreSQL, PostGIS, GDAL, Java y el complemento actualizados.

## 21. Limitaciones conocidas

- Es una herramienta de migración, no un validador integral de calidad catastral.
- No garantiza conformidad automática con todas las versiones futuras de LADM-COL.
- La reparación `-makevalid` puede modificar geometrías; compare resultados.
- `-skipfailures` puede omitir registros problemáticos.
- La importación individual de vectoriales, Excel, CSV y los lotes sobrescribe tablas con el mismo nombre.
- En lote pueden existir colisiones de nombres entre carpetas.
- La carga automática en QGIS espera la columna `geom`.
- Los perfiles no usan cifrado fuerte.
- La creación automática de infraestructura depende de privilegios elevados.
- La experiencia con Excel depende de los controladores GDAL disponibles.

## 22. Lista de aceptación de una migración

- [ ] El archivo original fue preservado.
- [ ] Se documentaron fuente, fecha, responsable y versión.
- [ ] La conexión y el esquema de destino son correctos.
- [ ] El proceso terminó sin errores no revisados.
- [ ] Se exportó y archivó el log.
- [ ] Los conteos coinciden o las diferencias están justificadas.
- [ ] CRS, extensión y tipos geométricos son correctos.
- [ ] Se revisaron geometrías inválidas y vacías.
- [ ] Se revisaron identificadores, nulos, duplicados y dominios.
- [ ] Se validaron relaciones y reglas de negocio.
- [ ] En catastro, se ejecutaron controles topológicos y LADM-COL aplicables.
- [ ] Los datos sensibles tienen controles de acceso.
- [ ] Existe copia de seguridad o procedimiento de reversión.
- [ ] El responsable funcional aprobó el resultado.

## 23. Soporte

Al reportar un problema incluya:

- Versión de QGIS y sistema operativo.
- Versión de GeoMigrator Pro.
- Tipo de fuente y tamaño aproximado.
- Versión de PostgreSQL/PostGIS.
- Descripción de lo esperado y lo ocurrido.
- Log exportado, después de revisar que no contenga información sensible.
- Una muestra anonimizada cuando sea posible.

- Repositorio: https://github.com/manfred182/qgis-plugins
- Incidencias: https://github.com/manfred182/qgis-plugins/issues
- Correo: nanometal182@gmail.com