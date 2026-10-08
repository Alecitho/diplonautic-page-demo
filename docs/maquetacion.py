"""Maquetación común de los manuales PDF (ReportLab).

Proporciona la plantilla de documento (portada, cabecera, pie, índice y
marcadores) y funciones cortas para escribir el contenido:
    h1, h2, h3, p, lista, tabla, codigo, nota, captura, salto
"""
import os
from datetime import date
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, ListFlowable,
                                ListItem, NextPageTemplate, PageBreak, PageTemplate, Paragraph,
                                Preformatted, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
LOGO = os.path.join(ROOT_DIR, "app", "static", "img", "logo-diplonautic.jpg")

# Paleta corporativa (la misma que la web)
PETROL_900 = colors.HexColor("#072f3f")
PETROL_700 = colors.HexColor("#0e4a63")
TEAL_500 = colors.HexColor("#1f9bb3")
TEAL_100 = colors.HexColor("#e3f3f6")
SAND_50 = colors.HexColor("#f7f5f0")
INK_900 = colors.HexColor("#14212b")
INK_600 = colors.HexColor("#4a5a66")
LINE = colors.HexColor("#dde4e8")
WARN_BG = colors.HexColor("#fdf3dc")

# --------------------------------------------------------------------------
# Estilos de texto
# --------------------------------------------------------------------------
_base = getSampleStyleSheet()
ST = {
    "body": ParagraphStyle("body", parent=_base["BodyText"], fontName="Helvetica", fontSize=10,
                           leading=14.5, textColor=INK_900, spaceAfter=6),
    "H1": ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=18, leading=22,
                         textColor=PETROL_900, spaceBefore=4, spaceAfter=10, keepWithNext=1),
    "H2": ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=13.5, leading=17,
                         textColor=PETROL_700, spaceBefore=12, spaceAfter=6, keepWithNext=1),
    "H3": ParagraphStyle("H3", fontName="Helvetica-Bold", fontSize=11, leading=14,
                         textColor=INK_900, spaceBefore=8, spaceAfter=4, keepWithNext=1),
    "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=8.6, leading=11, textColor=INK_900),
    "cellhead": ParagraphStyle("cellhead", fontName="Helvetica-Bold", fontSize=8.6, leading=11,
                               textColor=colors.white),
    "code": ParagraphStyle("code", fontName="Courier", fontSize=8.2, leading=10.5, textColor=INK_900),
    "caption": ParagraphStyle("caption", fontName="Helvetica-Oblique", fontSize=8.5, leading=11,
                              textColor=INK_600, alignment=TA_CENTER, spaceBefore=3, spaceAfter=10),
    "note": ParagraphStyle("note", fontName="Helvetica", fontSize=9.4, leading=13, textColor=INK_900),
    "toc1": ParagraphStyle("toc1", fontName="Helvetica-Bold", fontSize=10.5, leading=14.5,
                           leftIndent=0, textColor=PETROL_900),
    "toc2": ParagraphStyle("toc2", fontName="Helvetica", fontSize=9.5, leading=12,
                           leftIndent=16, textColor=INK_600),
}


# --------------------------------------------------------------------------
# Plantilla de documento
# --------------------------------------------------------------------------
class Manual(BaseDocTemplate):
    def __init__(self, filename, titulo, subtitulo, version="1.0"):
        super().__init__(filename, pagesize=A4, leftMargin=2.1 * cm, rightMargin=2.1 * cm,
                         topMargin=2.6 * cm, bottomMargin=2.2 * cm, title=titulo,
                         author="Diplonautic", subject=subtitulo, creator="docs/generar_manuales.py")
        self.titulo, self.subtitulo, self.version = titulo, subtitulo, version
        self._seq = 0
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="f")
        self.addPageTemplates([
            PageTemplate(id="portada", frames=[frame], onPage=self._portada),
            PageTemplate(id="contenido", frames=[frame], onPage=self._pagina),
        ])

    def beforeDocument(self):
        # multiBuild maqueta varias pasadas: las claves deben repetirse en cada una
        self._seq = 0

    # Registra H1/H2 en el índice y en los marcadores del PDF
    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name in ("H1", "H2"):
            nivel = 0 if flowable.style.name == "H1" else 1
            texto = flowable.getPlainText()
            self._seq += 1
            clave = f"sec{self._seq}"
            self.canv.bookmarkPage(clave)
            self.canv.addOutlineEntry(texto, clave, level=nivel, closed=nivel > 0)
            self.notify("TOCEntry", (nivel, texto, self.page, clave))

    def _portada(self, canv, doc):
        w, h = A4
        canv.saveState()
        canv.setFillColor(PETROL_900)
        canv.rect(0, 0, w, h * 0.58, stroke=0, fill=1)
        canv.setFillColor(PETROL_700)
        canv.rect(0, h * 0.58 - 0.5 * cm, w, 0.5 * cm, stroke=0, fill=1)
        canv.drawImage(ImageReader(LOGO), 2.1 * cm, h - 5.2 * cm, width=10 * cm, height=10 * cm * 117 / 640,
                       mask="auto")
        canv.setFillColor(colors.white)
        canv.setFont("Helvetica-Bold", 30)
        canv.drawString(2.1 * cm, h * 0.42, self.titulo)
        canv.setFont("Helvetica", 14)
        canv.setFillColor(colors.HexColor("#8fd6e3"))
        canv.drawString(2.1 * cm, h * 0.42 - 1.1 * cm, self.subtitulo)
        canv.setFillColor(colors.white)
        canv.setFont("Helvetica", 10.5)
        lineas = [
            "DEMO de web corporativa con área privada y foro interno",
            f"Versión del documento: {self.version}",
            f"Fecha de generación: {date.today().strftime('%d/%m/%Y')}",
        ]
        for i, linea in enumerate(lineas):
            canv.drawString(2.1 * cm, h * 0.42 - 2.6 * cm - i * 0.6 * cm, linea)
        canv.setFont("Helvetica", 8.5)
        canv.setFillColor(colors.HexColor("#9fb6c0"))
        canv.drawString(2.1 * cm, 1.6 * cm, "Documento generado automáticamente con docs/generar_manuales.py")
        canv.restoreState()

    def _pagina(self, canv, doc):
        w, h = A4
        canv.saveState()
        canv.drawImage(ImageReader(LOGO), doc.leftMargin, h - 1.75 * cm, width=4.2 * cm,
                       height=4.2 * cm * 117 / 640, mask="auto")
        canv.setFont("Helvetica", 8.5)
        canv.setFillColor(INK_600)
        canv.drawRightString(w - doc.rightMargin, h - 1.45 * cm, self.titulo)
        canv.setStrokeColor(LINE)
        canv.setLineWidth(0.6)
        canv.line(doc.leftMargin, h - 1.95 * cm, w - doc.rightMargin, h - 1.95 * cm)
        canv.line(doc.leftMargin, 1.5 * cm, w - doc.rightMargin, 1.5 * cm)
        canv.drawString(doc.leftMargin, 1.05 * cm, "Diplonautic · DEMO web corporativa")
        canv.drawRightString(w - doc.rightMargin, 1.05 * cm, f"Página {doc.page}")
        canv.restoreState()


def agrupar_titulos(contenido):
    """Une cada título con el bloque siguiente para que nunca quede solo al pie de página.

    (keepWithNext de ReportLab no agrupa con bloques KeepTogether como tablas o capturas.)
    """
    resultado, titulos = [], []
    for bloque in contenido:
        if isinstance(bloque, Paragraph) and bloque.style.name in ("H1", "H2", "H3"):
            titulos.append(bloque)
        elif titulos and not isinstance(bloque, PageBreak):
            # Un KeepTogether anidado fuerza saltos de página: se aplana su contenido
            interior = bloque._content if isinstance(bloque, KeepTogether) else [bloque]
            resultado.append(KeepTogether(titulos + list(interior)))
            titulos = []
        else:
            resultado += titulos + [bloque]
            titulos = []
    return resultado + titulos


def construir(ruta, titulo, subtitulo, contenido, version="1.0"):
    """Genera el PDF: portada + índice + contenido (multiBuild resuelve el índice)."""
    doc = Manual(ruta, titulo, subtitulo, version)
    indice = TableOfContents(levelStyles=[ST["toc1"], ST["toc2"]], dotsMinLevel=0)
    historia = [NextPageTemplate("contenido"), PageBreak(),
                Paragraph("Índice", ParagraphStyle("TOCTitle", parent=ST["H1"])), indice, PageBreak()]
    historia += agrupar_titulos(contenido)
    doc.multiBuild(historia)
    return ruta


# --------------------------------------------------------------------------
# Bloques de contenido
# --------------------------------------------------------------------------
def h1(texto):
    return Paragraph(texto, ST["H1"])


def h2(texto):
    return Paragraph(texto, ST["H2"])


def h3(texto):
    return Paragraph(texto, ST["H3"])


def p(texto):
    """Párrafo. Admite el marcado de ReportLab: <b>, <i>, <font face='Courier'>."""
    return Paragraph(texto, ST["body"])


def c(texto):
    """Fragmento de código en línea (escapa < > &)."""
    return f"<font face='Courier' color='#0e4a63'>{escape(str(texto))}</font>"


def lista(items, numerada=False):
    return ListFlowable(
        [ListItem(Paragraph(i, ST["body"]), leftIndent=14) for i in items],
        bulletType="1" if numerada else "bullet", start="1" if numerada else "•",
        bulletFormat="%s." if numerada else None,
        leftIndent=14, bulletFontSize=9 if not numerada else 9.5, bulletColor=PETROL_700,
    )


def tabla(filas, anchos, cabecera=True, escapar=False):
    """Tabla con cabecera azul y filas alternas. Los anchos son en cm."""
    def celda(valor, cab):
        texto = escape(str(valor)) if escapar else str(valor)
        return Paragraph(texto, ST["cellhead"] if cab else ST["cell"])

    datos = [[celda(v, cabecera and i == 0) for v in fila] for i, fila in enumerate(filas)]
    t = Table(datos, colWidths=[a * cm for a in anchos], repeatRows=1 if cabecera else 0)
    estilo = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    if cabecera:
        estilo.append(("BACKGROUND", (0, 0), (-1, 0), PETROL_700))
    inicio = 1 if cabecera else 0
    for fila in range(inicio, len(datos)):
        if (fila - inicio) % 2 == 1:
            estilo.append(("BACKGROUND", (0, fila), (-1, fila), SAND_50))
    t.setStyle(TableStyle(estilo))
    return KeepTogether([t, Spacer(1, 8)]) if len(datos) <= 14 else t


def codigo(texto):
    pre = Preformatted(texto.strip("\n"), ST["code"])
    t = Table([[pre]], colWidths=[None])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SAND_50),
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return KeepTogether([t, Spacer(1, 8)])


def nota(texto, tipo="info"):
    fondo, borde = (TEAL_100, TEAL_500) if tipo == "info" else (WARN_BG, colors.HexColor("#d99a00"))
    t = Table([[Paragraph(texto, ST["note"])]], colWidths=[None])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), fondo),
        ("LINEBEFORE", (0, 0), (0, -1), 3, borde),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return KeepTogether([t, Spacer(1, 8)])


def captura(nombre, pie, ancho_cm=14.5):
    ruta = os.path.join(BASE_DIR, "capturas", nombre)
    if not os.path.exists(ruta):
        return nota(f"[Captura no encontrada: {escape(nombre)}]", "warn")
    iw, ih = ImageReader(ruta).getSize()
    img = Image(ruta, width=ancho_cm * cm, height=ancho_cm * cm * ih / iw)
    marco = Table([[img]], colWidths=[ancho_cm * cm])
    marco.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return KeepTogether([marco, Paragraph(pie, ST["caption"])])


def espacio(alto_cm=0.3):
    return Spacer(1, alto_cm * cm)


def salto():
    return PageBreak()
