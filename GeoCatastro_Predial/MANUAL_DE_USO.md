# Manual de uso — Herramienta de Consulta Catastral Local

**Versión del complemento:** 1.1.0  
**Compatible con:** QGIS 3.x  
**Autor:** Jose Orlando Castillo Ospina  
**Contacto:** nanometal182@gmail.com

## 1. Objetivo

La Herramienta de Consulta Catastral Local permite buscar, revisar, seleccionar, localizar en el mapa y exportar información predial del modelo catastral multipropósito IGAC. Trabaja sobre capas vectoriales cargadas en QGIS y reconoce campos propios de la capa y campos incorporados mediante joins de Registro 1 (R1) y Registro 2 (R2).

## 2. Requisitos

- QGIS 3.x.
- Una capa vectorial catastral cargada en el proyecto.
- Los joins R1 y R2 deben estar configurados en la capa cuando se necesiten datos de propietarios, avalúos, matrículas, zonas, estrato, uso u otros atributos asociados.
- Para exportar a Excel, el entorno Python de QGIS debe tener disponible `openpyxl`.
- La capa debe tener geometría válida para usar selección y zoom en el mapa.

## 3. Instalación

1. Abra QGIS.
2. Vaya a **Complementos > Administrar e instalar complementos**.
3. Si el complemento ya está publicado, búsquelo como **Herramienta de Consulta Catastral Local** e instálelo.
4. Para instalarlo desde un archivo, abra **Instalar a partir de ZIP**, seleccione el ZIP del complemento y confirme la instalación.
5. Verifique que el complemento esté activado.

El acceso queda disponible en:

- el botón **Consultas Catastrales** de la barra de herramientas; y
- el menú **Vector > Consultas Catastrales**.

## 4. Preparación de la capa

1. Cargue en QGIS la capa de predios que desea consultar.
2. Si la información R1 o R2 está en tablas separadas, configure los joins desde **Propiedades de la capa > Uniones (Joins)**.
3. Compruebe que las llaves utilizadas para relacionar las tablas correspondan entre sí.
4. Abra la herramienta y seleccione la capa en el panel **Capa activa**.
5. Revise el resumen de campos detectados. Los campos faltantes aparecen como **No encontrados**.
6. Si acaba de agregar o modificar capas, pulse **↺** para actualizar la lista.

La herramienta detecta automáticamente los prefijos que QGIS agrega a los campos unidos. No es necesario renombrar manualmente los campos R1 o R2 si sus nombres semánticos pueden reconocerse.

## 5. Guía rápida: primera consulta

1. Abra **Consultas Catastrales**.
2. Elija una capa vectorial en **Capa activa**.
3. Escriba un código predial, documento, nombre, dirección o matrícula en la búsqueda rápida.
4. Pulse **Buscar**.
5. Seleccione una fila para ver la información detallada del predio.
6. Pulse **Zoom** para localizar los resultados, **Excel** para exportarlos o **PDF** para crear la ficha cartográfica del predio actual.

## 6. Elementos de la interfaz

### 6.1 Capa activa

Permite escoger una de las capas vectoriales cargadas en el proyecto. Debajo del selector se muestran:

- cantidad de registros;
- cantidad de campos;
- tipo de geometría; y
- sistema de referencia de coordenadas (CRS).

### 6.2 Botón Campos

El botón **Campos** abre un diagnóstico con todos los atributos disponibles y sus tipos. Los campos relacionados con datos catastrales R1/R2 detectados se resaltan en verde.

Use este diagnóstico cuando la herramienta indique que falta un campo o cuando un filtro no produzca los resultados esperados.

### 6.3 Búsqueda rápida

La búsqueda rápida busca el texto introducido en todos los campos de texto y numéricos de la capa. Es útil para localizar rápidamente:

- código predial;
- código anterior;
- nombre del propietario;
- número de documento;
- dirección;
- matrícula inmobiliaria; o
- cualquier otro valor presente en la tabla de atributos.

Las diez búsquedas más recientes quedan disponibles temporalmente en el selector con el icono de reloj.

### 6.4 Filtros avanzados

Los filtros avanzados se agrupan de la siguiente manera:

| Grupo | Campos principales |
|---|---|
| Identificación predial | Número predial, código anterior, código de vereda o manzana |
| Propietario | Nombre, tipo y número de documento, dirección, destino económico, avalúo y vigencia |
| Áreas | Área de terreno y área construida (m²), área geográfica y perímetro (m), y sus equivalentes calculados en hectáreas/kilómetros |
| Información Jurídica | Matrícula inmobiliaria, zonas física y económica, estrato, uso, pisos, baños, locales y puntaje |

Para realizar una consulta avanzada:

1. Complete uno o varios filtros.
2. Pulse **Buscar**.
3. Cuando use varios filtros, la herramienta exige que se cumplan todos simultáneamente.
4. Revise el mensaje de estado y la lista de campos no encontrados.

Si se pulsa **Buscar** sin diligenciar filtros, la herramienta intentará mostrar todos los registros de la capa. En capas grandes esta operación puede tardar y consumir más memoria.

## 7. Resultados y detalle del predio

Los resultados aparecen en una tabla y también se abren en una ventana flotante titulada **Reporte Predial**.

- Al seleccionar una fila, el formulario avanzado muestra el detalle del predio.
- **Anterior** y **Siguiente** permiten recorrer los resultados uno por uno.
- Al navegar, QGIS acerca el mapa al predio correspondiente.
- Las columnas técnicas de log o identificadores globales se omiten de la vista para facilitar la lectura.
- Los valores de área, perímetro y avalúo se presentan con formato legible.

## 8. Seleccionar y localizar en el mapa

### Seleccionar

Pulse **Seleccionar** para seleccionar en la capa todos los registros obtenidos por la consulta. La capa consultada pasa a ser la capa activa de QGIS.

### Zoom

Pulse **Zoom** para seleccionar los resultados y ajustar el mapa a su extensión. Esta función opera con capas de puntos, líneas o polígonos.

## 9. Ventana Reporte Predial

La ventana flotante permite trabajar con los resultados sin perder de vista el mapa. Incluye:

- **Filtrar en tabla:** oculta en tiempo real las filas que no contienen el texto buscado.
- **Columnas:** permite mostrar u ocultar atributos.
- **Copiar selección:** copia las filas seleccionadas, junto con sus encabezados, al portapapeles.
- **Exportar Excel:** exporta solamente las filas visibles y las columnas visibles de esta ventana.
- **Menú contextual:** al hacer clic derecho sobre la tabla se puede copiar la selección o exportar.

Ocultar filas con el filtro de la tabla no cambia la selección espacial original; solo modifica la vista y el contenido exportado desde la ventana flotante.

## 10. Exportación a Excel

Hay dos formas de exportar:

### Exportación general

El botón **Excel** o **Exportar Excel** de la ventana principal guarda todos los resultados de la consulta y todas las columnas visibles definidas por la herramienta.

### Exportación desde Reporte Predial

El botón de exportación de la ventana flotante guarda:

- las filas que permanecen visibles después de filtrar; y
- las columnas que permanecen activadas en el menú **Columnas**.

El archivo generado incluye título, fecha, nombre de la capa, cantidad de registros, encabezados formateados, filtros automáticos y paneles inmovilizados.

Si aparece el mensaje **openpyxl no instalado**, el administrador de QGIS debe instalar `openpyxl` en el entorno Python utilizado por QGIS. Instalarlo en otro Python del equipo no necesariamente resuelve el problema.

## 10.1 Ficha cartográfica en PDF

Después de realizar una consulta, el botón rojo **Salida gráfica PDF** genera la ficha de los predios seleccionados. Está visible junto a **Exportar Excel** y también como **PDF** en la ventana **Reporte Predial**. Para un predio genera una página; para varios genera un único PDF multipágina, con una ficha carta vertical por cada predio seleccionado.

La plantilla se genera automáticamente con el motor de diseños de QGIS e incluye:

- hoja tamaño carta en orientación vertical;
- mapa centrado en la geometría del predio;
- resaltado temporal del predio sin modificar la simbología de la capa;
- escala aproximada, norte y sistema de referencia;
- identificación predial, propietario, documento, dirección, matrícula, avalúo, áreas, vigencia, zonas, estrato y uso; y
- fecha de generación y nota de verificación catastral.

El atajo **Ctrl+P** abre directamente el cuadro para guardar el PDF. El nombre sugerido usa el código predial. La generación requiere una geometría válida; si el resultado proviene solo de una tabla alfanumérica sin geometría, QGIS mostrará el mensaje correspondiente.

## 11. Limpiar la consulta

Pulse **Limpiar** para:

- vaciar los filtros;
- borrar la tabla de resultados;
- reiniciar la navegación;
- limpiar la búsqueda rápida; y
- ocultar mensajes de expresión o campos faltantes.

La selección existente en el mapa puede limpiarse mediante las herramientas normales de selección de QGIS.

## 12. Consolidar / Merge (Terrenos + Vereda + R1/R2)

Esta herramienta genera una única capa de predios a partir de los terrenos urbanos y rurales, incorpora las capas de manzana y vereda, unifica sus códigos en **MANZANA_VEREDA_CODIGO**, materializa el nombre de la vereda y adjunta las tablas alfanuméricas R1 y R2 como uniones (joins) por código predial.

### 12.1 Carga directa desde archivos

Pulse el botón **⚡ Crear capa consultable desde .GDB + R1 + R2** en la ventana principal. La ventana muestra tres entradas independientes; puede seleccionarlas en cualquier orden:

1. **Geodatabase:** la carpeta con extensión `.gdb`.
2. **Registro R1:** el archivo de Registro 1.
3. **Registro R2:** el archivo de Registro 2.

La ruta de cada archivo permanece visible y el indicador cambia a `✓ GDB`, `✓ R1` o `✓ R2`. Cuando los tres están seleccionados se habilita **⚡ Crear capa unificada y consultar**. Cada entrada puede reemplazarse antes de procesar.

La herramienta busca automáticamente las capas `U_TERRENO`, `R_TERRENO`, `U_TERRENO_INFORMAL`, `R_TERRENO_INFORMAL`, `U_MANZANA` y `R_VEREDA` dentro de la geodatabase. Las cuatro capas de terreno se incorporan a la salida; el campo `ORIGEN` distingue `URBANO`, `RURAL`, `URBANO_INFORMAL` y `RURAL_INFORMAL`. Para predios urbanos copia `MANZANA_CODIGO` y para rurales `VEREDA_CODIGO` al campo común `MANZANA_VEREDA_CODIGO`.

El selector **Capa activa** muestra únicamente las capas consolidadas resultantes. Las capas fuente de Terreno, Vereda, R1, R2 y las tablas normalizadas permanecen disponibles internamente en el proyecto para sostener las uniones, pero no aparecen como opciones de consulta.

El botón **📋 Omisiones gráficas** se habilita después de la consolidación cuando existen números prediales en R1 o R2 que no aparecen en ninguna de las cuatro capas espaciales. El Excel generado incluye número predial, NoPredial, propietario, tipo y número de documento, dirección, presencia en R1/R2 y el motivo de la omisión. Si un predio tiene varios propietarios, sus nombres y documentos se conservan separados por punto y coma.

Para unir la parte alfanumérica, la herramienta prioriza **NUMERO PREDIAL** en R1 y R2 y lo compara con **CODIGO/CODIGO PREDIAL** de Terreno. Internamente crea una llave textual normalizada, por lo que diferencias de tipo, espacios, puntos o guiones no impiden la coincidencia. El registro de ejecución indica cuántos predios encontraron correspondencia en R1 y en R2.

Las fuentes se agrupan en **Fuentes GeoCatastro** y quedan ocultas en el árbol de capas para no recargar el mapa. Deben permanecer en el proyecto porque sostienen las uniones virtuales R1/R2.

### 12.2 Configuración manual

El flujo anterior se conserva dentro de la misma ventana. Si las capas ya están abiertas en QGIS, sus nombres no siguen el estándar o necesita escoger manualmente los campos de unión, use la sección **Configuración manual (opcional)** que aparece al abrir **⚡ Crear capa consultable desde .GDB + R1 + R2**.

### 12.3 Insumos del modo manual

En **Capas de entrada** seleccione (todos son opcionales salvo al menos un terreno):

- **Terreno Urbano** y **Terreno Rural:** capas poligonales de terrenos. Se combinan en una sola capa. Cada predio recibe el campo **ORIGEN** con el valor `URBANO` o `RURAL`.
- **Manzanas:** capa urbana con el código de manzana, usada para validar los códigos urbanos.
- **Veredas:** capa rural con el código y el nombre de la vereda. El nombre se copia a cada predio rural en **NOMBRE_VEREDA**.
- **R1** y **R2:** tablas alfanuméricas (con o sin geometría). Se adjuntan como joins virtuales por código predial.

Pulse **↻ Recargar capas** si agregó capas después de abrir la ventana.

### 12.4 Campos clave

En **Campos clave** la herramienta detecta automáticamente:

- **Código predial (terrenos):** llave principal (por ejemplo `CODIGO`).
- **Código manzana/vereda (terrenos):** origen del campo unificado **MANZANA_VEREDA_CODIGO**.
- **Código manzana (capa manzanas)** y **Código/Nombre vereda (capa veredas):** para validar códigos y traer el nombre rural.
- **Predial en R1** y **Predial en R2:** llave con la que se unen R1 y R2.
- **Prefijo join R1/R2:** texto que antecede a los campos unidos (por defecto `R1_` y `R2_`). Gracias a este prefijo, el resto del complemento reconoce automáticamente los campos de R1/R2 en la capa consolidada.

Todos los campos son editables: si la detección automática no acierta, elija el campo correcto en la lista. Pulse **🔍 Detectar campos clave** para volver a autodetectar tras cambiar de capa.

### 12.5 Ejecutar el modo manual

1. Escriba el **Nombre de la capa** de salida (por defecto `Predios_Consolidados`).
2. Pulse **🔗 Consolidar**.
3. Siga el avance en la barra de progreso y el registro inferior.

La capa consolidada se crea en memoria y se agrega al proyecto. El registro informa cuántos predios se generaron, cuántas manzanas y veredas se cargaron y si algún código territorial quedó sin coincidencia.

### 12.6 Notas

- La capa se crea **en memoria**: para conservarla, expórtela (clic derecho sobre la capa > **Exportar > Guardar objetos como…**) a GeoPackage u otro formato.
- Los terrenos urbanos no tienen nombre de vereda, por lo que **NOMBRE_VEREDA** queda vacío; su código de manzana sí queda en **MANZANA_VEREDA_CODIGO**.
- R1 y R2 pueden tener varios registros por predio; al adjuntarse como join no se duplica la geometría (QGIS muestra la primera coincidencia). Si necesita una fila por propietario o por unidad, use un join espacial o de tabla aparte.
- Si un código de vereda o predial no coincide, verifique tipos y ceros a la izquierda entre las capas.

## 13. Solución de problemas

### No aparece la capa

- Confirme que sea una capa vectorial.
- Pulse **↺** para actualizar la lista.
- Compruebe que la capa siga cargada en el proyecto.

### Aparecen campos no encontrados

- Abra **Campos** y revise los atributos disponibles.
- Compruebe las uniones R1/R2 en las propiedades de la capa.
- Verifique que la tabla unida esté disponible y que las llaves coincidan.
- Actualice la lista de capas después de modificar un join.

### La consulta no devuelve resultados

- Pruebe primero con una parte corta del código, nombre o documento en la búsqueda rápida.
- Quite filtros avanzados que puedan ser demasiado restrictivos.
- Confirme en la tabla de atributos que el valor realmente existe.
- Revise si el campo requerido fue detectado.

### El zoom no cambia el mapa

- Confirme que la capa tenga geometría.
- Compruebe que la consulta produjo resultados.
- Verifique que la capa y el proyecto tengan un CRS válido.

### No se puede exportar a Excel

- Confirme que haya resultados.
- Verifique permisos de escritura en la carpeta de destino.
- Asegúrese de que `openpyxl` esté instalado en el Python de QGIS.
- Pruebe una ruta local y un nombre de archivo sencillo.

### La consulta es lenta

- Use filtros específicos antes de consultar capas grandes.
- Evite ejecutar **Buscar** con todos los filtros vacíos.
- Compruebe el rendimiento de la fuente PostgreSQL/PostGIS y de los joins.

## 14. Buenas prácticas

- Mantenga nombres y tipos de campos consistentes con el modelo IGAC.
- Verifique los joins antes de iniciar una sesión de consultas.
- Use la búsqueda rápida para localizar un registro y los filtros avanzados para construir consultas precisas.
- Revise la cantidad de resultados antes de seleccionar, acercar o exportar.
- Guarde los Excel en una ubicación con permisos de escritura y compruebe el archivo generado.

## 15. Soporte

- Correo: nanometal182@gmail.com
- Repositorio: https://github.com/manfred182/qgis-plugins
- Incidencias: https://github.com/manfred182/qgis-plugins/issues

Al solicitar soporte, incluya la versión de QGIS, la versión del complemento, el mensaje completo del error y una descripción de la estructura de la capa y sus joins. No comparta contraseñas ni datos personales sensibles.

## Salida PDF de consulta o vereda

En la barra de resultados, **PDF consulta / vereda** exporta todos los resultados del buscador, independientemente del predio que se esté navegando. Busque el nombre o código de la vereda y revise los resultados antes de exportar.

El documento incluye un mapa conjunto de las geometrías encontradas y una ficha por elemento, en tamaño carta, con información en lista, escala aproximada y grilla de latitud/longitud WGS 84 (EPSG:4326). Conserva las capas visibles del mapa como contexto. El conjunto de predios no equivale al límite oficial de la vereda.

El botón **Salida gráfica PDF** y Ctrl+P mantienen la exportación de la selección del mapa o del predio navegado. Ambos formatos incluyen la grilla geográfica. Las consultas truncadas deben refinarse antes de exportar el conjunto. Se mantiene el límite de elementos por PDF del aplicativo. Los valores muy extensos se abrevian en la plantilla.

## Guardar la consolidación como Shapefile

Al finalizar el merge, el aplicativo pregunta dónde guardar `Predios_Consolidados.shp`. Los datos R1/R2 quedan incorporados en el shapefile. La capa cargada en el proyecto pasa a ser permanente. Si se cancela el diálogo, el resultado permanece temporal.

La simbología automática es sin relleno, contorno negro y grosor de 1 mm. Se guarda un archivo `.qml` junto al shapefile para conservar el estilo y los alias de los campos (DBF abrevia los nombres a 10 caracteres). Las omisiones sin geometría se guardan como una tabla `_omisiones.dbf`.

Guarde después el proyecto `.qgz` para conservar las referencias a estas capas. Al trasladar el resultado, mantenga juntos los archivos `.shp`, `.shx`, `.dbf`, `.prj`, `.cpg` y `.qml`, además de los archivos de omisiones. Guardar un proyecto o una plantilla no incorpora estos archivos dentro del proyecto.
