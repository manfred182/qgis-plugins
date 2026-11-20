# Ampliación editorial a partir del audio: capítulos 1 a 5

Propuestas para `tmp/build_manual.py`. No se modificó el constructor ni el documento Word. Revisión basada en el texto del constructor, `tmp/audio/apuntes_audio.md` y `tmp/audio/transcript_complete.txt`; no se consultaron fuentes externas.

## Criterio de redacción

Conviene conservar el tratamiento de **usted** del manual. La cercanía puede venir de anticipar lo que la persona verá y explicar el motivo de cada acción, sin llenar el texto de diminutivos, frases de ánimo o instrucciones repetidas. El lector necesita saber dónde está, qué está haciendo y qué resultado observar.

Los bloques siguientes son texto utilizable. Las indicaciones entre corchetes son notas para quien edita y deben retirarse del Word. **Video** identifica operaciones o explicaciones respaldadas por la grabación. **Complemento didáctico** identifica aclaraciones para el principiante; no debe atribuirse su demostración al instructor.

## Apertura sugerida para el manual

[Texto listo para usar. Complemento didáctico que presenta el alcance ya existente.]

Si esta es su primera experiencia con QGIS, empiece por una tarea concreta: abrir la información de un municipio y aprender a leerla en pantalla. No necesita conocer todas las herramientas para seguir esta práctica. Primero instalará el programa; después cargará los terrenos y las construcciones de Morelia, ajustará sus colores y consultará una imagen del territorio y sus tablas.

El recorrido sigue el video de José Castillo Ospina. Cada capítulo combina instrucciones con una explicación breve de lo que ocurre en QGIS. Al terminar un procedimiento, deténgase a comparar su pantalla con el resultado descrito. Esa pausa le ayudará a reconocer dónde se encuentra antes de pasar a la siguiente tarea.

Para los ejercicios necesitará los datos indicados en “Antes de empezar”. El video y el proyecto `servicios.qgz` sirven como referencia, pero no contienen la geodatabase ni los libros Excel. Si todavía no dispone de esos insumos, puede instalar QGIS y familiarizarse con su ventana mientras los consigue.

## 1. Descargar QGIS

### Entrada propuesta

[Video 01:31–05:36, ampliado con explicación didáctica.]

QGIS permite reunir información geográfica en un mismo espacio de trabajo. En esta práctica se utilizará para visualizar los límites de los terrenos, las construcciones y una ortofoto de Morelia. El instructor lo presenta como software libre y gratuito: puede descargarlo sin realizar un pago por la instalación. Durante el proceso sí encontrará términos de licencia que deberá leer y aceptar para continuar.

La grabación utiliza QGIS **3.44.15 Solothurn**, de la rama **LTR 3.44**. Las letras LTR identifican la opción de liberación a largo plazo que se selecciona en el video. Tome ese número como referencia para reconocer las capturas del manual; cuando visite la página, los números disponibles pueden haber cambiado.

### Procedimiento ampliado

1. Abra su navegador de internet y entre en **qgis.org**. Busque **Descargar** o **Download**. Ambos nombres conducen a la sección desde la que se obtiene el programa.
2. Seleccione la opción para **Windows**. En este punto está eligiendo el instalador correspondiente al sistema operativo de la práctica.
3. Si aparece una invitación a donar, puede continuar hasta la descarga. En el video el instructor pasa esa invitación y selecciona la opción **LTR 3.44**.
4. Espere a que el navegador termine de descargar el archivo. Luego abra la carpeta **Descargas** de su equipo. En la grabación el instalador se llama **QGIS-OSGeo4W-3.44.15-2.msi**; ese nombre permite reconocer la versión utilizada.

### Explicación que falta en la versión actual

[Complemento didáctico.]

En este momento ha descargado un **instalador**, es decir, el archivo que prepara QGIS en su computador. El programa quedará disponible después de completar el asistente del capítulo siguiente. La información de Morelia se incorporará más adelante, cuando cargue la geodatabase.

Antes de continuar, compruebe que la descarga terminó y que puede localizar el archivo. El tiempo de espera depende de la conexión a internet; la rapidez que muestra el video no es una medida del tiempo que tardará en su equipo.

## 2. Instalar y abrir QGIS

### Entrada propuesta

[Video 05:36–08:54, con explicaciones didácticas.]

La instalación se realiza mediante un asistente: una sucesión de ventanas que le permiten revisar la licencia, elegir la ubicación del programa y confirmar la instalación. Algunas opciones aparecen en inglés. Los nombres que se indican a continuación le ayudarán a reconocerlas sin tener que traducir toda la ventana.

Antes de comenzar, localice el instalador descargado. Para esta parte necesitará permiso para instalar programas en el computador.

### Procedimiento ampliado

1. Haga doble clic en el instalador y espere a que aparezca el asistente. En la ventana de bienvenida, pulse **Next**, que significa **Siguiente**.
2. En el apartado de licencia, lea los términos. Para continuar, marque **I accept the terms in the License Agreement** y pulse **Next**. La aceptación de la licencia forma parte de la instalación de este software gratuito.
3. Revise **Destination Folder**, la carpeta donde se instalará el programa. En la grabación aparece `C:\Program Files\QGIS 3.44.15\`. Si no necesita una ubicación diferente, puede conservar la propuesta del asistente.
4. Revise los accesos directos. **Create desktop shortcuts** crea accesos en el escritorio y **Create start menu shortcuts** los crea en el menú Inicio. Puede conservar las opciones mostradas para encontrar el programa con facilidad.
5. Pulse **Next** y después **Install**. Si Windows solicita autorización para instalar, confirme el permiso correspondiente al instalador de QGIS que acaba de abrir.
6. Espere mientras el asistente copia y prepara los archivos. El instructor explica que la duración depende del equipo. Cuando aparezca **Finish**, pulse ese botón para terminar.
7. Abra **QGIS Desktop 3.44.15** desde **Inicio** o desde el acceso directo creado. Espere a que termine el primer arranque. El instructor señala que en ese momento se cargan los complementos y otros componentes del programa.
8. Si aparece la ventana informativa mostrada en la grabación, ciérrela después de revisarla para entrar al área de trabajo.

### Aclaraciones útiles

[Complemento didáctico.]

La carpeta de instalación contiene los archivos del programa. Los datos de Morelia pueden conservarse en su propia carpeta de trabajo; los localizará desde QGIS cuando empiece el ejercicio. Un acceso directo solo ofrece una forma cómoda de abrir la aplicación.

La señal de que puede continuar es la ventana principal de QGIS: verá una barra de menús en la parte superior, paneles a los lados y un área central destinada al mapa. También puede aparecer una página de inicio con proyectos recientes. El aspecto inicial varía si el equipo ya tenía una instalación de QGIS o una configuración anterior.

## 3. Reconocer la interfaz

### Entrada propuesta

[Video 08:54–11:40; los conceptos y el ejercicio breve son complementos didácticos.]

Antes de añadir archivos, dedique unos minutos a orientarse. Para esta práctica basta con reconocer tres lugares: **Navegador**, donde encontrará sus archivos; **Capas**, donde organizará lo que ha cargado; y el **lienzo del mapa**, donde verá el territorio. Los demás menús y botones se irán utilizando a medida que hagan falta.

En la grabación el instructor empieza con un proyecto vacío. Un proyecto reúne la configuración de su trabajo en QGIS: las fuentes que incorpora, el orden en que se dibujan y la apariencia que les asigna. Más adelante aprenderá a guardar esa organización para recuperarla.

### Tabla de apoyo propuesta

| Zona | Cómo reconocerla y usarla en esta práctica |
|---|---|
| Menús y barras superiores | Contienen las órdenes para abrir proyectos, añadir información y recorrer el mapa. Puede localizar una orden por su nombre antes de aprender su icono. |
| Navegador | Muestra unidades, carpetas y conexiones disponibles. Las pequeñas flechas permiten desplegar su contenido. Aquí buscará `18479.gdb`. |
| Capas | Muestra la información incorporada al proyecto. La casilla junto a cada nombre controla su visibilidad; el nombre seleccionado determina sobre qué capa abrirá propiedades o tablas. |
| Lienzo del mapa | Es el área central donde se dibujan las capas geográficas. Puede acercarse a una zona o desplazarse para recorrerla. |
| Barra inferior | Presenta información de la vista, como la escala, las coordenadas y el sistema de referencia del proyecto. En esta primera exploración puede observar esos datos sin modificarlos. |

### Orientación paso a paso

1. Localice **Navegador** y despliegue la unidad donde guardó sus insumos. Cada persona puede tenerlos en una ubicación distinta; siga la carpeta de su equipo en lugar de intentar reproducir la ruta del instructor.
2. Localice el panel **Capas**. Al cargar la primera capa, su nombre aparecerá allí. Ese panel será su punto de referencia para saber qué información está utilizando.
3. Identifique el lienzo central. Cuando cargue los datos, use la rueda del ratón para acercarse o alejarse y **Desplazar mapa** para recorrer la zona.

[Complemento didáctico breve.]

Si comienza en la página de inicio, puede crear el estado de trabajo de la grabación con **Proyecto → Nuevo**. Si un panel falta, actívelo desde **Ver → Paneles**. Estas rutas son apoyos para llegar a la misma disposición del video y deben señalarse como complemento práctico.

Conviene distinguir dos acciones que utilizará con frecuencia. **Hacer clic en el nombre de una capa** la deja seleccionada para consultar sus propiedades. **Marcar su casilla** permite verla en el mapa. Una capa puede permanecer cargada y seleccionada mientras su casilla está desmarcada.

Acercar, alejar o desplazar cambia la parte del territorio que está mirando. Los datos conservan su forma y ubicación; por ahora está recorriendo el mapa, sin activar herramientas de edición.

## 4. Cargar las capas rurales

### Entrada propuesta

[Video 11:09–12:47; explicación del contenedor y del gesto de arrastrar como apoyo didáctico.]

Ahora incorporará información real al proyecto. La práctica utiliza **18479.gdb**, una geodatabase con los datos de Morelia. Puede entenderla como un contenedor que reúne varios conjuntos de información geográfica. En su interior encontrará los grupos **RURAL** y **URBANO**; en este capítulo trabajará con el primero.

Los nombres ayudan a reconocer lo que va a cargar. **R_TERRENO** contiene los polígonos de los terrenos rurales y **R_CONSTRUCCION** los de las construcciones registradas en esa información. En estos nombres, **R_** identifica el ámbito rural. El instructor también explora **R_UNIDAD**, que retirará del proyecto después.

Si todavía no dispone de `18479.gdb`, necesitará conseguir ese insumo para reproducir el ejercicio. El proyecto suministrado conserva referencias a la geodatabase, pero sus datos no vienen incluidos dentro del archivo QGZ.

### Procedimiento ampliado

1. En **Navegador**, recorra las carpetas hasta encontrar **18479.gdb**. Despliegue su contenido y abra el grupo **RURAL**. Trabaje con los nombres de capa que QGIS muestra dentro de la geodatabase.
2. Localice **R_TERRENO**. Mantenga pulsado el botón izquierdo sobre su nombre, arrastre hasta el lienzo o el panel **Capas** y suelte el botón. Espere a que termine la carga y se dibujen los polígonos.
3. Repita el gesto con **R_CONSTRUCCION**. Después mire el panel **Capas**: debe poder identificar ambos nombres. Para seguir la exploración del video, puede añadir también **R_UNIDAD**.
4. Compruebe el orden de dibujo. Sitúe **R_CONSTRUCCION** encima de **R_TERRENO**. Puede cambiar el orden arrastrando el nombre dentro del panel. Así resulta más fácil distinguir las construcciones mientras el terreno todavía tiene su relleno inicial.
5. Acerque el mapa para observar los polígonos con más detalle. Marque y desmarque una casilla cada vez para reconocer qué información pertenece a cada capa. Al terminar la revisión, deje visibles terrenos y construcciones.

### Cómo interpretar el primer resultado

[Complemento didáctico.]

Los colores que aparezcan al cargar los datos pueden diferir de los de la grabación. En este primer momento sirven para dibujar las capas; en el capítulo siguiente les asignará una apariencia que facilite su lectura. Identifique cada conjunto por su nombre en **Capas** y compruebe el efecto de su casilla antes de cambiar colores.

Si los nombres aparecen en el panel pero el lienzo está vacío, haga clic derecho en **R_TERRENO** y seleccione **Zoom a la capa**. Esta comprobación lleva la vista a la extensión de los datos y puede ayudarle a encontrar una capa que ya está cargada.

Cuando el instructor retira **R_UNIDAD**, la quita de la vista de trabajo mediante el panel **Capas**. Para repetir ese paso, use el menú contextual de esa capa y la opción de retirarla del proyecto. Los datos originales siguen dentro de la geodatabase.

## 5. Configurar la simbología rural

### Entrada propuesta

[Video 12:47–14:59, con explicación didáctica.]

Ya tiene terrenos y construcciones en el mapa. El siguiente paso es hacerlos fáciles de distinguir. Para ello cambiará su **simbología**, es decir, la forma en que QGIS los dibuja. Estos ajustes afectan a su apariencia: podrá cambiar colores, contornos y tramas conservando las geometrías y los datos de las capas.

En un polígono, el **relleno** ocupa el interior y el **contorno** dibuja su borde. El instructor deja transparente el interior de los terrenos y utiliza un borde verde para reconocer sus límites. Para las construcciones emplea una trama roja: líneas repetidas dentro del polígono que permiten distinguirlas y conservar visible parte del fondo.

### Ajustar los terrenos

1. En **Capas**, localice **R_TERRENO**. Haga doble clic en su nombre o use clic derecho → **Propiedades**. En la ventana que se abre, entre en **Simbología**.
2. Mantenga **Símbolo Único**. Esta opción aplica un mismo estilo a todos los objetos de la capa; es suficiente para esta primera representación de terrenos.
3. Configure un relleno transparente y un contorno verde. En el audio, el instructor revisa **Relleno simple**, deja transparente el relleno y cambia el color del borde. El estilo **outline green**, identificado visualmente en la versión actual del manual, permite reconocer ese resultado en la galería.
4. Pulse **Aplicar** y observe el mapa. El interior de los terrenos debe permitir ver el fondo y sus límites deben seguir dibujados. Cuando el resultado sea el esperado, pulse **Aceptar**.

[Nota editorial: elegir una ruta principal inequívoca según la captura. El principiante necesita una secuencia, no una disyuntiva “elija el estilo o configure”. Si se documenta el preset, describir primero esa ruta; la configuración manual puede aparecer como alternativa claramente separada. No inventar etiquetas de controles que no se hayan leído en la ventana.]

### Ajustar las construcciones

1. Abra **Propiedades → Simbología** de **R_CONSTRUCCION**.
2. Seleccione la trama diagonal que muestra la grabación. Revise el color de las líneas del patrón y ajústelo a rojo. El instructor también revisa el borde o línea simple que forma parte del símbolo.
3. Pulse **Aplicar** para comparar el resultado con el mapa y **Aceptar** para terminar. Acerque la vista hasta distinguir las líneas de las construcciones y los contornos verdes de los terrenos.
4. Si **R_UNIDAD** continúa cargada y ya terminó de observarla, retírela desde el panel **Capas**, como hace el instructor al final de este tramo.

### Explicación que conviene añadir al cierre

[Complemento didáctico.]

**Aplicar** permite revisar los cambios manteniendo abierta la ventana de propiedades; **Aceptar** confirma la configuración y cierra la ventana. Usar primero Aplicar ayuda a comprobar que está modificando la capa que quería.

En este punto del recorrido el fondo puede seguir blanco, porque todavía no ha añadido la ortofoto. El relleno transparente permite ver lo que haya debajo; en los capítulos de conexión al IGAC podrá apreciar su utilidad sobre la imagen del territorio.

El resultado de este tramo se reconoce por dos elementos: terrenos con contorno verde y construcciones con trama roja. Los colores son la elección de esta práctica para facilitar la lectura del mapa. Al acercarse y alejarse, compruebe que la trama conserva suficiente claridad y que permite reconocer las construcciones.

El ajuste de **0,70 mm** del contorno de R_TERRENO pertenece a un momento posterior, cercano a **27:05**, y está corroborado en el proyecto suministrado. Puede mantenerse como referencia al capítulo 9; conviene evitar que el lector lo interprete como un paso ejecutado durante los minutos 12:55 a 15:30.

## Alertas factuales y de edición

1. **Mantener el dato de versión como referencia histórica del video.** No convertir 3.44.15 en una recomendación permanente de versión actual. El constructor ya distingue bien esta cuestión; conservarla al humanizar.
2. **Software gratuito y licencia.** Evitar “no necesita licencia” o “licencia perpetua” como explicación técnica general. La grabación usa expresiones coloquiales; el asistente sí muestra aceptación de términos. Basta con explicar que no se realiza un pago para descargarlo e instalarlo y que hay términos de licencia.
3. **No añadir reinicio del equipo.** El reconocimiento en 07:35–07:43 es ambiguo y el procedimiento escrito actual no lo requiere. No convertir esa frase en un paso de reiniciar Windows sin evidencia visual.
4. **No recomendar borrar la carpeta del escritorio.** El instructor relata una preferencia personal entre 07:23 y 07:43. Los accesos directos pueden mantenerse como ayuda para principiantes.
5. **Primer arranque.** El audio menciona carga de complementos. No fijar minutos de espera ni prometer un tiempo concreto: depende del equipo y de su configuración.
6. **Proyecto nuevo.** El audio confirma que abre uno vacío a las 09:00. Si se incorpora la ruta Proyecto → Nuevo, presentarla como apoyo didáctico para llegar a ese estado, salvo que la captura confirme esa misma ruta.
7. **Windows de 64 bits y requisitos de equipo.** Mantener solo lo corroborado por el instalador y los materiales actuales. No añadir cifras de RAM, disco o procesador ni afirmaciones de compatibilidad no examinadas.
8. **Datos ausentes.** La advertencia de que la GDB y los Excel no están incluidos es esencial y debe mantenerse visible antes del primer ejercicio con datos. Una redacción más cercana no debe diluir ese límite práctico.
9. **R_UNIDAD.** No definirla como apartamento, propiedad horizontal o predio independiente. El video la explora brevemente; su significado exacto no se ha verificado con un esquema de datos.
10. **Relleno, patrón y borde.** No atribuir ángulos, separaciones o grosores concretos al minuto 14 si no se leyeron en pantalla. El reconocimiento de “líneas del patrón” es suficiente para explicar la intención, pero no para inventar parámetros.
11. **Nombres ingleses de estilos.** `outline green` proviene de la revisión visual incorporada al constructor, no del audio. Conservar esa distinción interna y usar la captura para confirmar la secuencia exacta antes de ampliar los clics.
12. **Orden temporal.** Retirar R_UNIDAD ocurre hacia 14:46–14:59. Se puede anticipar como orientación en el capítulo 4, pero el paso completo encaja mejor al cerrar el capítulo 5. El grosor de 0,70 mm se ajusta después, cerca de 27:05.
13. **No duplicar explicaciones.** Si se añaden estos párrafos, reducir las definiciones repetidas de la página de términos o dejar allí versiones breves para consulta. La profundidad debe aportar comprensión, no repetir el mismo aviso en cada página.
14. **Paginación del índice.** El constructor tiene un índice con páginas fijas y `pages_planned: 16`. La ampliación cambiará la extensión del Word. Actualizar las páginas después de revisar el documento final o convertir el índice en uno que no prometa números obsoletos. Esta revisión puede realizarse en Word sin entregar ningún PDF.

## Cambios prioritarios si no se incorpora todo

- Añadir a la instalación la diferencia entre instalador, programa, accesos directos y carpeta de datos; traducir los botones una vez.
- Explicar Navegador, Capas y lienzo antes de recorrer menús secundarios. Enseñar selección y visibilidad con dos frases concretas.
- Detallar una vez el gesto de arrastrar y qué debe aparecer en pantalla; colocar la disponibilidad de la GDB antes del ejercicio.
- Separar terrenos y construcciones en dos secuencias de simbología. Explicar relleno, contorno, trama y Aplicar/Aceptar.
- Decir que el fondo blanco antes de la ortofoto es compatible con un relleno transparente bien configurado. Este detalle resuelve una duda frecuente del principiante sin añadir operaciones al tutorial.
