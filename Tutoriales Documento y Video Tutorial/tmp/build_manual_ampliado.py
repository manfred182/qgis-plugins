from pathlib import Path

# Reuse the verified document styles and screenshot helpers without running
# the first edition's content or overwriting that edition.
_base = Path(__file__).with_name('build_manual.py').read_text(encoding='utf-8')
exec(compile(_base.split("para('Manual de instalación y primeros pasos en QGIS','Title')")[0], 'manual_helpers', 'exec'))

styles['Normal'].paragraph_format.space_after = Pt(7)
DOC.core_properties.subject = 'Manual ampliado para aprender QGIS con la práctica catastral de Morelia'
DOC.core_properties.comments = 'Versión ampliada basada en el video local, el proyecto servicios.qgz y documentación oficial de QGIS 3.44. Los complementos didácticos se identifican en el texto.'
header.text = 'QGIS 3.44   |   Guía de instalación y práctica catastral'
header.runs[0].font.size = Pt(8)

para('Manual de instalación y primeros pasos en QGIS', 'Title')
para('Guía ampliada para la práctica catastral de Morelia Caquetá', 'Subtitle')
para('**Versión de referencia** QGIS 3.44.15 Solothurn en Windows\n**Fuente principal** Tutorial_1_Instalacion QGIS.mp4\n**Duración del video** 30 minutos y 48 segundos\n**Edición ampliada** 11 de octubre de 2026')
heading('Empieza por entender lo que estás viendo', 2)
para('La primera vez que abres QGIS puedes encontrarte con muchos botones y un mapa vacío. Para comenzar esta práctica basta con reconocer unas pocas herramientas: buscar los datos, añadirlos al proyecto, decidir cómo se ven y consultar la información que contienen.')
para('Esta guía te acompaña en ese recorrido con los datos de Morelia, Caquetá. Además de indicar dónde hacer clic, explica qué cambia en cada paso, por qué se hace y cómo reconocer un resultado correcto. Puedes avanzar a tu ritmo y volver al video cuando necesites ver un movimiento en pantalla.')
heading('Qué podrás hacer al terminar', 2)
para('Instalarás QGIS, cargarás terrenos y construcciones desde una geodatabase, los diferenciarás con contornos y tramas, y añadirás una ortofoto del IGAC. Después consultarás los atributos de los predios y los registros R1 y R2 en Excel. El cierre te ayudará a guardar un proyecto que puedas volver a abrir.')
heading('Hasta dónde llega esta práctica', 2)
para('El recorrido se concentra en **visualizar y consultar** información. La grabación no desarrolla edición de predios, una unión entre las tablas Excel y las capas, cálculos de avalúo ni un mapa de impresión. Los apartados de preparación, interpretación y guardado amplían el aprendizaje y se señalan como complementos didácticos.')

newpage('Antes de abrir el programa')
para('**Complemento didáctico.** Dedica unos minutos a revisar tus archivos. Así evitarás confundir un problema de instalación con la ausencia de los datos necesarios para la práctica.')
heading('Qué necesitas tener a mano', 2)
table(['Recurso', 'Para qué lo utilizarás'], [
    ('Computador con Windows de 64 bits', 'Instalar y ejecutar la versión utilizada en el video. Necesitas permiso para instalar programas.'),
    ('Conexión a internet', 'Descargar QGIS, consultar Colombia en Mapas y recibir la imagen del servicio del IGAC.'),
    ('18479.gdb', 'Cargar los polígonos de terrenos y construcciones de Morelia.'),
    ('18479-Morelia_R1.xlsx y 18479-Morelia_R2.xlsx', 'Consultar los registros alfanuméricos que aparecen al final del tutorial.'),
    ('servicios.qgz', 'Revisar la configuración del proyecto suministrado, si cuentas también con sus fuentes de datos.')
], [2.65, 4.39], 10.5)
para('En la carpeta del tutorial se recibieron **el video y servicios.qgz**. La geodatabase y los dos Excel están referenciados en ese proyecto, pero no están incluidos en esta carpeta ni empaquetados dentro del QGZ. Si todavía no los tienes, puedes completar la instalación y familiarizarte con la interfaz. Para reproducir las capas y las tablas necesitarás esos insumos.')
heading('Organiza una carpeta de trabajo', 2)
para('Puedes crear una carpeta llamada **Practica_Morelia** y guardar allí el proyecto que vas a construir. Conserva la GDB completa y los Excel en una ubicación estable. Una GDB es una carpeta con varios archivos internos: no extraigas uno de ellos para cargarlo de forma aislada ni cambies sus nombres internos.')
para('Cuando veas una ruta del computador del instructor, úsala como orientación para localizar el tipo de archivo. En tu equipo la letra del disco y las carpetas pueden ser diferentes. Lo que debes encontrar es la fuente correcta, por ejemplo **18479.gdb**, dentro de la ubicación donde recibiste los datos.')
heading('Cómo seguir las indicaciones', 2)
para('Las rutas como **Propiedades → Simbología** indican una secuencia de opciones. Los nombres en negrita te ayudan a reconocer botones, capas y campos. Cada capítulo incluye una referencia temporal al video; algunas capturas se han recortado para que los controles sean legibles.')
para('Las comprobaciones te permiten detenerte y revisar el resultado antes de continuar. Si algo cambia de color o no aparece, vuelve primero a la capa seleccionada, su casilla de visibilidad y su posición en el panel Capas.')

newpage('Contenido de la guía')
table(['Recorrido', 'Páginas', 'Referencia del video'], [
    ('Conceptos para entender el mapa', '4', 'Complemento didáctico'),
    ('1 Descargar QGIS', '5', '01:31 a 05:35'),
    ('2 Instalar y abrir QGIS', '6', '05:35 a 08:40'),
    ('3 Reconocer la interfaz y navegar', '7 y 8', '08:40 a 11:40'),
    ('4 Cargar las capas rurales', '9', '11:40 a 12:55'),
    ('5 Preparar la simbología rural', '10 y 11', '12:55 a 15:30'),
    ('6 Buscar y entender la ortofoto', '12 y 13', '16:25 a 18:45'),
    ('7 Conectar el servicio REST', '14', '18:45 a 20:05'),
    ('8 Añadir las capas urbanas', '15', '20:05 a 22:40'),
    ('9 Diferenciar todas las capas', '16 y 17', '22:40 a 27:20'),
    ('10 Leer la tabla de atributos', '18', '27:20 a 28:20'),
    ('11 Consultar R1 y R2 y entender su relación', '19 y 20', '28:20 a 30:48'),
    ('12 Guardar y recuperar el proyecto', '21 y 22', 'Complemento didáctico'),
    ('13 Resolver problemas frecuentes', '23', 'Complemento didáctico'),
    ('14 Repetir el recorrido con autonomía', '24', 'Ejercicio de repaso'),
    ('15 Comprobar lo aprendido', '25', 'Cierre de la práctica'),
    ('Fuentes y consultas', '26', 'Material de referencia')
], [3.85, .75, 2.44], 10.5)
heading('Una forma cómoda de avanzar', 2)
para('Si estás empezando, sigue el orden de la guía y haz una pausa después de cargar las primeras capas. Cuando ya puedas ver terrenos y construcciones, continúa con la ortofoto. Deja las tablas para el momento en que puedas reconocer esas capas sin dificultad.')
para('Si ya tienes QGIS instalado, puedes comenzar en el capítulo 3. Si solo necesitas recuperar el proyecto suministrado, ve al capítulo 12 y comprueba antes que cuentas con la GDB y los Excel originales.')
para('Los tiempos describen la grabación y son aproximados. La versión del programa, los conteos y los parámetros que se citan corresponden al material revisado; no tienen que coincidir con una actualización posterior de los insumos.')

newpage('Conceptos para entender el mapa')
para('**Complemento didáctico.** Entender estas diferencias te ayudará a interpretar lo que hace QGIS. No necesitas memorizar todas las definiciones antes de empezar; vuelve a ellas cuando encuentres una palabra nueva.')
heading('El proyecto organiza tu trabajo', 2)
para('El **proyecto** reúne las capas que abriste, el orden en que se dibujan, sus símbolos y la configuración del mapa. En esta práctica se guarda con extensión **.qgz**. Piensa en él como el documento que conserva la preparación de tu sesión: al abrirlo, QGIS vuelve a buscar las fuentes que tiene registradas.')
para('Las **fuentes de datos** son los archivos o servicios que contienen la información. Aquí son la GDB, los Excel y el servicio de la ortofoto. Guardar el proyecto no sustituye a guardar esas fuentes; por eso también necesitas conservarlas.')
heading('Una capa representa un conjunto de información', 2)
para('Una **capa vectorial** representa objetos mediante puntos, líneas o polígonos. Los terrenos y las construcciones de esta práctica se muestran como polígonos. Cada objeto tiene una geometría, que permite dibujarlo, y atributos, que describen sus características.')
para('Una **capa ráster** representa información organizada en píxeles. La ortofoto pertenece a este tipo y funciona aquí como imagen de referencia. Una **tabla sin geometría**, como los registros Excel que se cargan, puede aparecer en Capas y consultarse aunque no dibuje ningún elemento en el mapa.')
heading('La apariencia también comunica', 2)
para('La **simbología** determina cómo se ve cada objeto: color, relleno, contorno o trama. Un terreno verde no adquiere una condición nueva por ese color; simplemente lo estamos representando así. Cambiar su símbolo no cambia sus coordenadas ni los valores de la tabla.')
para('El **orden de dibujo** decide qué aparece por encima. Si una imagen cubre todo el lienzo y está encima de los polígonos, puede ocultarlos. Por eso situaremos la ortofoto debajo de las capas vectoriales y evitaremos rellenos opacos en los terrenos.')
heading('La ubicación necesita un sistema común', 2)
para('El **sistema de referencia de coordenadas**, abreviado SRC o CRS, da significado espacial a las coordenadas. En el capítulo 12 revisarás los sistemas almacenados en el proyecto. Por ahora conserva la información de origen: cambiar un código sin comprobarlo puede colocar una capa en un lugar incorrecto.')

newpage('1 Descargar QGIS', '01:31 a 05:35')
para('En el video se utiliza **QGIS 3.44.15 Solothurn**, de la rama de soporte prolongado **LTR 3.44**, para Windows. Esta es la referencia de las capturas y de las opciones de la guía. La página de descarga puede mostrar versiones diferentes cuando la visites.')
steps([
    'Abre el navegador y entra a **qgis.org**. Busca la opción **Descargar** o **Download** para llegar a la página oficial de instaladores.',
    'Selecciona **Windows**. Si aparece una invitación a donar, puedes continuar a la descarga; en la grabación la donación es voluntaria.',
    'Localiza la opción de soporte prolongado **LTR**. El instructor selecciona **LTR 3.44** y descarga el instalador autónomo para Windows.',
    'Espera a que termine la descarga y abre **Descargas**. El archivo visible en el tutorial se llama **QGIS-OSGeo4W-3.44.15-2.msi**.'
])
figure(275, 'Opción LTR utilizada por el instructor en la página oficial.', (1020, 260, 1645, 790), 4.9)
para('**Antes de abrir el archivo.** Comprueba que la descarga haya finalizado. Has obtenido el instalador, que preparará QGIS en tu equipo. El programa quedará disponible al completar el asistente; los datos de Morelia se cargarán después. El tiempo de descarga depende de tu conexión.')
para('No necesitas buscar un instalador con el mismo número en sitios de terceros para seguir los conceptos de la práctica. Si tu versión tiene otra organización de botones, busca el nombre de la herramienta que se indica en la guía.')
link('Descarga oficial de QGIS', 'https://qgis.org/download/')

newpage('2 Instalar y abrir QGIS', '05:35 a 08:40')
para('El asistente de instalación prepara el programa en tu equipo. Algunas pantallas aparecen en inglés; aquí encontrarás el texto que se ve en el video junto con la acción que debes realizar.')
steps([
    'Haz doble clic en el instalador y espera a que se abra Windows Installer. En la bienvenida, pulsa **Next**, que equivale a Siguiente.',
    'Lee la licencia. Para continuar, marca **I accept the terms in the License Agreement** y pulsa **Next**.',
    'En **Destination Folder**, revisa la carpeta de destino. El instructor conserva **C:\\Program Files\\QGIS 3.44.15\\**. Si no tienes un motivo para elegir otra, puedes conservar la propuesta del asistente.',
    'Las opciones **Create desktop shortcuts** y **Create start menu shortcuts** crean accesos en el escritorio y en Inicio. Déjalas activadas si quieres abrir QGIS desde esos lugares. Pulsa **Next** y después **Install**.',
    'Si Windows pide autorización, comprueba que corresponde al instalador oficial que descargaste y permite continuar. Espera a que finalice la instalación; luego pulsa **Finish**.',
    'Busca **QGIS Desktop 3.44.15** en Inicio o utiliza el acceso creado. El primer arranque puede tardar mientras se carga el programa. Si aparece una ventana informativa, ciérrala para acceder al área de trabajo.'
])
figure(365, 'Carpeta de instalación y opciones para crear accesos directos.', (705, 193, 1205, 584), 4.25)
para('**Ya puedes continuar cuando** veas la ventana principal con menús, paneles laterales y el lienzo del mapa. Que el lienzo esté vacío es normal: todavía no has añadido información.')
para('La carpeta de instalación contiene el programa; tus datos pueden estar en otra carpeta. Si no tienes permiso para instalar, necesitarás al responsable de tu equipo. Las carpetas y conexiones de una instalación anterior también pueden seguir apareciendo al abrir QGIS.')

newpage('3 Reconocer la interfaz', '08:40 a 11:40')
para('Antes de buscar herramientas nuevas, ubica las zonas que utilizarás durante todo el recorrido. En el computador del instructor ya existen carpetas y conexiones configuradas; tu pantalla puede verse más vacía.')
figure(635, 'Navegador y Capas a la izquierda y lienzo del mapa en el área central.', (0, 0, 1918, 1030), 7.04)
table(['Zona', 'Qué harás allí'], [
    ('Menús y barras superiores', 'Abrir proyectos y acceder a herramientas de carga, navegación y consulta.'),
    ('Navegador', 'Encontrar discos, carpetas, geodatabases, libros Excel y conexiones.'),
    ('Capas', 'Ver qué datos están cargados, activarlos, seleccionarlos y ordenarlos.'),
    ('Lienzo del mapa', 'Observar la representación de los datos y recorrer el territorio.'),
    ('Barra inferior', 'Consultar la escala, las coordenadas y el SRC del proyecto.')
], [1.6, 5.44], 10.5)
para('La diferencia entre **Navegador** y **Capas** es útil desde el inicio: el primero te muestra dónde están las fuentes; el segundo te muestra cuáles has incorporado al proyecto. Encontrar un archivo en Navegador no significa que ya esté cargado.')
para('**Si falta un panel.** Como complemento práctico, entra a **Ver → Paneles** y activa **Navegador** o **Capas**. Puedes volver a colocar los paneles de forma que el mapa quede visible.')

newpage('Practicar la navegación y la selección', '08:40 a 11:40')
para('**Complemento didáctico del capítulo 3.** Estas acciones se parecen entre sí, pero producen resultados diferentes. Aprender a distinguirlas evita muchos tropiezos al configurar un mapa.')
heading('Seleccionar una capa no es ocultarla', 2)
para('Haz clic en el **nombre** de una capa para convertirla en la capa activa. Esa selección determina sobre qué capa abrirás Propiedades o la tabla de atributos. Haz clic en su **casilla** para mostrarla u ocultarla. Una capa puede estar seleccionada y, al mismo tiempo, tener la visibilidad desactivada.')
para('Cuando abras una ventana de propiedades, mira su título antes de cambiar un valor. Si querías modificar R_TERRENO y la ventana pertenece a R_CONSTRUCCION, ciérrala y selecciona la capa correcta. Este hábito es más fiable que intentar recordar cuál fue tu último clic.')
heading('Acercarte no cambia los datos', 2)
para('La rueda del ratón permite acercar o alejar la vista. La herramienta **Desplazar mapa** permite recorrer el lienzo sin editar las geometrías. Al acercarte ves una porción menor del territorio con más detalle; al alejarte recuperas el contexto general.')
para('La escala de la barra inferior ayuda a entender ese cambio. Por ejemplo, **1:2 000** representa una vista de mayor detalle que **1:20 000**. El ejemplo es explicativo; no es una escala obligatoria de la práctica ni garantiza por sí solo que la imagen tenga más resolución.')
heading('Recuperar una capa que quedó fuera de la vista', 2)
steps([
    'En Capas, comprueba que la casilla del conjunto que buscas esté activada.',
    'Haz clic derecho sobre el nombre y elige **Zoom a la capa**. QGIS ajustará la vista a la extensión de esa capa.',
    'Si la fuente está disponible pero todavía no la distingues, revisa si otra capa la tapa o si su relleno se confunde con el fondo.'
])
heading('Una prueba breve para familiarizarte', 2)
para('Después de cargar los terrenos en el siguiente capítulo, desactiva y activa su casilla. Luego selecciona su nombre y vuelve a usar Zoom a la capa. Observa qué cambia en cada caso. No necesitas activar la edición para realizar ninguna de estas acciones.')
para('Al terminar, deberías poder explicar con tus palabras la diferencia entre buscar un archivo, cargarlo, seleccionarlo y ocultarlo. Son cuatro acciones distintas que se repiten a lo largo de toda la guía.')

newpage('4 Cargar las capas rurales', '11:40 a 12:55')
para('La práctica comienza con **18479.gdb**, la geodatabase de Morelia. Dentro de ella se agrupan datos rurales y urbanos. Vas a abrir primero los terrenos y las construcciones rurales para trabajar con pocos elementos y reconocer su función.')
steps([
    'En **Navegador**, despliega la unidad y las carpetas donde guardaste los insumos. Localiza **18479.gdb** y expándela. Abre el grupo **RURAL**.',
    'Busca **R_TERRENO**. Mantén pulsado el botón izquierdo sobre su nombre, arrastra hasta el lienzo o el panel **Capas** y suelta. Espera a que aparezcan los polígonos: representan los terrenos de esa fuente.',
    'Añade **R_CONSTRUCCION** de la misma manera. Añade también **R_UNIDAD** para repetir la exploración del instructor; la retirarás al terminar el ajuste del capítulo siguiente.',
    'En Capas, deja **R_CONSTRUCCION** por encima de **R_TERRENO**. Si es necesario, arrastra su nombre para cambiar el orden. Acércate hasta distinguir las construcciones.',
    'Reconoce cada conjunto activando y desactivando su casilla. Al terminar el ajuste del capítulo siguiente retirarás **R_UNIDAD**, como hace el instructor. Quitarla del proyecto no borra sus datos de la GDB.'
])
figure(725, 'Carga de R_CONSTRUCCION desde el grupo RURAL antes de ordenar las capas.', (0, 150, 1200, 900), 5.55)
para('**Qué debes ver.** R_TERRENO y R_CONSTRUCCION aparecen en Capas y sus objetos se dibujan. Los colores iniciales pueden ser distintos de los del video porque QGIS asigna símbolos al cargar los datos.')
para('Si el lienzo permanece vacío, empieza por **Zoom a la capa**. Si no encuentras la GDB en Navegador, comprueba su ubicación y que la carpeta esté completa. El proyecto servicios.qgz no reemplaza esa fuente.')

newpage('5 Preparar la simbología rural', '12:55 a 15:30')
para('Ahora vas a facilitar la lectura del mapa. Los terrenos se mostrarán con contorno verde y sin relleno visible; las construcciones, con una trama roja. De esta manera podrás distinguir ambos conjuntos y, más adelante, ver la ortofoto debajo.')
steps([
    'Haz doble clic en **R_TERRENO** o entra a **Propiedades** desde su menú contextual. Abre **Simbología** y mantén el renderizador **Símbolo Único**.',
    'En la galería, elige **outline green**, el estilo de contorno verde. Pulsa **Aplicar** para revisar el cambio en el lienzo y después **Aceptar** para confirmar y cerrar la ventana.',
    'Abre la simbología de **R_CONSTRUCCION** y elige **hashed black /** en la galería. En el árbol del símbolo, revisa **Relleno en patrón de línea** para las líneas interiores y la **Línea simple** exterior para el contorno. Ajusta ambos a rojo para obtener el resultado de referencia.',
    'Aplica el cambio, cierra el diálogo y acércate a una zona donde puedas distinguir las construcciones dentro de los terrenos. Si R_UNIDAD sigue cargada, retírala para mantener la vista de este tramo.'
])
figure(905, 'Contornos verdes de terrenos y tramas rojas de construcciones.', (440, 120, 1918, 1005), 6.6)
para('**Comprueba el resultado.** El terreno conserva un borde y deja ver el fondo, que todavía puede ser blanco. Las construcciones se distinguen por sus líneas rojas. Si todo parece una mancha, acércate y revisa el relleno; el apartado siguiente explica sus componentes.')
para('Cerca de **27:05**, el instructor ajusta el contorno de R_TERRENO a **0,70 mm**. Ese es el valor conservado en servicios.qgz; puedes aplicarlo al completar la simbología de todas las capas.')

newpage('Entender los componentes del símbolo', '12:55 a 15:30')
para('**Complemento didáctico del capítulo 5.** Un polígono tiene un interior y un borde. Puedes representarlos de formas diferentes sin modificar el objeto geográfico. Esta distinción ayuda a decidir qué cambiar cuando un símbolo no se ve como esperabas.')
heading('El relleno ocupa el interior', 2)
para('Un relleno sólido colorea toda la superficie del polígono. Es útil para algunos mapas, pero en esta práctica puede tapar la imagen que colocaremos debajo. Un relleno transparente o sin relleno visible deja libre el interior y permite consultar el fondo.')
para('Si necesitas que el límite siga destacándose, conserva el contorno y cambia solo el relleno. Reducir la opacidad de toda la capa también puede atenuar el borde; por eso conviene revisar qué parte del símbolo estás modificando.')
heading('El contorno marca el límite', 2)
para('El color te ayuda a reconocer el conjunto y la anchura determina cuánto destaca su línea. Los valores en milímetros de la simbología describen el grosor con que se dibuja el símbolo; **no son una medida del ancho real del terreno**.')
para('Una línea muy gruesa puede ocultar objetos cercanos cuando estás lejos. Una muy fina puede perderse sobre una imagen con muchos detalles. Usa Aplicar para evaluar el resultado en una vista general y en una vista cercana antes de darlo por terminado.')
heading('La trama diferencia las construcciones', 2)
para('Una trama usa líneas repetidas para reconocer la superficie sin cubrirla por completo. Su apariencia depende del color, el ángulo, el grosor y la separación. Una trama cruzada combina direcciones; una discontinua interrumpe las líneas y produce otro patrón.')
para('En un símbolo compuesto puedes encontrar varios componentes, por ejemplo una trama interior y una línea de contorno. Selecciona el componente correcto antes de cambiar su color o anchura. Si solo cambias uno, los demás pueden conservar su apariencia anterior.')
heading('Aplicar un símbolo único', 2)
para('**Símbolo Único** asigna la misma apariencia a todos los objetos de una capa. Aquí funciona porque las categorías ya vienen separadas en capas distintas: R_TERRENO, R_CONSTRUCCION y los conjuntos con el sufijo _INFORMAL. No se está creando una clasificación por un campo de la tabla.')
para('Al revisar tu mapa, pregúntate si puedes distinguir el límite del terreno, reconocer la construcción y seguir viendo la referencia del fondo. Si esas tres lecturas son posibles, la simbología está cumpliendo su propósito en esta práctica.')

newpage('6 Localizar la ortofoto del IGAC', '16:25 a 18:45')
para('Los polígonos muestran límites y formas; la ortofoto aporta contexto visual. El instructor la busca en **Colombia en Mapas**, el portal del IGAC, para observar el territorio de Morelia junto con las capas catastrales.')
steps([
    'Abre **colombiaenmapas.gov.co**. Usa los **Filtros** por entidad territorial para localizar **Morelia, Caquetá** y consultar los productos disponibles.',
    'Busca la ficha **Ortoimagen Departamento de Caquetá Municipio de Morelia Resolución 50 cm Año 2022**. Revisa el municipio, la cobertura y el año antes de continuar.',
    'En los resultados también aparece una ortoimagen de la cabecera municipal con resolución de **10 cm** y año **2021**. Es otro producto; no lo confundas con la imagen de 50 cm de esta práctica.',
    'Visualiza el producto y revisa su ficha. Baja hasta **Enlaces de interés**, abre **Servicio (REST)** y copia la dirección completa de la página que se abre.'
])
figure(1110, 'Ficha del producto con su resolución y enlace al servicio REST.', (0, 550, 530, 1025), 3.55)
para('**La comprobación clave.** Para este recorrido, la dirección termina en **orto/orto18479morelia/ImageServer**. Es la que vas a usar en QGIS. Copia el enlace del servicio, no la dirección general del portal ni la página de resultados.')
para('Si el portal cambia su distribución, busca los mismos datos de identificación en la ficha. La coincidencia del municipio y del producto es más útil que la posición exacta de un botón.')
link('Abrir Colombia en Mapas', 'https://www.colombiaenmapas.gov.co/')

newpage('Leer la ortofoto con cuidado', '16:25 a 21:08')
para('**Complemento didáctico del capítulo 6.** La imagen es una ayuda para orientarte y comparar, pero su fecha y su resolución condicionan lo que puedes interpretar. Conviene conocerlas antes de sacar conclusiones sobre un predio.')
heading('Qué significa una resolución de 50 cm', 2)
para('Como explicación general, una resolución espacial de 50 cm describe un tamaño de píxel en terreno de aproximadamente medio metro. No quiere decir que cualquier objeto de ese tamaño sea reconocible ni que esa cifra sea la exactitud de los límites catastrales.')
para('Al acercarte mucho, los píxeles se hacen más visibles; el zoom no crea detalles que la imagen no contiene. Por eso puedes llegar a un punto en que aumentar la vista solo agrande la imagen sin mejorar la interpretación.')
heading('La fecha de los insumos y la de elaboración son distintas', 2)
para('La ficha revisada muestra insumos de **febrero de 2022** y elaboración del producto en **junio de 2024**. Esas fechas describen momentos diferentes del proceso. Una elaboración posterior no implica que todas las escenas se hayan capturado ese mismo año.')
para('El instructor señala que algunas construcciones de la base pueden no aparecer en la ortofoto. Antes de interpretar una diferencia como un error, considera si la construcción es posterior a la imagen y si estás mirando el lugar y la capa correctos.')
heading('Qué puedes observar y qué necesita otra comprobación', 2)
para('Puedes usar la ortofoto para reconocer vías, sectores edificados y el contexto visible de un polígono. Si un límite o una construcción no coincide a primera vista, registra la diferencia y revisa las fuentes, sus fechas y sus sistemas de referencia.')
para('La imagen por sí sola no demuestra la condición jurídica de un predio, la titularidad de una persona ni la clasificación formal o informal de una construcción. En esta guía se conservan los conjuntos que trae la GDB; no se reclasifican por su apariencia.')
heading('Recibir una imagen por internet', 2)
para('QGIS solicitará al servicio la imagen necesaria para la vista que estás consultando. Al mover o acercar el mapa puede tardar en renovarse y dibujarse por partes. Esto explica los rectángulos que se ven durante algunos momentos de la grabación.')
para('Distingue ese refresco temporal de una zona sin cobertura. Primero espera; después vuelve a una zona conocida del municipio. Si la imagen no llega, revisa la conexión y el enlace siguiendo el capítulo de problemas frecuentes.')

newpage('7 Crear la conexión REST en QGIS', '18:45 a 20:05')
para('La conexión guarda un nombre y la dirección del servicio. **Crear**, **conectar** y **añadir** son pasos distintos: registrarás la dirección, consultarás lo que ofrece y finalmente incorporarás la imagen al proyecto.')
steps([
    'En QGIS, abre el **Administrador de fuentes de datos**, entra a **Servidor REST ArcGIS** y pulsa **Nuevo**. Como apoyo, puedes abrir el administrador con el atajo **Ctrl + L**.',
    'Escribe **Ortofoto_Rural_Morelia_Caqueta** en **Nombre**. Este texto es una etiqueta para reconocer la conexión en tu equipo.',
    'Pega la URL completa indicada debajo. En la grabación se usa **Sin Autenticación** y los campos opcionales conservan sus valores predeterminados. Pulsa **Aceptar**.',
    'Selecciona la conexión recién creada y pulsa **Conectar**. Cuando aparezca el recurso **orto/orto18479morelia**, selecciónalo y pulsa **Añadir**.',
    'Cierra el administrador al ver la capa en el proyecto. Si se dibuja por encima de los polígonos, arrástrala al final del panel Capas.'
])
link('https://mapas2.igac.gov.co/image/rest/services/orto/orto18479morelia/ImageServer', 'https://mapas2.igac.gov.co/image/rest/services/orto/orto18479morelia/ImageServer')
figure(1165, 'Nombre de la conexión, URL completa y opción Sin Autenticación.', (635, 303, 1495, 850), 6.15)
para('**Comprueba dos cosas.** La capa debe aparecer en Capas y la imagen debe verse en una zona cubierta. Tener la conexión guardada sin pulsar Añadir todavía no incorpora la imagen al mapa.')
para('El administrador identifica el SRC de la ortofoto como **EPSG:9377 — MAGNA-SIRGAS 2018 / Origen-Nacional**. Añadir el servicio mantiene una consulta remota; no descarga una copia completa para trabajar sin internet.')

newpage('8 Añadir las capas urbanas', '20:05 a 22:40')
para('Con la imagen al fondo puedes ampliar la práctica a los datos urbanos y a los conjuntos que traen el sufijo **_INFORMAL**. Los prefijos **R_** y **U_** identifican aquí el ámbito rural y urbano. Mantener esos nombres te ayudará a orientarte.')
steps([
    'Sitúa **orto/orto18479morelia** debajo de las capas vectoriales. Acércate a una zona de trabajo y espera a que termine de actualizarse la imagen.',
    'En **Navegador → 18479.gdb**, abre **URBANO**. Añade **U_TERRENO**, **U_TERRENO_INFORMAL**, **U_CONSTRUCCION** y **U_CONSTRUCCION_INFORMAL**.',
    'En el grupo **RURAL**, añade **R_TERRENO_INFORMAL** y **R_CONSTRUCCION_INFORMAL**. Conserva también R_TERRENO y R_CONSTRUCCION.',
    'Revisa el panel antes de cambiar símbolos. Debes reconocer ocho capas vectoriales: cuatro de terrenos y cuatro de construcciones, contando los conjuntos rurales, urbanos y sus variantes informales.'
])
figure(1325, 'Conjuntos rurales y urbanos sobre la ortofoto antes del ajuste final de símbolos.', (0, 590, 1918, 1005), 7.04)
heading('Ordenar para poder leer', 2)
para('Como criterio de trabajo, deja la ortofoto al fondo, los terrenos encima de ella y las construcciones por encima de los terrenos. Si dos contornos se superponen, oculta temporalmente una capa para identificar a cuál pertenece cada línea. Es una ayuda de lectura; no cambia la fuente.')
para('Revisa también que los terrenos no tengan rellenos sólidos. Colocar una capa por encima no basta si su interior tapa toda la imagen. El orden y la transparencia trabajan juntos para mantener visible la información.')
para('**Antes de seguir.** Comprueba los nombres y las casillas de las ocho capas. Conserva la clasificación que recibiste en los insumos: el sufijo _INFORMAL identifica un conjunto de la fuente y no una conclusión que debas establecer mirando la ortofoto.')

newpage('9 Diferenciar terrenos y construcciones', '22:40 a 27:20')
para('Ahora el mapa tiene más información y necesita una apariencia consistente. La siguiente tabla resume el resultado visual de la práctica, corroborado en el proyecto suministrado. Los colores sirven para reconocer las capas dentro de este ejercicio; no se presentan como una norma cartográfica general.')
table(['Capa', 'Apariencia de referencia'], [
    ('R_TERRENO', 'Contorno verde y relleno transparente'),
    ('R_TERRENO_INFORMAL', 'Contorno rojo'),
    ('R_CONSTRUCCION', 'Trama diagonal roja'),
    ('R_CONSTRUCCION_INFORMAL', 'Trama discontinua verde'),
    ('U_TERRENO', 'Contorno azul y relleno transparente'),
    ('U_TERRENO_INFORMAL', 'Contorno amarillo'),
    ('U_CONSTRUCCION', 'Trama diagonal roja en otra dirección'),
    ('U_CONSTRUCCION_INFORMAL', 'Trama cruzada gris oscura')
], [2.9, 4.14], 10.5)
steps([
    'Abre **Propiedades → Simbología** en la capa que quieres cambiar. En los terrenos, configura un contorno visible y deja transparente el interior.',
    'En las construcciones, elige una trama diagonal, discontinua o cruzada según la tabla. El video muestra estilos de la galería como **hashed black \\** y **hashed black X**, cuyos colores después se ajustan.',
    'Pulsa **Aplicar** y revisa el resultado antes de **Aceptar**. Repite con las demás capas y termina ajustando R_TERRENO a **0,70 mm**, como se observa cerca de 27:05.'
])
figure(1565, 'Tramas y contornos que permiten leer los polígonos sobre la imagen.', (440, 120, 1918, 600), 7.04)
para('Si dos categorías se confunden, verifica primero que modificaste la capa correcta y todos los componentes del símbolo. La página siguiente reúne parámetros guardados que te permiten reproducir el estado de referencia con más precisión.')

newpage('Parámetros del proyecto de referencia')
para('**Complemento técnico del capítulo 9.** Estos valores se extrajeron de **servicios.qgz**. Describen su estado guardado y sirven para profundizar la reproducción de los símbolos. No todos los ajustes se leen con claridad durante la grabación.')
heading('Contornos de los terrenos', 2)
table(['Capa', 'Color del contorno', 'Anchura'], [
    ('R_TERRENO', 'Verde RGB 51 160 44', '0,70 mm'),
    ('U_TERRENO', 'Azul RGB 31 120 180', '0,70 mm'),
    ('R_TERRENO_INFORMAL', 'Rojo RGB 228 26 28', '0,96 mm'),
    ('U_TERRENO_INFORMAL', 'Amarillo RGB 228 227 26', '0,96 mm')
], [2.8, 3.24, 1.0], 10)
para('En R_TERRENO y U_TERRENO el relleno es transparente. Los dos conjuntos informales están representados mediante líneas de contorno. **RGB** expresa las cantidades de rojo, verde y azul del color; puedes introducirlas si necesitas la misma tonalidad.')
heading('Tramas de las construcciones', 2)
table(['Capa', 'Interior del símbolo', 'Contorno'], [
    ('R_CONSTRUCCION', 'Rojo RGB 227 26 28\nÁngulo 45° y separación 2 mm\nLínea interna 0,30 mm', 'Rojo\n0,46 mm'),
    ('U_CONSTRUCCION', 'Rojo RGB 227 26 28\nÁngulo 135° y separación 2 mm\nLínea interna 0,30 mm', 'Rojo\n0,46 mm'),
    ('R_CONSTRUCCION_INFORMAL', 'Verde RGB 84 176 74\n45° y separación 2 mm\nLínea discontinua 0,66 mm\nPatrón 0,66;2 mm', 'Verde RGB 51 160 44\n0,46 mm'),
    ('U_CONSTRUCCION_INFORMAL', 'Gris RGB 63 63 63\nDos tramas a 45° y 135°\nSeparación 2 mm\nLíneas internas 0,30 mm', 'Gris\n0,46 mm')
], [2.8, 2.9, 1.34], 9.5)
para('La separación determina la distancia entre líneas de la trama. El patrón **0,66;2 mm** alterna un tramo dibujado de 0,66 mm con una separación de 2 mm. Para la trama cruzada urbana hay dos componentes interiores; ambos deben conservarse.')
para('Al configurar un símbolo compuesto, revisa sus líneas internas y su contorno por separado. Las anchuras de esta tabla corresponden a esos componentes de línea. Evalúa el resultado a más de una escala: copiar un valor no sustituye a comprobar si el mapa se puede leer.')

newpage('10 Leer la tabla de atributos', '27:20 a 28:20')
para('Hasta ahora has observado formas y colores. La tabla de atributos te permite leer la información asociada a cada objeto de una capa. En el tutorial se abre **R_TERRENO** para revisar sus datos descriptivos.')
steps([
    'Selecciona **R_TERRENO** en Capas, haz clic derecho y elige **Abrir tabla de atributos**. Confirma el nombre de la capa en el título de la ventana.',
    'Lee los encabezados. Cada columna es un campo y cada fila corresponde a un objeto de esta capa. Desplázate horizontalmente para ver las columnas que no caben en la pantalla.',
    'Observa los contadores. La grabación muestra **1292** objetos totales, **1292** filtrados y **0** seleccionados. Esos números describen la base del video; otra entrega puede tener una cantidad diferente.',
    'Cuando termines, cierra la tabla para volver al mapa. Consultar valores no requiere activar la edición.'
])
figure(1655, 'Encabezados y contadores de R_TERRENO sin reproducir los registros personales.', (10, 72, 1350, 154), 7.04)
heading('Leer los contadores sin confundirlos', 2)
para('El total indica cuántos objetos contiene la capa. El contador de filtrados permite saber cuántos cumplen la condición de visualización vigente. Los seleccionados son los objetos que has marcado para trabajar o consultar. Una selección no equivale por sí sola a borrar los demás registros.')
para('Si ves menos filas de las esperadas, revisa el modo de visualización y los filtros antes de asumir que faltan datos. También verifica que abriste la tabla de la capa que querías consultar.')
heading('Comparar información con cuidado', 2)
para('Amplía las columnas si un identificador aparece cortado. Un encabezado abreviado o un valor parcialmente visible puede parecer igual a otro que en realidad es distinto. Busca siempre el nombre completo del campo y el valor íntegro.')
para('Como complemento didáctico, ordenar una columna te ayuda a recorrer los valores; filtrar limita los registros que ves. Son tareas diferentes y ninguna de las dos demuestra, por sí sola, que se haya modificado la fuente. Evita activar herramientas de edición si solo necesitas consultar.')
para('**Comprueba tu comprensión.** Si puedes identificar la capa abierta, distinguir una fila de una columna y explicar sus tres contadores, ya tienes la base para revisar los Excel del siguiente capítulo.')

newpage('11 Consultar los registros R1 y R2', '28:20 a 30:48')
para('El instructor incorpora dos libros Excel que complementan la información espacial. Se cargan como **tablas sin geometría**: aparecen en Capas y se pueden abrir, aunque no dibujen nuevos polígonos.')
steps([
    'En **Navegador**, localiza la carpeta de registros. En la grabación se ve como **Resgistros_1_2**. Despliega **18479-Morelia_R1.xlsx** y añade **18479-Morelia_R1**.',
    'Abre su tabla desde Capas. Recorre las columnas para familiarizarte con la estructura. La grabación muestra **2635** objetos.',
    'Repite con **18479-Morelia_R2.xlsx** y la tabla **18479-Morelia_R2**. Allí se muestran **3070** objetos.',
    'Maximiza la ventana si necesitas espacio. En R2 el video ordena de forma descendente una segunda columna de área; el nombre completo guardado en el proyecto es **AreaTerreno (m2)_1**.'
])
figure(1715, 'Los libros Excel y sus tablas desplegados en Navegador.', (0, 260, 445, 385), 3.5)
table(['Tabla', 'Campos que puedes reconocer'], [
    ('R1\n19 campos', 'Departamento, Municipio, NoPredial, Numero Predial, Nombre, TipoDocumento, Direccion, DestinoEconomico, AreaTerreno (m2), AreaConstruida (m2), Avaluo ($) y Vigencia, entre otros.'),
    ('R2\n46 campos', 'MatriculaInmobiliaria, ZonaFisica, ZonaEconomica, AreaTerreno (m2), Habitaciones, Baños, Locales, Pisos, Estrato, Uso, Puntaje y AreaConstruida (m2), con varios bloques repetidos.')
], [.8, 6.24], 10.5)
para('Los conteos proceden de la grabación y el número de campos se corrobora en servicios.qgz. Los nombres orientan la consulta, pero no sustituyen el diccionario de datos para interpretar códigos o reglas de negocio.')
para('En R2 hay campos con sufijos como **_1** y **_2**. Lee el encabezado completo antes de ordenar o comparar; no supongas que dos columnas de nombre parecido contienen el mismo bloque de información.')
para('**Resultado esperado.** Puedes abrir las dos tablas y recorrer sus campos. El tutorial todavía las consulta por separado: no ejecuta una unión automática con las capas de la GDB.')

newpage('Entender la relación entre el mapa y los registros', '28:20 a 30:48')
para('**Complemento didáctico del capítulo 11.** El instructor señala el **número predial** como referencia compartida entre la información espacial y los registros. Entender esa relación es el siguiente aprendizaje; realizar una unión requiere un procedimiento adicional.')
heading('Un identificador permite buscar correspondencias', 2)
para('Imagina un ejemplo ficticio en el que el predio **PREDIO_A** aparece en una capa de terrenos y en una tabla de registros. Si el identificador tiene el mismo significado y el mismo valor en ambas fuentes, permite buscar qué filas corresponden a ese objeto. PREDIO_A es solo una etiqueta de ejemplo y no representa el formato oficial del número predial.')
para('Los nombres de campo tampoco bastan para elegir la relación. En los Excel existen **NoPredial** y **Numero Predial**; en R_TERRENO, el proyecto registra **CODIGO** y **CODIGO_ANTERIOR**, entre otros. Antes de una futura unión, comprueba qué representa cada campo, cómo está almacenado y cuál corresponde al identificador de la otra fuente.')
heading('Qué revisar antes de una futura unión', 2)
bullet('Que ambos campos representen el mismo identificador y la misma versión de la información. Comparar una codificación anterior con una vigente puede producir ausencias de coincidencia.')
bullet('Que los valores estén completos. Revisa ceros iniciales, espacios, separadores y el tipo de dato. Un número mostrado de forma abreviada no sirve para comprobar una coincidencia íntegra.')
bullet('Cuántas filas existen por identificador. Si PREDIO_A aparece dos veces en una tabla, hay que entender por qué antes de decidir cómo incorporar esa información al mapa.')
bullet('Qué significan los campos y los bloques repetidos. La estructura por sí sola no explica las reglas que utiliza la entidad que entregó los registros.')
heading('Más filas no significa necesariamente más predios', 2)
para('R1 y R2 tienen más filas que R_TERRENO en la grabación. Esa diferencia no demuestra un error ni permite concluir qué tabla está duplicada. Son fuentes con estructuras diferentes y el tutorial no desarrolla una comparación de cobertura ni de correspondencias entre ellas.')
para('Por la misma razón, no deduzcas que cada fila de R1 o R2 corresponde a un polígono rural único. Verificar esa relación exige revisar los identificadores, los ámbitos incluidos y la organización de los registros.')
heading('Lo que has logrado en esta práctica', 2)
para('Ya sabes localizar y abrir las fuentes, reconocer sus campos y entender por qué un identificador común es relevante. Para continuar con una unión necesitarías una práctica específica que defina el campo correcto, la relación entre filas y la forma de comprobar las coincidencias.')

newpage('12 Guardar y recuperar tu proyecto')
para('**Complemento práctico.** En la secuencia revisada el mapa continúa como **Proyecto sin título** y no se muestra el guardado final. Este capítulo añade el cierre necesario para conservar tu trabajo. El archivo servicios.qgz se recibió como material complementario.')
heading('Guardar la configuración que preparaste', 2)
steps([
    'Entra a **Proyecto → Guardar como**. Elige tu carpeta de trabajo y escribe un nombre descriptivo, por ejemplo **Morelia_Practica_QGIS.qgz**.',
    'Conserva la GDB y los Excel en ubicaciones estables. El proyecto registra cómo llegar a las fuentes y cómo mostrar sus datos; no incorpora automáticamente una copia de esos archivos.',
    'Después de cambiar símbolos, orden o configuración, utiliza **Guardar** para actualizar el proyecto. Distingue esta acción de guardar ediciones en una fuente: aquí estás trabajando en la preparación y consulta del mapa.',
    'Cierra el proyecto y vuelve a abrir tu archivo QGZ. Comprueba que las capas se localizan, conservan sus símbolos y que la ortofoto responde si tienes internet.'
])
heading('Qué llevar si cambias de computador', 2)
para('Lleva el QGZ y las fuentes locales que utiliza: la carpeta GDB completa y los Excel. El acceso a la ortofoto seguirá dependiendo del servicio remoto. Un proyecto puede abrirse y, aun así, necesitar que indiques las nuevas rutas de los datos.')
para('Como organización de ejemplo, puedes mantener el proyecto dentro de Practica_Morelia y conservar una subcarpeta de datos con los insumos. La estructura concreta es una decisión tuya; lo importante es poder reconocer qué archivos necesita el proyecto y evitar moverlos sin revisar sus referencias.')
heading('Abrir el material suministrado', 2)
para('Para explorar el estado de referencia, utiliza **Proyecto → Abrir** y selecciona **servicios.qgz**. Sus fuentes apuntan a rutas del equipo de origen:')
bullet('GDB: **D:\\SIG - Catastro Caqueta\\SIG_Morelia\\18479.gdb**.')
bullet('Excel: **D:\\SIG - Catastro Caqueta\\SIG_Morelia\\Resgistros_1_2\\**. Se conserva el nombre de la carpeta tal como aparece en los materiales de referencia.')
para('Si no tienes esas carpetas, QGIS necesitará localizar tus copias. Guarda después una copia propia del proyecto para conservar las referencias corregidas. La siguiente página explica qué revisar cuando falten fuentes o la superposición no sea correcta.')

newpage('Recuperar las fuentes y revisar el SRC')
para('**Complemento técnico del capítulo 12.** Un archivo que no se encuentra y una capa ubicada incorrectamente son problemas distintos. Resuélvelos en ese orden: primero comprueba que la fuente esté disponible y después revisa su ubicación espacial.')
heading('Cuando QGIS no encuentra una fuente', 2)
steps([
    'Identifica qué capa no se pudo cargar y qué archivo o servicio utiliza. En servicios.qgz puede ser la GDB, uno de los Excel o la ortofoto remota.',
    'Localiza la copia que recibiste. Para capas de la GDB necesitas la carpeta completa y la capa interna correcta; para Excel, el libro y su tabla correspondiente.',
    'Utiliza la opción de reparación de fuentes que ofrezca QGIS al abrir el proyecto para indicar la ubicación actual. Si todavía no tienes el insumo, conservar el nombre de una ruta no permite reconstruir sus datos.',
    'Cuando las capas vuelvan a cargar, guarda una copia del proyecto y ábrela de nuevo para comprobar que las referencias quedaron resueltas.'
])
heading('Sistemas de referencia del proyecto suministrado', 2)
table(['Elemento', 'Sistema de referencia'], [
    ('Proyecto y capas de la GDB', 'ESRI:103599 — MAGNA-SIRGAS_CMT12'),
    ('Ortofoto del IGAC', 'EPSG:9377 — MAGNA-SIRGAS 2018 / Origen-Nacional'),
    ('Tablas R1 y R2', 'Sin geometría y sin SRC espacial')
], [2.6, 4.44], 10.5)
para('El SRC de una **capa** describe sus coordenadas de origen. El SRC del **proyecto** define cómo se representa el mapa en el lienzo. QGIS puede transformar la visualización para mostrar juntas capas con sistemas diferentes cuando sus referencias están correctamente definidas. Esto no reescribe por sí solo las fuentes.')
para('Revisa el SRC del proyecto en la barra inferior o en **Proyecto → Propiedades → SRC**. Para conocer el de una capa, consulta sus propiedades. Los códigos de la tabla describen el material suministrado y no son una instrucción para asignarlos a cualquier archivo que recibas.')
para('**Asignar un SRC** cambia cómo se interpretan las coordenadas existentes; **reproyectar** calcula coordenadas en otro sistema. No cambies un código solo para intentar que dos capas coincidan visualmente. Primero confirma los metadatos y la referencia original; si QGIS pide una transformación específica, revisa esa necesidad antes de continuar con un análisis.')

newpage('13 Resolver problemas frecuentes')
para('**Complemento práctico.** Empieza por una comprobación sencilla y observa el resultado antes de cambiar otra cosa. Así podrás identificar qué causaba el problema y evitarás acumular ajustes innecesarios.')
table(['Lo que observas', 'Comprobación inicial'], [
    ('No encuentras 18479.gdb', 'Busca en la ubicación donde recibiste los datos. Comprueba que la GDB esté completa y descomprimida.'),
    ('La capa está cargada pero el lienzo se ve vacío', 'Activa su casilla, usa Zoom a la capa y revisa si la fuente está disponible.'),
    ('La ortofoto tapa los polígonos', 'Arrastra la imagen debajo de las capas vectoriales en Capas.'),
    ('Los terrenos ocultan la imagen', 'Revisa el relleno de sus símbolos. Mantén transparente el interior y visible el contorno.'),
    ('Cambiaste un color y otra parte quedó igual', 'En Simbología, comprueba los componentes del símbolo: trama interior y contorno pueden ser distintos.'),
    ('El servicio REST no conecta', 'Revisa internet y la URL completa terminada en ImageServer. Abre esa dirección en el navegador para comprobar si responde.'),
    ('La imagen tarda o se ve por rectángulos', 'Espera al refresco y vuelve a una zona conocida de cobertura. Distingue la carga temporal de una ausencia persistente.'),
    ('Una capa aparece desplazada', 'Comprueba que sea la fuente esperada y revisa los SRC. No asignes un código nuevo sin conocer el original.'),
    ('El Excel no dibuja objetos', 'Es una tabla sin geometría. Ábrela desde Capas; cargarla no crea polígonos ni una unión.'),
    ('La tabla muestra menos filas', 'Revisa filtros, modo de visualización y versión de los insumos. Compara total y filtrados.'),
    ('El QGZ pide localizar archivos', 'Indica las copias actuales de la GDB y los Excel. Después guarda y vuelve a abrir una copia del proyecto.'),
    ('R1 aparece dos veces', 'servicios.qgz guarda dos referencias a R1. Para una consulta simple basta una; retira la duplicada desde Capas si no la necesitas.')
], [2.35, 4.69], 10)
heading('Si todavía no puedes leer el mapa', 2)
para('Oculta temporalmente los conjuntos que no estás revisando. Deja primero la ortofoto y una capa de terrenos, comprueba el contorno y añade las construcciones. Después incorpora las demás capas una a una. Esta prueba permite reconocer cuál oculta o confunde la información.')
para('Cuando un servicio no responde incluso desde el navegador, su disponibilidad puede depender del servidor. Conserva el proyecto y vuelve a comprobar el servicio cuando se restablezca el acceso; cambiar símbolos no solucionará una conexión caída.')

newpage('14 Repetir el recorrido con autonomía')
para('**Ejercicio de repaso.** Esta actividad reúne lo aprendido sin añadir operaciones de edición o análisis. Puedes realizarla con un proyecto nuevo y tus copias de los insumos. El propósito es que tomes decisiones sencillas y sepas explicar cada resultado.')
heading('Preparar una vista rural', 2)
steps([
    'Abre un proyecto nuevo y carga R_TERRENO y R_CONSTRUCCION desde 18479.gdb. Comprueba que puedes localizar cada fuente en Navegador y cada capa en Capas.',
    'Usa Zoom a la capa. Deja las construcciones encima de los terrenos y configura el contorno verde y la trama roja. Cambia solo la apariencia; no actives la edición.',
    'Añade la ortofoto mediante la conexión REST. Si la conexión ya está guardada, selecciónala, conecta y añade el recurso. Coloca la imagen al fondo.'
])
para('**Revisa tu resultado.** ¿Puedes reconocer un terreno, una construcción y la imagen que hay debajo? Si uno oculta al otro, identifica si la causa es el orden de dibujo, el relleno o el grosor de la trama.')
heading('Incorporar las otras fuentes', 2)
steps([
    'Añade las capas urbanas y los conjuntos informales. Contrasta sus símbolos con la tabla del capítulo 9 y comprueba los nombres antes de modificar cada capa.',
    'Abre la tabla de R_TERRENO. Identifica un encabezado y explica qué indican los contadores de total, filtrados y seleccionados. No copies datos personales para resolver el ejercicio.',
    'Carga R1 y R2. Localiza sus campos de identificación y distingue una tabla sin geometría de una capa de polígonos. Reconoce por qué cargar ambas no crea una relación automática.'
])
heading('Cerrar y volver a abrir', 2)
para('Guarda el proyecto con un nombre propio y vuelve a abrirlo. Debes recuperar las capas y los símbolos sin tener que repetir su configuración. Si falta una fuente, localízala y guarda otra vez antes de dar por terminada la práctica.')
heading('Explicar una diferencia sin apresurarte', 2)
para('Elige una zona donde el mapa y la imagen se puedan comparar. Si observas una diferencia, enumera qué revisarías: fecha del producto, cobertura, fuente cargada y SRC. El ejercicio consiste en plantear una comprobación razonada, no en declarar que un predio está mal o que una construcción tiene determinada condición jurídica.')
para('Puedes considerar completado el repaso cuando logres reconstruir esa vista y explicar dónde están los datos, cómo se representan y qué consultas puedes hacer sin modificar las fuentes.')

newpage('15 Comprobar lo aprendido')
para('La utilidad de esta práctica está en poder repetirla y reconocer qué estás haciendo. Utiliza la lista como una revisión personal. Si una afirmación todavía no se cumple, vuelve al capítulo correspondiente y repite esa parte con calma.')
heading('Instalación y manejo básico', 2)
bullet('QGIS abre y puedes identificar Navegador, Capas y el lienzo del mapa.')
bullet('Distingues entre seleccionar una capa, cambiar su visibilidad y acercarte a su extensión.')
bullet('Puedes localizar 18479.gdb y añadir sus capas sin manipular los archivos internos de la carpeta.')
heading('Representación del territorio', 2)
bullet('Los terrenos conservan contornos legibles y permiten ver la imagen a través de su interior.')
bullet('Las construcciones se diferencian mediante tramas y reconoces los conjuntos rurales y urbanos.')
bullet('La conexión REST utiliza la URL de la práctica y la ortofoto queda debajo de los vectores.')
bullet('Consideras la fecha y la resolución de la imagen antes de interpretar una diferencia con la GDB.')
heading('Consulta y conservación', 2)
bullet('Puedes abrir la tabla de R_TERRENO, recorrer sus campos e interpretar los contadores.')
bullet('Puedes abrir R1 y R2 y sabes que todavía son tablas consultadas por separado.')
bullet('Comprendes qué revisarías antes de relacionar registros mediante el número predial.')
bullet('Has guardado una copia propia del proyecto y comprobado que vuelve a abrir con sus fuentes.')
heading('Tres preguntas para afianzar el aprendizaje', 2)
para('**Si cambia el color de un terreno, ¿cambia su información?** No. En esta práctica cambias su representación, no sus atributos ni su geometría.')
para('**Si llevas solo el QGZ a otro computador, ¿llevas todos los datos?** No. Necesitas las fuentes locales y acceso al servicio remoto para recuperar el contenido completo de la vista.')
para('**Si R1 aparece en Capas, ¿ya quedó unida a los polígonos?** No. La tabla puede consultarse sin geometría y la unión sería una operación adicional que este video no desarrolla.')
para('Con esta base puedes continuar hacia prácticas de selección, consultas por atributos o relaciones entre tablas. Para hacerlo con datos catastrales, el siguiente paso es contar con los insumos completos y su documentación de campos.')

newpage('Fuentes y consultas')
heading('Material principal de esta guía', 2)
para('**Tutorial_1_Instalacion QGIS.mp4.** Fuente del recorrido, las acciones demostradas, las capturas y los conteos de registros. Las marcas de tiempo se redondean a segundos. El título del archivo menciona instalación, pero la grabación continúa con carga de datos, simbología, ortofoto y consulta de tablas.')
para('**servicios.qgz.** Material complementario utilizado para corroborar nombres, rutas, conexión REST, sistemas de referencia, campos y parámetros de simbología. Su configuración guardada se distingue de lo que se alcanza a ver o ejecutar en la grabación.')
para('Los ejemplos de identificadores y de organización de carpetas son didácticos. No reproducen registros personales ni sustituyen un diccionario de datos. Las capturas de tablas se limitan a su estructura o al panel de archivos.')
heading('Consultar las herramientas de QGIS', 2)
para('Los siguientes enlaces oficiales amplían las comprobaciones técnicas de la guía. La documentación corresponde a QGIS 3.44; algunas páginas pueden conservar fragmentos en inglés debido al avance de la traducción.')
link('QGIS — Descarga oficial', 'https://qgis.org/download/')
link('QGIS 3.44 — Apertura de fuentes de datos', 'https://docs.qgis.org/3.44/es/docs/user_manual/managing_data_source/opening_data.html')
link('QGIS 3.44 — Propiedades de capas vectoriales y simbología', 'https://docs.qgis.org/3.44/es/docs/user_manual/working_with_vector/vector_properties.html')
link('QGIS 3.44 — Trabajo con tablas de atributos', 'https://docs.qgis.org/3.44/es/docs/user_manual/working_with_vector/attribute_table.html')
link('QGIS 3.44 — Archivos de proyecto', 'https://docs.qgis.org/3.44/es/docs/user_manual/introduction/project_files.html')
link('QGIS 3.44 — Sistemas de referencia y proyecciones', 'https://docs.qgis.org/3.44/es/docs/user_manual/working_with_projections/working_with_projections.html')
heading('Consultar el producto del IGAC', 2)
link('IGAC — Colombia en Mapas', 'https://www.colombiaenmapas.gov.co/')
link('IGAC — Servicio REST de la ortofoto de Morelia', 'https://mapas2.igac.gov.co/image/rest/services/orto/orto18479morelia/ImageServer')
para('Las fechas y resoluciones citadas corresponden a la ficha revisada durante el tutorial. La disponibilidad de los servicios y la presentación del portal pueden cambiar. Cuando consultes otro producto, vuelve a comprobar su identificación, cobertura y metadatos.')
output = OUT / 'Manual_QGIS_Instalacion_y_Primeros_Pasos_Ampliado.docx'
DOC.save(output)
word_count = sum(len(p.text.split()) for p in DOC.paragraphs) + sum(len(c.text.split()) for t in DOC.tables for r in t.rows for c in r.cells)
print(output)
print(json.dumps({'paragraphs': len(DOC.paragraphs), 'tables': len(DOC.tables), 'figures': figcount, 'words': word_count, 'pages_planned': 26}, ensure_ascii=False))
