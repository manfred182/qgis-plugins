# Ampliación técnica propuesta para el manual

Textos de apoyo para integrar en los capítulos existentes. Conservan el trato de usted y añaden contexto sin convertir el documento en un curso avanzado. Las explicaciones conceptuales son complementos prácticos; las cifras y parámetros del archivo se identifican como datos de `servicios.qgz`.

## 1. Ortofoto y conexión REST — capítulos 6 a 8

**Texto propuesto.** «La ortofoto le permite reconocer caminos, ríos, viviendas y otros elementos del territorio mientras consulta los límites catastrales. Úsela para orientarse y comparar lo que aparece en cada fuente. La imagen y la base de predios pueden corresponder a fechas diferentes: una diferencia visual merece revisarse antes de sacar una conclusión.»

**Texto propuesto.** «La conexión REST funciona como un acceso guardado al servidor. El nombre `Ortofoto_Rural_Morelia_Caqueta` le ayuda a reconocerlo en QGIS; la URL indica dónde se encuentra la imagen. Copie la dirección completa, incluido el final `ImageServer`. Al añadir el servicio, QGIS solicita al servidor la imagen correspondiente a la vista del mapa. Por eso necesita internet y puede tardar unos segundos después de acercarse o desplazarse.»

**Comprobación para principiantes.** «Cuando termine, busque `orto/orto18479morelia` en Capas y sitúela debajo de los vectores. Si ve una imagen pero desaparecen los límites de predios, revise el orden de las capas. Si ve límites sobre fondo blanco, espere a que termine la solicitud y compruebe que está dentro de la cobertura.»

**Precisión.** Guardar el proyecto conserva la referencia al servicio; no guarda una copia completa de la ortofoto. El archivo local corrobora la URL, pero esta revisión no comprueba que el servidor esté disponible hoy. No ampliar los campos de autenticación, prefijo o portales con configuraciones que no se muestran.

## 2. Simbología — capítulos 5 y 9

**Texto propuesto.** «Empiece por una capa y observe el resultado antes de continuar. En los terrenos interesa reconocer sus límites sin cubrir la imagen; en las construcciones, una trama ayuda a distinguir las superficies. La simbología cambia la forma de ver los datos. Un color rojo o verde elegido para esta práctica no asigna una categoría oficial ni cambia la información del predio.»

**Texto propuesto.** «Un símbolo puede estar formado por varias piezas. En una construcción puede haber una línea de borde y otras líneas que crean la trama interior. Si cambia un color y una parte del símbolo conserva el anterior, revise las piezas que aparecen en el árbol del símbolo. Al aumentar el grosor o reducir la separación de la trama, el dibujo se vuelve más denso; compruebe el resultado tanto de cerca como de lejos.»

**Tabla opcional, claramente titulada “Parámetros corroborados en el proyecto suministrado”.** Usar solamente si aporta valor; no exigir que el principiante copie todos los números antes de entender la vista.

| Capa | Configuración guardada útil |
|---|---|
| R_TERRENO | Relleno transparente; borde RGB 51,160,44; 0,70 mm |
| U_TERRENO | Relleno transparente; borde RGB 31,120,180; 0,70 mm |
| R_TERRENO_INFORMAL | Contorno RGB 228,26,28; 0,96 mm |
| U_TERRENO_INFORMAL | Contorno RGB 228,227,26; 0,96 mm |
| R_CONSTRUCCION | Trama a 45°; separación 2 mm; líneas RGB 227,26,28 y 0,30 mm; borde 0,46 mm |
| U_CONSTRUCCION | Trama a 135°; separación 2 mm; líneas RGB 227,26,28 y 0,30 mm; borde 0,46 mm |
| R_CONSTRUCCION_INFORMAL | Trama a 45°; separación 2 mm; línea RGB 84,176,74 y 0,66 mm, con patrón discontinuo 0,66;2 mm; borde RGB 51,160,44 y 0,46 mm |
| U_CONSTRUCCION_INFORMAL | Tramas a 45° y 135°; separación 2 mm; líneas RGB 63,63,63 y 0,30 mm; borde 0,46 mm |

**Precisión para edición.** En las tramas, los anchos anteriores corresponden al subsímbolo `SimpleLine`. El XML conserva también `line_width=0.26` en el contenedor `LinePatternFill`. En las capas rurales, el color genérico de ese contenedor conserva un azul, pero las líneas internas están configuradas con los colores rojo y verde indicados. No confundir esos valores al describir el resultado.

## 3. Leer una tabla de atributos — capítulo 10

**Texto propuesto.** «La tabla de atributos ofrece otra forma de mirar la misma capa. Cada fila de R_TERRENO corresponde a un objeto de esa capa; las columnas reúnen los datos asociados. Antes de buscar un valor, confirme el nombre de la tabla en la barra superior. Así evita consultar por error otra capa que haya quedado seleccionada.»

**Texto propuesto.** «Una celda con puntos suspensivos puede contener un dato más largo que el espacio disponible. Amplíe la columna para leerlo completo. Desplazarse horizontalmente cambia las columnas visibles; ordenar cambia el orden de las filas. Ninguna de estas acciones modifica por sí sola los límites dibujados en el mapa.»

**Comprobación para principiantes.** «En el ejemplo, 1292 objetos totales y 1292 filtrados indican que la vista de la tabla incluye todos los objetos; 0 seleccionados indica que no hay objetos seleccionados. Estos números ayudan a entender qué está viendo. Una tabla con menos filas puede tener un filtro activo o corresponder a otra versión de los datos.»

**Precisión.** No tratar `NULL`, una celda vacía y el número cero como equivalentes. Tampoco interpretar automáticamente `SHAPE_Area` como área legal o como el área declarada en los registros. En el proyecto, R_TERRENO contiene `CODIGO`, `CODIGO_ANTERIOR`, `VEREDA_CODIGO`, `SHAPE_Length` y `SHAPE_Area`, entre otros; los nombres orientan la consulta, pero no sustituyen un diccionario de datos.

## 4. Entender R1 y R2 antes de relacionarlas — capítulo 11

**Texto propuesto.** «R1 y R2 se incorporan como tablas de consulta. Por eso pueden aparecer en Capas aunque no dibujen nada sobre la ortofoto. Para explorarlas, abra su tabla y recorra los encabezados. En R1 encontrará, entre otros, `Numero Predial`, `Nombre`, `AreaTerreno (m2)`, `Avaluo ($)` y `Vigencia`; en R2 encontrará campos como `MatriculaInmobiliaria`, `ZonaFisica`, `Habitaciones` y `AreaConstruida (m2)`. La grabación muestra 2635 filas en R1 y 3070 en R2.»

**Ejemplo hipotético explícito.** «Imagine un caso inventado: en el mapa existe un polígono con el identificador ficticio `P-001`, y en una tabla hay dos filas con ese mismo identificador, llamadas aquí “detalle A” y “detalle B”. El mapa tiene un objeto y la tabla tiene dos registros asociados. Esto explica por qué contar filas de una tabla y contar polígonos puede dar resultados diferentes. No significa, por sí solo, que haya datos repetidos por error. Este ejemplo no describe los registros reales de Morelia.»

**Texto propuesto.** «Antes de relacionar fuentes, hay que decidir qué campos representan el mismo identificador y revisar sus valores completos, tipos y posibles repeticiones. En estas fuentes aparecen nombres distintos: `CODIGO` en R_TERRENO y `NoPredial` y `Numero Predial` en los Excel. Su parecido no basta para elegir una clave. Conviene comprobar también que los identificadores conserven sus ceros iniciales y no se hayan convertido en números redondeados.»

**Límites de la explicación.** El video consulta las tablas por separado y el XML de R_TERRENO no tiene uniones configuradas. No escribir que R1/R2 ya quedaron enlazadas, ni incluir una unión como paso ejecutado. Los conteos de filas no son conteos demostrados de predios únicos. No dar significado oficial a `TipoRegistro`, `NoOrden`, `TotalRegistro`, `Espacio1` a `Espacio6` o a los sufijos `_1` y `_2` sin documentación del productor. En R2 el nombre exacto corroborado del campo usado para ordenar es `AreaTerreno (m2)_1`; el ordenamiento guardado coincide con la vista descendente.

## 5. Guardar y volver a abrir — capítulo 12

**Texto propuesto.** «El proyecto reúne su organización del trabajo: qué capas añadió, dónde están sus fuentes, cómo se dibujan y qué vista está consultando. Guárdelo en una carpeta que pueda encontrar con facilidad. Si más adelante cambia de lugar la GDB o los Excel, el proyecto puede pedirle que localice de nuevo esos archivos.»

**Ejercicio de cierre.** «Guarde su propia copia, cierre el proyecto y vuelva a abrirla. Compruebe tres cosas: que las capas se localizan, que los símbolos se conservaron y que la ortofoto responde con internet. Esta pequeña prueba permite detectar una ruta pendiente antes de continuar otro día.»

**Precisión.** Mantener el rótulo “complemento práctico”: la grabación termina con el proyecto sin título. La existencia de `servicios.qgz` no demuestra que se haya guardado durante el video. Compartir solo el QGZ no entrega los datos de la GDB ni de los Excel. No prometer recuperación sin disponer de esos insumos.

## 6. SRC de la capa y SRC del proyecto — capítulo 12

**Texto propuesto.** «Cada fuente necesita una referencia para interpretar sus coordenadas. El proyecto también tiene un SRC, que organiza la representación del mapa. QGIS puede transformar la representación de capas que usan referencias diferentes para mostrarlas juntas. Por eso encontrar dos códigos distintos no demuestra, por sí solo, que exista un problema.»

**Datos corroborados.** El proyecto suministrado y sus ocho capas de la GDB usan `ESRI:103599 — MAGNA-SIRGAS_CMT12`. La ortofoto usa `EPSG:9377 — MAGNA-SIRGAS 2018 / Origen-Nacional`. Los Excel cargados como tablas sin geometría no necesitan un SRC para consultar sus filas.

**Texto propuesto.** «Si una capa aparece desplazada, revise primero cuál es su SRC original y qué información acompaña la fuente. Asignar otro SRC cambia la interpretación de las coordenadas; reproyectar calcula coordenadas en otro sistema. Son operaciones diferentes. No cambie un código solo porque otra capa utiliza uno distinto.»

**Precisión.** No afirmar equivalencia oficial entre los dos códigos ni recomendar reemplazar uno por otro. El proyecto corrobora sus identificadores y parámetros almacenados; no certifica la exactitud de la información catastral ni valida una transformación geodésica concreta.

## Alertas generales al integrar

- Mantener tres procedencias claras: acciones observadas en el video, datos corroborados en QGZ y explicaciones o ejercicios añadidos para aprender.
- No convertir los colores o el sufijo `_INFORMAL` en un diagnóstico jurídico; conservar la clasificación del insumo.
- Usar capturas de encabezados para explicar las tablas. Los ejemplos inventados permiten enseñar relaciones sin reproducir nombres ni números de documento de las filas reales.
- El índice del builder contiene páginas escritas a mano. Al ampliar capítulos deberá recalcularse a partir del documento renderizado o sustituirse por un índice actualizable.
