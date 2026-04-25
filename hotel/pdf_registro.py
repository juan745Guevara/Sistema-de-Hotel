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


def build_registro_pdf(
    *,
    titulo_hotel: str,
    subtitulo_periodo: str,
    pie_generacion: str,
    filas: list[dict],
) -> bytes:
    """
    filas: dicts con claves orden, entrada, salida, documento, nombre_completo,
    nacionalidad, procedencia, habitacion, num_huespedes, reserva_id
    """
    buf = BytesIO()
    page_size = landscape(A4)
    doc = SimpleDocTemplate(
        buf,
        pagesize=page_size,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
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
        fontSize=7,
        leading=9,
    )
    header_style = ParagraphStyle(
        'H',
        parent=styles['Normal'],
        fontSize=7,
        leading=9,
        textColor=colors.white,
    )

    story = []
    story.append(Paragraph(_p(f'{titulo_hotel} — Registro'), title_style))
    story.append(Paragraph(_p(subtitulo_periodo), sub_style))
    story.append(
        Paragraph(
            '<i>Ingresos al establecimiento por fecha y hora de check-in (orden cronológico). '
            'Salida: fecha y hora de check-out si consta en el sistema.</i>',
            sub_style,
        )
    )

    headers = [
        'N°',
        'Fecha y hora ingreso',
        'Fecha y hora salida',
        'Documento',
        'Apellidos y nombres',
        'Nacionalidad',
        'Procedencia',
        'Hab.',
        'Pers.',
        'Reserva',
    ]
    data = [[Paragraph(_p(h), header_style) for h in headers]]

    for f in filas:
        row = [
            Paragraph(_p(str(f['orden'])), cell_style),
            Paragraph(_p(f['entrada']), cell_style),
            Paragraph(_p(f['salida']), cell_style),
            Paragraph(_p(f['documento']), cell_style),
            Paragraph(_p(f['nombre_completo']), cell_style),
            Paragraph(_p(f['nacionalidad']), cell_style),
            Paragraph(_p(f['procedencia']), cell_style),
            Paragraph(_p(f['habitacion']), cell_style),
            Paragraph(_p(str(f['num_huespedes'])), cell_style),
            Paragraph(_p(str(f['reserva_id'])), cell_style),
        ]
        data.append(row)

    tw = page_size[0] - 24 * mm
    col_widths = [
        8 * mm,
        28 * mm,
        28 * mm,
        22 * mm,
        52 * mm,
        22 * mm,
        38 * mm,
        12 * mm,
        12 * mm,
        14 * mm,
    ]
    scale = tw / sum(col_widths)
    col_widths = [w * scale for w in col_widths]

    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a365d')),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (7, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ]
        )
    )
    story.append(tbl)
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(_p(pie_generacion), styles['Normal']))
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
