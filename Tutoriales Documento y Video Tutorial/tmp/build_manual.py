from pathlib import Path
import re
import json
from PIL import Image
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'output' / 'Manual_QGIS'
OUT.mkdir(parents=True, exist_ok=True)
ASSETS = ROOT / 'tmp' / 'manual_assets'
ASSETS.mkdir(parents=True, exist_ok=True)
DOC = Document()
sec = DOC.sections[0]
sec.page_width, sec.page_height = Inches(8.5), Inches(11)
sec.top_margin, sec.bottom_margin = Inches(.65), Inches(.65)
sec.left_margin, sec.right_margin = Inches(.72), Inches(.72)
sec.header_distance, sec.footer_distance = Inches(.28), Inches(.28)

styles = DOC.styles
for name in ['Normal', 'Title', 'Subtitle', 'Heading 1', 'Heading 2', 'Heading 3', 'Caption', 'Header', 'Footer', 'List Bullet', 'List Number']:
    s = styles[name]
    s.font.name = 'Calibri'
    s.font.color.rgb = RGBColor(0,0,0)
    rf = s.element.get_or_add_rPr()
    for child in list(rf):
        if child.tag == qn('w:color'):
            for attr in list(child.attrib):
                if 'theme' in attr.lower(): del child.attrib[attr]
    if name in ['Title','Subtitle','Heading 1','Heading 2','Heading 3']:
        pp = s.element.find(qn('w:pPr'))
        if pp is not None:
            for child in list(pp):
                if child.tag in [qn('w:pBdr'), qn('w:shd')]: pp.remove(child)
styles['Normal'].font.size = Pt(11)
styles['Normal'].paragraph_format.line_spacing = 1.08
styles['Normal'].paragraph_format.space_after = Pt(7)
styles['Title'].font.size = Pt(27)
styles['Title'].font.bold = True
styles['Title'].paragraph_format.space_after = Pt(8)
styles['Subtitle'].font.size = Pt(15)
styles['Subtitle'].paragraph_format.space_after = Pt(10)
styles['Heading 1'].font.size = Pt(19)
styles['Heading 1'].font.bold = True
styles['Heading 1'].paragraph_format.space_before = Pt(0)
styles['Heading 1'].paragraph_format.space_after = Pt(8)
styles['Heading 2'].font.size = Pt(12)
styles['Heading 2'].font.bold = True
styles['Heading 2'].paragraph_format.space_before = Pt(9)
styles['Heading 2'].paragraph_format.space_after = Pt(5)
styles['Caption'].font.size = Pt(9)
styles['Caption'].font.italic = False
styles['Caption'].paragraph_format.space_after = Pt(9)
styles['Caption'].paragraph_format.line_spacing = 1
for name in ['List Bullet','List Number']:
    styles[name].font.size = Pt(11)
    styles[name].paragraph_format.space_after = Pt(5)
    styles[name].paragraph_format.line_spacing = 1.05

DOC.core_properties.title = 'Manual de instalación y primeros pasos en QGIS'
DOC.core_properties.subject = 'Tutorial escrito de QGIS 3.44.15 y práctica catastral de Morelia Caquetá'
DOC.core_properties.author = 'José Castillo Ospina'
DOC.core_properties.keywords = 'QGIS, Morelia, catastro, IGAC, geodatabase, ortofoto'
DOC.core_properties.comments = 'Elaborado a partir del video Tutorial_1_Instalacion QGIS.mp4 y del proyecto servicios.qgz.'

header = sec.header.paragraphs[0]
header.text = 'QGIS 3.44   |   Manual de instalación y primeros pasos'
header.style = styles['Header']
header.runs[0].font.size = Pt(8)
footer = sec.footer.paragraphs[0]
footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
footer.add_run('Manual de consulta   ·   Página ').font.size = Pt(9)
fld = OxmlElement('w:fldSimple'); fld.set(qn('w:instr'), 'PAGE')
footer._p.append(fld)

def rich(p, text):
    for i, part in enumerate(re.split(r'\*\*(.*?)\*\*', text)):
        r = p.add_run(part)
        r.bold = bool(i % 2)
    return p

def para(text='', style=None):
    return rich(DOC.add_paragraph(style=style), text)

def heading(text, level=1):
    return DOC.add_heading(text, level=level)

def newpage(title, time=None):
    h=heading(title)
    h.paragraph_format.page_break_before=True
    if time:
        p=para('Referencia en el video   '+time)
        p.runs[0].font.size=Pt(9)
        p.paragraph_format.space_after=Pt(9)

def steps(items):
    for idx, text in enumerate(items, 1):
        p=para(f'**{idx}.**  '+text)
        p.paragraph_format.left_indent=Inches(.18)
        p.paragraph_format.first_line_indent=Inches(-.18)
        p.paragraph_format.space_after=Pt(6)

def bullet(text): return para(text, 'List Bullet')

def link(label, url):
    p=DOC.add_paragraph()
    h=OxmlElement('w:hyperlink')
    h.set(qn('r:id'), p.part.relate_to(url,RT.HYPERLINK,is_external=True))
    r=OxmlElement('w:r'); rp=OxmlElement('w:rPr')
    color=OxmlElement('w:color'); color.set(qn('w:val'),'1F4E79'); rp.append(color)
    u=OxmlElement('w:u'); u.set(qn('w:val'),'single'); rp.append(u)
    r.append(rp); t=OxmlElement('w:t'); t.text=label; r.append(t); h.append(r); p._p.append(h)
    return p

def table(headers, rows, widths, size=10):
    t=DOC.add_table(rows=1, cols=len(headers))
    t.alignment=WD_TABLE_ALIGNMENT.CENTER
    t.autofit=False
    for i,w in enumerate(widths):
        t.columns[i].width=Inches(w)
    for cells, data, ishead, ridx in [(t.rows[0].cells,headers,True,0)]+[(t.add_row().cells,row,False,i+1) for i,row in enumerate(rows)]:
        for i,(cell,txt) in enumerate(zip(cells,data)):
            cell.width=Inches(widths[i]); cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            tcpr=cell._tc.get_or_add_tcPr()
            borders=OxmlElement('w:tcBorders')
            for e in ['top','left','bottom','right']:
                b=OxmlElement('w:'+e); b.set(qn('w:val'),'single'); b.set(qn('w:sz'),'4'); b.set(qn('w:color'),'D9D9D9'); borders.append(b)
            tcpr.append(borders)
            margins=OxmlElement('w:tcMar')
            for e,val in [('top','85'),('bottom','85'),('left','100'),('right','100')]:
                el=OxmlElement('w:'+e); el.set(qn('w:w'),val); el.set(qn('w:type'),'dxa'); margins.append(el)
            tcpr.append(margins)
            shd=OxmlElement('w:shd'); shd.set(qn('w:fill'),'DCE6F1' if ishead else ('F5F7F9' if ridx%2==0 else 'FFFFFF')); tcpr.append(shd)
            p=cell.paragraphs[0]; p.paragraph_format.space_after=Pt(0); p.paragraph_format.line_spacing=1.04
            rich(p,str(txt))
            for r in p.runs: r.font.size=Pt(size); r.bold=ishead or r.bold
        pr=t.rows[ridx]._tr.get_or_add_trPr()
        cant=OxmlElement('w:cantSplit'); pr.append(cant)
        if ishead:
            repeat=OxmlElement('w:tblHeader'); pr.append(repeat)
    para('').paragraph_format.space_after=Pt(1)
    return t

figcount=0
def figure(t, caption, crop=None, width=7.04):
    global figcount
    figcount+=1
    source=ROOT/'tmp'/'video'/f'frame_{t:04d}.jpg'
    im=Image.open(source)
    if crop: im=im.crop(crop)
    target=ASSETS/f'fig_{figcount:02d}.jpg'
    im.save(target,quality=94)
    p=DOC.add_paragraph(); p.paragraph_format.space_after=Pt(4); p.paragraph_format.keep_with_next=True
    p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(target),width=Inches(width))
    c=para(f'Figura {figcount}. {caption} Video {t//60:02d}:{t%60:02d}.','Caption')
    return c

para('Manual de instalación y primeros pasos en QGIS','Title')
para('Práctica catastral de Morelia Caquetá','Subtitle')
para('**Versión de referencia** QGIS 3.44.15 Solothurn en Windows\n**Fuente principal** Tutorial_1_Instalacion QGIS.mp4\n**Duración del video** 30 minutos y 48 segundos\n**Fecha del manual** 11 de octubre de 2026')
heading('Qué aprenderá',2)
para('Este manual permite seguir por escrito la instalación de QGIS y la primera exploración de información catastral de Morelia, Caquetá. Está dirigido a personas que empiezan a usar un sistema de información geográfica en labores de consulta y apoyo a la gestión territorial.')
para('Al terminar podrá abrir datos de una geodatabase, distinguir terrenos y construcciones mediante símbolos, consultar una ortofoto del IGAC y revisar tablas de atributos y registros en Excel.')
heading('Antes de empezar',2)
bullet('Disponga de un computador con Windows de 64 bits, acceso a internet para descargar QGIS y consultar la ortofoto, y permisos para instalar programas.')
bullet('Tenga disponibles la geodatabase **18479.gdb** y los archivos **18479-Morelia_R1.xlsx** y **18479-Morelia_R2.xlsx** si desea repetir la práctica completa.')
para('**Disponibilidad de los insumos.** La carpeta revisada contiene el video y **servicios.qgz**. La GDB y los Excel aparecen referenciados en ese proyecto, pero sus datos no están incluidos en esta carpeta ni dentro del QGZ. Puede realizar la instalación antes de conseguirlos.')
heading('Cómo usar el manual',2)
para('Siga los capítulos en orden o consulte el índice de la página siguiente. Las marcas de tiempo permiten volver al momento correspondiente del video. Las capturas se extrajeron de la grabación; algunos diálogos se recortaron para facilitar su lectura.')
para('Los apartados marcados como **complemento práctico** añaden comprobaciones o acciones de cierre. Se distinguen de las operaciones demostradas por el instructor.')

newpage('Contenido y términos básicos')
table(['Capítulo','Página','Video aproximado'],[
('Descargar QGIS','3','01:31 a 05:35'),('Instalar y abrir el programa','4','05:35 a 08:40'),
('Reconocer la interfaz','5','08:40 a 11:40'),('Cargar las capas rurales','6','11:40 a 12:55'),
('Configurar la simbología rural','7','12:55 a 15:30'),('Localizar la ortofoto en el IGAC','8','16:25 a 18:45'),
('Crear la conexión REST','9','18:45 a 20:05'),('Superponer las capas urbanas','10','20:05 a 22:40'),
('Diferenciar terrenos y construcciones','11','22:40 a 27:20'),('Consultar atributos de una capa','12','27:20 a 28:20'),
('Abrir los registros R1 y R2','13','28:20 a 30:48'),('Guardar y recuperar el proyecto','14','Complemento práctico'),
('Resolver problemas frecuentes','15','Complemento práctico'),('Comprobación final y fuentes','16','Consulta')
],[4.55,.6,1.89],10)
heading('Términos que aparecen en la práctica',2)
para('**Capa.** Conjunto de información que se incorpora al mapa o al panel Capas. Una capa vectorial representa objetos mediante puntos, líneas o polígonos; una tabla sin geometría puede consultarse sin dibujarse en el mapa.')
para('**Geodatabase o GDB.** Carpeta de base de datos geográfica. En esta práctica, 18479.gdb contiene grupos de datos rurales y urbanos.')
para('**Simbología.** Colores, contornos y tramas que controlan la apariencia de los objetos. Cambiar el símbolo no modifica su geometría ni los valores de sus atributos.')
para('**Ortofoto u ortoimagen.** Imagen aérea corregida geométricamente que se utiliza aquí como referencia visual del territorio.')
para('**Servicio REST.** Dirección de un servidor desde la cual QGIS solicita información por internet. En este tutorial se consulta una imagen del IGAC.')
para('**SRC o CRS.** Sistema de referencia de coordenadas. Permite ubicar y superponer correctamente las distintas capas.')

newpage('1 Descargar QGIS','01:31 a 05:35')
para('El instructor utiliza la rama de soporte prolongado **LTR 3.44**, cuyo instalador en la grabación corresponde a **QGIS 3.44.15 Solothurn**. Para reproducir las pantallas, tome esta versión como referencia.')
steps([
'Abra el navegador y entre al sitio oficial **qgis.org**. Seleccione **Descargar** o **Download**.',
'En la página de descarga, seleccione **Windows**. Si aparece la invitación a donar, continúe a la descarga; la donación es voluntaria.',
'Elija **Descargar LTR 3.44**, bajo la opción de liberación a largo plazo. En el video se usa el instalador autónomo para Windows.',
'Espere a que termine la descarga. Abra la carpeta **Descargas** y ubique el instalador. En la grabación se identifica como **QGIS-OSGeo4W-3.44.15-2.msi**.'
])
figure(275,'Selección de la versión LTR en la página oficial de descarga.',(1020,260,1645,790),4.9)
para('**Comprobación.** El archivo debe estar descargado por completo antes de ejecutarlo. La duración de la descarga depende de la conexión a internet.')
para('**Nota sobre versiones.** La página puede ofrecer otras versiones cuando consulte este manual. Los números anteriores describen el video y no constituyen una indicación permanente de cuál será la versión más reciente.')
link('Abrir la página oficial de descarga de QGIS','https://qgis.org/download/')

newpage('2 Instalar y abrir QGIS','05:35 a 08:40')
steps([
'Haga doble clic en el instalador descargado. Espere a que se prepare el asistente de Windows Installer.',
'En la bienvenida del asistente, pulse **Next**.',
'Lea los términos de licencia. Para continuar, marque **I accept the terms in the License Agreement** y pulse **Next**.',
'En **Destination Folder**, conserve la carpeta predeterminada si no requiere otra ubicación. En el video es **C:\\Program Files\\QGIS 3.44.15\\**.',
'Deje activadas las opciones **Create desktop shortcuts** y **Create start menu shortcuts** si desea esos accesos. Pulse **Next** y después **Install**. Si Windows solicita permiso de administrador para instalar, autorice el instalador que descargó del sitio oficial.',
'Espere a que termine el asistente y pulse **Finish**. Abra **QGIS Desktop 3.44.15** desde Inicio o desde el acceso creado.',
'Espere a que se cargue QGIS. Si aparece una ventana informativa inicial, ciérrela para acceder al área de trabajo.'
])
figure(365,'Carpeta de destino y accesos directos del instalador.',(705,193,1205,584),4.8)
para('**Comprobación.** Se abre la ventana principal de QGIS con sus menús, paneles laterales y un lienzo de mapa vacío. El programa puede conservar configuraciones o rutas de una instalación anterior.')

newpage('3 Reconocer la interfaz','08:40 a 11:40')
para('Antes de cargar datos, identifique las zonas de trabajo. En el equipo del instructor hay carpetas, conexiones y herramientas ya configuradas; su instalación puede mostrar un contenido distinto.')
figure(635,'Panel Navegador, panel Capas y lienzo de mapa al inicio de la práctica.',(0,0,1918,1030),7.04)
table(['Zona','Para qué se utiliza'],[
('Menús y barras superiores','Abrir proyectos, cargar datos, navegar y consultar herramientas.'),
('Navegador','Explorar unidades, carpetas, bases de datos y conexiones.'),
('Capas','Activar, ocultar, ordenar y seleccionar los datos cargados.'),
('Lienzo del mapa','Visualizar y recorrer la información geográfica.'),
('Barra inferior','Consultar la escala, las coordenadas y el SRC del proyecto.')
],[1.55,5.49],10.5)
steps(['En **Navegador**, despliegue la unidad donde guardó sus archivos. Busque la carpeta que contiene los datos de Morelia.',
'Use la rueda del ratón para acercarse o alejarse del mapa y la herramienta **Desplazar mapa** para recorrerlo.',
'En **Capas**, marque o desmarque la casilla de una capa para cambiar su visibilidad. Seleccione su nombre antes de abrir sus propiedades o su tabla.'])
para('**Si falta un panel.** Como complemento práctico, puede activarlo desde **Ver → Paneles**, seleccionando Navegador o Capas.')

newpage('4 Cargar las capas rurales','11:40 a 12:55')
para('La práctica utiliza **18479.gdb**, una geodatabase del municipio de Morelia. La ubicación visible en el video pertenece al computador del instructor; en su equipo debe buscar la carpeta donde recibió los insumos.')
steps([
'En **Navegador**, localice y despliegue **18479.gdb**. Abra el grupo **RURAL**.',
'Localice **R_TERRENO**. Arrastre la capa al lienzo o al panel **Capas**. Espere a que se dibujen los polígonos.',
'Repita el procedimiento con **R_CONSTRUCCION**. El instructor también carga **R_UNIDAD** para explorarla y después la retira del panel.',
'Verifique que **R_CONSTRUCCION** quede sobre **R_TERRENO** en el orden de dibujo. Acerque el mapa para distinguir las construcciones.',
'Si desea repetir la exploración de R_UNIDAD, cárguela de forma temporal. Para continuar con la vista del tutorial, quite esa capa del proyecto cuando termine de revisarla.'
])
figure(725,'Momento de carga de R_CONSTRUCCION desde RURAL antes de ordenar las capas.',(0,150,1200,900),6.5)
para('**Comprobación.** R_TERRENO y R_CONSTRUCCION aparecen en Capas y se visualizan en el mapa. Los colores iniciales pueden diferir: QGIS asigna símbolos al cargar las capas.')
para('**Complemento práctico.** Si el lienzo queda vacío, haga clic derecho sobre R_TERRENO y seleccione **Zoom a la capa**. Quite capas mediante el panel de QGIS; no borre la carpeta GDB.')

newpage('5 Configurar la simbología rural','12:55 a 15:30')
para('El objetivo visual es mostrar los límites de los terrenos y distinguir las construcciones. Un relleno opaco en los terrenos puede ocultar los elementos que están debajo.')
steps([
'Haga doble clic en **R_TERRENO** o abra **Propiedades** desde su menú contextual. Seleccione **Simbología**.',
'Mantenga el renderizador **Símbolo Único**. En la galería, elija el estilo de contorno verde **outline green** o configure un contorno verde con relleno transparente. Pulse **Aplicar** o **Aceptar**.',
'Abra la simbología de **R_CONSTRUCCION**. Seleccione una trama diagonal de la galería y cambie su color a rojo. El video también revisa las capas de línea que componen el símbolo.',
'Aplique el estilo y cierre el diálogo. Acerque el mapa hasta ver los límites de los terrenos y las tramas de las construcciones.',
'Si aún está cargada **R_UNIDAD**, retírela del panel para continuar con las dos capas principales de este tramo.'
])
figure(905,'Terrenos con contorno verde y construcciones con trama roja.',(440,120,1918,1005),7.04)
para('**Comprobación.** El interior de los terrenos deja ver el fondo y las construcciones se distinguen en rojo. Una trama demasiado gruesa o densa puede ocultar el detalle al alejar el mapa.')
para('**Parámetro posterior.** Cerca del minuto 27:05 se ajusta el contorno verde de R_TERRENO a **0,70 mm**. El proyecto servicios.qgz conserva ese valor.')

newpage('6 Localizar la ortofoto del IGAC','16:25 a 18:45')
para('El instructor abre **Colombia en Mapas**, el portal de información geoespacial del IGAC, para encontrar una imagen de referencia de Morelia.')
steps([
'Abra **colombiaenmapas.gov.co** en el navegador.',
'Use los **Filtros** por entidad territorial para localizar **Morelia, Caquetá**. Consulte los productos disponibles para ese municipio.',
'Busque la ficha **Ortoimagen Departamento de Caquetá Municipio de Morelia Resolución 50 cm Año 2022**. En la lista también aparece una ortoimagen de la cabecera municipal de 10 cm y año 2021; revise la ficha para elegir el producto de la práctica.',
'Añada o visualice el producto en el mapa del portal. Revise su cobertura y sus metadatos.',
'En la ficha, desplácese hasta **Enlaces de interés**. Abra **Servicio (REST)** y copie la dirección completa de la página del servicio.'
])
figure(1110,'Ficha de la ortoimagen y enlaces del servicio REST.',(0,550,530,1025),3.7)
para('**Comprobación.** El servicio que se abre para esta práctica termina en **orto/orto18479morelia/ImageServer**. Se utilizará en QGIS en el siguiente capítulo.')
link('Abrir Colombia en Mapas','https://www.colombiaenmapas.gov.co/')

newpage('7 Crear la conexión REST en QGIS','18:45 a 20:05')
steps([
'Vuelva a QGIS. Abra el **Administrador de fuentes de datos** y seleccione **Servidor REST ArcGIS**. Pulse **Nuevo**.',
'En **Nombre**, escriba **Ortofoto_Rural_Morelia_Caqueta**. Este nombre identifica la conexión en su equipo.',
'En **URL**, pegue la dirección completa del servicio que se indica debajo. En la grabación se utiliza **Sin Autenticación**; los campos opcionales conservan sus valores predeterminados.',
'Pulse **Aceptar**. Seleccione la conexión creada y pulse **Conectar**.',
'Seleccione el recurso **orto/orto18479morelia** y pulse **Añadir**. Cierre el administrador cuando la capa aparezca en el proyecto.'
])
para('**URL del servicio de la práctica**')
link('https://mapas2.igac.gov.co/image/rest/services/orto/orto18479morelia/ImageServer','https://mapas2.igac.gov.co/image/rest/services/orto/orto18479morelia/ImageServer')
figure(1165,'Conexión con el nombre, la URL completa y la opción Sin Autenticación.',(635,303,1495,850),6.8)
para('**Comprobación.** La imagen aparece en el panel Capas. El administrador identifica el SRC de la ortofoto como **EPSG:9377 — MAGNA-SIRGAS 2018 / Origen-Nacional**.')
para('La capa se consulta por internet. Añadir este servicio al proyecto no equivale a descargar una copia completa de la ortofoto.')

newpage('8 Superponer la información urbana','20:05 a 22:40')
steps([
'En **Capas**, arrastre **orto/orto18479morelia** a la parte inferior del orden de dibujo. Mantenga los terrenos y las construcciones por encima de la imagen.',
'Acerque y desplace el mapa. Espere a que el servicio actualice la imagen después de cada cambio de vista.',
'En **Navegador → 18479.gdb**, abra el grupo **URBANO**. Cargue **U_TERRENO**, **U_TERRENO_INFORMAL**, **U_CONSTRUCCION** y **U_CONSTRUCCION_INFORMAL**.',
'Desde el grupo **RURAL**, añada también **R_TERRENO_INFORMAL** y **R_CONSTRUCCION_INFORMAL**.',
'Ordene las capas para poder consultar sus contornos y construcciones. Ajuste su simbología siguiendo el capítulo siguiente.'
])
figure(1325,'Capas rurales y urbanas añadidas sobre la ortofoto antes del ajuste final de símbolos.',(0,590,1918,1005),7.04)
para('**Comprobación.** El panel contiene ocho capas vectoriales de terrenos y construcciones, además de la ortofoto. Los prefijos **R_** y **U_** identifican aquí las capas rurales y urbanas.')
para('**Durante la carga.** En la grabación la ortofoto se ve en rectángulos mientras cambia la extensión del mapa. Espere a que termine el refresco antes de interpretar ese estado como un fallo de cobertura.')
para('**Fecha de la imagen.** La ficha del producto muestra insumos de febrero de 2022 y elaboración en junio de 2024. El instructor advierte que algunas construcciones de la base pueden no aparecer todavía en la imagen.')
para('**Sobre la informalidad.** Conserve las capas que llevan el sufijo _INFORMAL como conjuntos separados y siga la clasificación de los insumos. La apariencia de una construcción en la imagen no basta para reclasificar su condición catastral.')

newpage('9 Diferenciar terrenos y construcciones','22:40 a 27:20')
para('Configure cada capa desde **Propiedades → Simbología**. El instructor utiliza contornos para los terrenos y tramas para las construcciones. Así conserva visible la ortofoto.')
table(['Capa','Apariencia de referencia'],[
('R_TERRENO','Contorno verde y relleno transparente'),
('R_TERRENO_INFORMAL','Contorno rojo'),
('R_CONSTRUCCION','Trama diagonal roja'),
('R_CONSTRUCCION_INFORMAL','Patrón discontinuo verde'),
('U_TERRENO','Contorno azul y relleno transparente'),
('U_TERRENO_INFORMAL','Contorno amarillo'),
('U_CONSTRUCCION','Trama diagonal roja'),
('U_CONSTRUCCION_INFORMAL','Trama cruzada gris oscura')
],[2.9,4.14],10.5)
steps([
'Seleccione la capa y abra **Simbología**. En los terrenos, use un símbolo sin relleno visible y cambie el color del contorno.',
'En las construcciones, seleccione una trama diagonal o cruzada de la galería. En el video se ven los estilos **hashed black \\** y **hashed black X**; después se ajustan sus colores.',
'Pulse **Aplicar** para revisar el resultado en el mapa y **Aceptar** para cerrar. Repita la operación con las capas restantes.',
'Al finalizar, ajuste **R_TERRENO** a una anchura de contorno de **0,70 mm**, tal como se ve cerca de 27:05.'
])
figure(1565,'Resultado de las tramas y contornos sobre la imagen de referencia.',(440,120,1918,600),7.04)
para('**Comprobación.** Se distinguen terrenos, construcciones y conjuntos informales sin cubrir por completo la ortofoto. La tabla describe el resultado visual del video y está corroborada en el proyecto suministrado.')

newpage('10 Consultar los atributos de una capa','27:20 a 28:20')
para('Una capa contiene geometrías y una tabla de datos asociada. En este tramo se consulta **R_TERRENO** para revisar la información descriptiva de los predios.')
steps([
'Seleccione **R_TERRENO** en el panel Capas.',
'Haga clic derecho y elija **Abrir tabla de atributos**. También puede usar el botón de tabla con la capa seleccionada.',
'Revise los encabezados de las columnas. Desplace horizontalmente la tabla para consultar los campos que quedan fuera de la ventana.',
'Observe el total de objetos, los objetos filtrados y los seleccionados. El tutorial muestra **1292** objetos totales y filtrados, con **0** seleccionados.',
'Cierre la tabla para volver al mapa. La consulta de sus valores no requiere activar la edición.'
])
figure(1655,'Encabezados y contadores de la tabla R_TERRENO. El recorte muestra la estructura y omite los registros.',(10,72,1350,154),7.04)
heading('Cómo interpretar lo que ve',2)
para('Cada fila corresponde a un objeto de la capa. Cada columna corresponde a un campo o atributo. Al desplazar la tabla cambia qué campos se ven; no cambia la geometría del mapa.')
para('**Comprobación.** La ventana abierta corresponde a R_TERRENO y sus columnas se pueden recorrer. Los conteos anteriores describen los datos del video; pueden variar si recibe una versión distinta de la base.')
heading('Complemento práctico',2)
para('Si un identificador predial se muestra incompleto, amplíe la columna antes de compararlo con otro registro. Utilice los nombres de campo y el valor completo para evitar confundir columnas parecidas.')
para('Si solo aparecen algunos registros, revise los filtros y el selector de visualización de la tabla. Compare el contador de objetos filtrados con el total.')

newpage('11 Abrir los registros R1 y R2','28:20 a 30:48')
steps([
'En **Navegador**, abra la carpeta de los registros. En el video se ve como **Registros_1_2**.',
'Despliegue **18479-Morelia_R1.xlsx** y añada su tabla **18479-Morelia_R1** al panel Capas.',
'Abra la tabla desde su menú contextual. Recorra sus columnas para consultar los campos. La grabación muestra **2635** objetos.',
'Repita el proceso con **18479-Morelia_R2.xlsx** y su tabla **18479-Morelia_R2**. La grabación muestra **3070** objetos.',
'Maximice la tabla si necesita más espacio y desplácese horizontalmente. En R2 se muestra un ordenamiento descendente por una segunda columna de área de terreno. El proyecto conserva su nombre completo como **AreaTerreno (m2)_1**.'
])
table(['Tabla','Campos de ejemplo que se consultan'],[
('R1','Departamento, Municipio, NoPredial, Numero Predial, Nombre, TipoDocumento, Direccion, DestinoEconomico, AreaTerreno (m2), AreaConstruida (m2), Avaluo ($) y Vigencia.'),
('R2','MatriculaInmobiliaria, ZonaFisica, ZonaEconomica, AreaTerreno (m2), Habitaciones, Baños, Locales, Pisos, Estrato, Uso, Puntaje y AreaConstruida (m2).')
],[.55,6.49],10.5)
figure(1715,'Archivos Excel y sus tablas disponibles en el panel Navegador.',(0,260,445,385),3.5)
para('**Comprobación.** Puede abrir ambas tablas aunque no dibujen polígonos. Se cargan como registros sin geometría; el tutorial las consulta por separado. No se demuestra una unión automática con los predios de la GDB.')
para('**Relación entre fuentes.** El instructor señala el número predial como referencia compartida con la base espacial. Una unión por ese identificador requeriría un procedimiento adicional que este tutorial no desarrolla.')

newpage('12 Guardar y recuperar el proyecto')
para('**Complemento práctico.** Este capítulo completa el flujo de trabajo. En la secuencia revisada el mapa continúa como Proyecto sin título; no se muestra el guardado final. El archivo servicios.qgz se recibió como material adicional y se utiliza para corroborar configuración y nombres.')
heading('Guardar su trabajo',2)
steps([
'Seleccione **Proyecto → Guardar como**. Elija una carpeta de trabajo y escriba un nombre descriptivo, por ejemplo **Morelia_Practica_QGIS.qgz**.',
'Conserve la geodatabase y los Excel en una ubicación estable. El archivo de proyecto guarda referencias a esas fuentes y la configuración del mapa.',
'Después de cambiar símbolos, orden de capas o vista, pulse **Guardar**. Cierre y vuelva a abrir su proyecto para comprobar que las fuentes se localizan.'
])
heading('Usar el proyecto suministrado',2)
para('Abra **servicios.qgz** mediante **Proyecto → Abrir** si desea revisar el estado guardado. Sus rutas corresponden al equipo de origen:')
bullet('GDB: **D:\\SIG - Catastro Caqueta\\SIG_Morelia\\18479.gdb**.')
bullet('Excel: carpeta **D:\\SIG - Catastro Caqueta\\SIG_Morelia\\Resgistros_1_2\\**. Esta es la escritura almacenada en el proyecto, aunque el panel del video muestra Registros_1_2.')
para('Si esas rutas no existen en su equipo, QGIS necesitará que indique dónde están sus copias de los archivos. El QGZ no contiene la GDB, los registros Excel ni una copia completa de la imagen remota.')
heading('Sistemas de referencia corroborados',2)
table(['Elemento','Sistema guardado'],[
('Proyecto y capas de la GDB','ESRI:103599 — MAGNA-SIRGAS_CMT12'),
('Ortofoto del IGAC','EPSG:9377 — MAGNA-SIRGAS 2018 / Origen-Nacional'),
('Tablas Excel R1 y R2','Sin geometría y sin SRC espacial')
],[2.6,4.44],10.5)
para('**Comprobación.** Las capas se dibujan y el proyecto se abre sin referencias pendientes. Si dos fuentes se superponen mal, revise el SRC definido de cada una antes de modificarlo; asignar otro código no equivale a reproyectar sus datos.')

newpage('13 Resolver problemas frecuentes')
para('**Complemento práctico.** Use estas comprobaciones cuando el resultado difiera de lo esperado. Revise primero la capa seleccionada, su visibilidad y su ubicación en el orden de dibujo.')
table(['Situación','Qué revisar'],[
('No aparece 18479.gdb','Compruebe que recibió la carpeta GDB completa, que está descomprimida y que busca en la ubicación correcta desde Navegador.'),
('Cargó la capa pero el mapa está vacío','Active su casilla y use Zoom a la capa. Compruebe que la fuente no esté marcada como no disponible.'),
('La ortofoto tapa los polígonos','Mueva la ortofoto al fondo del panel Capas; deje los vectores encima.'),
('Un terreno tapa la ortofoto','Abra Simbología y use relleno transparente o un símbolo solo de contorno.'),
('El servicio REST no conecta','Compruebe internet y la URL completa, terminada en ImageServer. Pruebe abrir la dirección en el navegador.'),
('La imagen aparece incompleta al desplazarse','Espere a que se actualice el servicio. Luego compruebe que la vista esté dentro de su cobertura.'),
('Capas que deberían coincidir aparecen desplazadas','Revise el SRC de las fuentes y del proyecto. No asigne un código distinto solo para forzar una coincidencia.'),
('La tabla Excel no dibuja nada','Es una tabla sin geometría. Ábrala desde Capas para consultar sus registros.'),
('Aparecen menos filas de las esperadas','Revise filtros, selección y versión de los insumos. Compare objetos totales y filtrados.'),
('servicios.qgz pide reparar las fuentes','Localice sus copias de 18479.gdb y de los dos Excel. Actualice las referencias y guarde una copia del proyecto.'),
('R1 aparece duplicada','El proyecto suministrado contiene dos referencias a R1. Para una consulta simple basta una; si retira la duplicada, hágalo desde Capas.')
],[2.05,4.99],10.5)
heading('Volver a una vista legible',2)
para('Oculte temporalmente las capas que no está revisando. Encienda primero la ortofoto y una capa de terrenos, confirme el resultado y añada las construcciones. Este orden facilita identificar qué capa provoca el problema visual.')

newpage('14 Comprobación final y fuentes')
heading('Lista de comprobación',2)
for s in [
'QGIS abre correctamente y puede identificar los paneles Navegador y Capas.',
'18479.gdb se localiza y sus capas rurales y urbanas se pueden cargar.',
'R_TERRENO y U_TERRENO permiten ver la imagen a través de su relleno.',
'Las construcciones se distinguen mediante tramas y colores.',
'La conexión Ortofoto_Rural_Morelia_Caqueta contiene la URL correcta.',
'La ortofoto se sitúa debajo de las capas vectoriales.',
'Puede abrir la tabla de atributos de R_TERRENO y recorrer sus columnas.',
'Puede consultar R1 y R2 como tablas sin geometría.',
'Ha guardado su propia copia del proyecto y puede volver a abrirla.'
]: bullet(s)
heading('Material utilizado',2)
para('**Tutorial_1_Instalacion QGIS.mp4.** Fuente principal de los pasos, el orden de trabajo, las capturas y los conteos de registros. Las marcas de tiempo se redondean a segundos y los intervalos del índice son aproximados.')
para('**servicios.qgz.** Fuente complementaria para corroborar nombres de capas, fuentes, URL de la ortofoto, SRC y configuración guardada. No se atribuye su creación a un paso que no aparece en la grabación.')
heading('Enlaces de consulta',2)
link('QGIS — Descarga oficial','https://qgis.org/download/')
link('QGIS 3.44 — Manual de usuario sobre apertura de datos','https://docs.qgis.org/3.44/es/docs/user_manual/managing_data_source/opening_data.html')
link('IGAC — Colombia en Mapas','https://www.colombiaenmapas.gov.co/')
link('IGAC — Servicio REST de la ortofoto de Morelia','https://mapas2.igac.gov.co/image/rest/services/orto/orto18479morelia/ImageServer')
para('**Alcance.** Este manual documenta instalación, visualización y consulta. El tutorial no desarrolla edición catastral, uniones entre los Excel y las capas, cálculos de avalúo ni producción de mapas para impresión.')

output = OUT/'Manual_QGIS_Instalacion_y_Primeros_Pasos.docx'
DOC.save(output)
print(output)
print(json.dumps({'paragraphs':len(DOC.paragraphs),'tables':len(DOC.tables),'figures':figcount,'pages_planned':16},ensure_ascii=False))
