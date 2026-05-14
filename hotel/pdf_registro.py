"""Generación del PDF del reporte de registro (ingresos/salidas por check-in y check-out)."""

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _p(text: str) -> str:
    return escape(str(text if text is not None else ''))


# Orden de columnas: estadía + datos de huésped mostrados en el libro + cierre estadía.
_LIBRO_REGISTRO_HEADERS = (
    'N°',
    'Ingreso',
    'Salida',
    'Tipo doc.',
    'N° documento',
    'Nombres',
    'Apellidos',
    'F. nac.',
    'Nacionalidad',
    'Sexo',
    'Residencia',
    'Motivo viaje',
    'Hab.',
)

_LIBRO_REGISTRO_KEYS = (
    'orden',
    'entrada',
    'salida',
    'tipo_documento',
    'documento_identidad',
    'nombre',
    'apellidos',
    'fecha_nacimiento',
    'nacionalidad',
    'sexo',
    'lugar_residencia',
    'motivo_viaje',
    'habitacion',
)


def build_registro_pdf(
    *,
    titulo_hotel: str,
    subtitulo_periodo: str,
    pie_generacion: str,
    filas: list[dict],
) -> bytes:
    """
    filas: dicts con las claves de _LIBRO_REGISTRO_KEYS (ver _filas_reporte_registro en views).
    """
    buf = BytesIO()
    page_size = landscape(A4)
    doc = SimpleDocTemplate(
        buf,
        pagesize=page_size,
        leftMargin=8 * mm,
        rightMargin=8 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title='Registro',
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'T',
        parent=styles['Heading1'],
        fontSize=14,
        spaceAfter=4,
        alignment=1,
    )
    sub_style = ParagraphStyle(
        'S',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=10,
        alignment=1,
        textColor=colors.HexColor('#333333'),
    )
    cell_style = ParagraphStyle(
        'C',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
    )
    header_style = ParagraphStyle(
        'H',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        textColor=colors.white,
    )
    pie_style = ParagraphStyle(
        'Pie',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
    )

    story = []
    story.append(Paragraph(_p(f'{titulo_hotel} — Registro'), title_style))
    story.append(Paragraph(_p(subtitulo_periodo), sub_style))
    story.append(
        Paragraph(
            '<i>Ingresos por fecha y hora de check-in. Datos del huésped según ficha en el sistema. '
            'Salida: check-out registrado.</i>',
            sub_style,
        )
    )

    data = [[Paragraph(_p(h), header_style) for h in _LIBRO_REGISTRO_HEADERS]]

    for f in filas:
        row = []
        for key in _LIBRO_REGISTRO_KEYS:
            val = f.get(key, '')
            row.append(Paragraph(_p(val if val is not None else ''), cell_style))
        data.append(row)

    tw = page_size[0] - 16 * mm
    n = len(_LIBRO_REGISTRO_KEYS)
    col_widths = [tw / n] * n

    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    last = n - 1
    center_tail_start = last
    tbl.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a365d')),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (center_tail_start, 0), (last, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ]
        )
    )
    story.append(tbl)
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(_p(pie_generacion), pie_style))
    if not filas:
        story.append(Spacer(1, 4 * mm))
        story.append(
            Paragraph(
                '<i>No hay registros de check-in en el período seleccionado.</i>',
                styles['Normal'],
            )
        )

    doc.build(story)
    pdf = buf.getvalue()
    buf.close()
    return pdf
