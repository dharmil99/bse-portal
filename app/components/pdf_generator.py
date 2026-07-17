from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
import io

NAVY = colors.HexColor('#0A1628')
GOLD = colors.HexColor('#D4AF37')
MUTE = colors.HexColor('#6B7A8D')
LINE = colors.HexColor('#E8ECF0')
GREEN = colors.HexColor('#16A34A')
RED = colors.HexColor('#DC2626')


def _header(elements, styles, title_text, company_name, sector):
    eyebrow_style = ParagraphStyle('Eyebrow', parent=styles['Normal'], fontSize=9, textColor=GOLD, spaceAfter=6, leading=11)
    elements.append(Paragraph("EELANOS ANALYTICS &middot; CONFIDENTIAL", eyebrow_style))
    rule = Table([[""]], colWidths=[0.5 * inch], rowHeights=[0.04 * inch])
    rule.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), GOLD)]))
    elements.append(rule)
    elements.append(Spacer(1, 0.15 * inch))
    title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=20, textColor=NAVY, spaceAfter=2)
    elements.append(Paragraph(title_text, title_style))
    sub_style = ParagraphStyle('Sub', parent=styles['Normal'], fontSize=11, textColor=MUTE)
    elements.append(Paragraph(f"{company_name} &middot; {sector}", sub_style))
    elements.append(Spacer(1, 0.25 * inch))


def _stat_cards(elements, styles, revenue, roce, score, label):
    roce_display = f"{roce}%" if roce not in (None, "N/A") else "N/A"
    score_display = f"{score}" if score not in (None, "N/A") else "N/A"
    stat_table = Table([["REVENUE", "ROCE", "SCORE"], [revenue or "N/A", roce_display, score_display]], colWidths=[1.9 * inch] * 3)
    stat_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, 0), 7), ('TEXTCOLOR', (0, 0), (-1, 0), MUTE),
        ('FONTSIZE', (0, 1), (-1, 1), 14), ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'), ('TEXTCOLOR', (0, 1), (-1, 1), NAVY),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('GRID', (0, 0), (-1, -1), 0.5, LINE),
        ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(stat_table)
    elements.append(Spacer(1, 0.08 * inch))
    label_style = ParagraphStyle('ScoreLabel', parent=styles['Normal'], fontSize=9, textColor=MUTE, alignment=1)
    elements.append(Paragraph(label, label_style))
    elements.append(Spacer(1, 0.25 * inch))


def _bar_row(label, pct):
    filled_width = 4.6 * (pct / 100)
    empty_width = 4.6 - filled_width
    header = Table([[label, f"{round(pct)}th pct"]], colWidths=[3.3 * inch, 1.3 * inch])
    header.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 8), ('TEXTCOLOR', (0, 0), (-1, -1), MUTE),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'), ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    bar = Table([[""]], colWidths=[max(filled_width, 0.02) * inch], rowHeights=[0.06 * inch])
    bar.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), NAVY)]))
    if empty_width > 0:
        empty = Table([[""]], colWidths=[empty_width * inch], rowHeights=[0.06 * inch])
        empty.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), LINE)]))
        bar_row = Table([[bar, empty]], colWidths=[filled_width * inch, empty_width * inch])
    else:
        bar_row = Table([[bar]], colWidths=[4.6 * inch])
    bar_row.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    wrapper = Table([[header], [bar_row]], colWidths=[4.6 * inch])
    wrapper.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    return wrapper


def _percentile_bars(elements, percentiles):
    if percentiles:
        for p in percentiles:
            elements.append(_bar_row(p["label"], p["pct"]))
        elements.append(Spacer(1, 0.15 * inch))


def _commentary(elements, styles, sector):
    commentary_style = ParagraphStyle('Commentary', parent=styles['Normal'], fontSize=9, textColor=MUTE, leading=13)
    elements.append(Paragraph(f"Executive commentary drawn from ratio percentile analysis across {sector.lower()} peer set.", commentary_style))
    elements.append(Spacer(1, 0.3 * inch))


def _footer(elements, from_date, to_date):
    date_range = f"{from_date} &mdash; {to_date}" if from_date and to_date else ""
    footer_table = Table([["Prepared by Eelanos Analytics Platform", date_range]], colWidths=[3.3 * inch, 3.3 * inch])
    footer_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 8), ('TEXTCOLOR', (0, 0), (-1, -1), MUTE),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'), ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(footer_table)


def _ratios_table(elements, styles, ratios):
    elements.append(Paragraph("Financial Ratios", styles['Heading2']))
    elements.append(Spacer(1, 0.1 * inch))

    def disp(v, suffix):
        return f"{v}{suffix}" if v not in (None, "N/A") else "N/A"

    table_data = [
        ["Metric", "Value"],
        ["Net Margin", disp(ratios.get('net_margin'), "%")],
        ["EBITDA Margin", disp(ratios.get('ebitda_margin'), "%")],
        ["ROCE", disp(ratios.get('roce'), "%")],
        ["Debt / Equity", disp(ratios.get('debt_to_equity'), "x")],
        ["ROE", disp(ratios.get('roe'), "%")],
    ]
    table = Table(table_data, colWidths=[3 * inch, 3 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f8f9fa'), colors.white]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey), ('FONTSIZE', (0, 1), (-1, -1), 11), ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.3 * inch))


def _yearly_financials_table(elements, styles, yearly_financials):
    if not yearly_financials:
        return
    elements.append(Paragraph("Multi-Year Financials (&#8377; Cr)", styles['Heading2']))
    note_style = ParagraphStyle('YFNote', parent=styles['Normal'], fontSize=8, textColor=MUTE)
    elements.append(Paragraph("Sales and Net Profit only — EBITDA is not tracked at annual granularity in the current dataset.", note_style))
    elements.append(Spacer(1, 0.08 * inch))
    rows = [["Year", "Sales", "Net Profit"]]
    for row in yearly_financials:
        rows.append([
            str(row.get("year", "")),
            f"{row['sales']:,.1f}" if row.get("sales") is not None else "N/A",
            f"{row['net_profit']:,.1f}" if row.get("net_profit") is not None else "N/A",
        ])
    table = Table(rows, colWidths=[1.5 * inch, 2.25 * inch, 2.25 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f8f9fa'), colors.white]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey), ('FONTSIZE', (0, 1), (-1, -1), 9), ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.3 * inch))


def _peer_table(elements, styles, company_name, peer_rows):
    elements.append(Paragraph("Sector Peer Comparison", styles['Heading2']))
    elements.append(Spacer(1, 0.1 * inch))

    def disp(v, suffix):
        return f"{v:.1f}{suffix}" if v is not None else "N/A"

    rows = [["Company", "ROE", "ROCE", "Net Margin", "Rev Growth", "D/E"]]
    for p in peer_rows:
        rows.append([
            p["name"],
            disp(p.get("roe"), "%"), disp(p.get("roce"), "%"), disp(p.get("net_margin"), "%"),
            disp(p.get("revenue_growth"), "%"),
            f"{p['debt_to_equity']:.2f}x" if p.get("debt_to_equity") is not None else "N/A",
        ])
    table = Table(rows, colWidths=[1.7 * inch, 0.86 * inch, 0.86 * inch, 0.9 * inch, 0.9 * inch, 0.7 * inch])
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), NAVY), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 8), ('PADDING', (0, 0), (-1, -1), 5),
    ]
    for i, p in enumerate(peer_rows, start=1):
        if p.get("is_target"):
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#FFF8E1')))
            style_cmds.append(('FONTNAME', (0, i), (-1, i), 'Helvetica-Bold'))
    table.setStyle(TableStyle(style_cmds))
    elements.append(table)
    elements.append(Spacer(1, 0.2 * inch))
    note_style = ParagraphStyle('Note', parent=styles['Normal'], fontSize=8, textColor=MUTE)
    elements.append(Paragraph(f"{company_name} highlighted above.", note_style))
    elements.append(Spacer(1, 0.25 * inch))


def _strengths_weaknesses(elements, styles, strengths, weaknesses):
    elements.append(Paragraph("Strengths", styles['Heading2']))
    elements.append(Spacer(1, 0.06 * inch))
    s_style = ParagraphStyle('S', parent=styles['Normal'], fontSize=10, textColor=GREEN, leading=14)
    if strengths:
        for s in strengths:
            elements.append(Paragraph(f"&#9679; {s['label']} &mdash; {round(s['pct'])}th percentile", s_style))
    else:
        elements.append(Paragraph("No ratio clears the 75th percentile against sector peers.",
                                   ParagraphStyle('SN', parent=styles['Normal'], fontSize=9, textColor=MUTE)))
    elements.append(Spacer(1, 0.2 * inch))

    elements.append(Paragraph("Weaknesses", styles['Heading2']))
    elements.append(Spacer(1, 0.06 * inch))
    w_style = ParagraphStyle('W', parent=styles['Normal'], fontSize=10, textColor=RED, leading=14)
    if weaknesses:
        for w in weaknesses:
            elements.append(Paragraph(f"&#9679; {w['label']} &mdash; {round(w['pct'])}th percentile", w_style))
    else:
        elements.append(Paragraph("No ratio falls below the 50th percentile.",
                                   ParagraphStyle('WN', parent=styles['Normal'], fontSize=9, textColor=MUTE)))
    elements.append(Spacer(1, 0.25 * inch))


def generate_pdf_report(company_name, sector, ratios, score, label, report_type="Executive Summary",
                         revenue=None, percentiles=None, from_date=None, to_date=None,
                         yearly_financials=None, peer_rows=None, strengths=None, weaknesses=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=inch, leftMargin=inch, topMargin=inch, bottomMargin=inch)
    styles = getSampleStyleSheet()
    elements = []

    _header(elements, styles, report_type, company_name, sector)

    if report_type == "Full Analysis":
        _stat_cards(elements, styles, revenue, ratios.get('roce'), score, label)
        _percentile_bars(elements, percentiles)
        _ratios_table(elements, styles, ratios)
        _yearly_financials_table(elements, styles, yearly_financials)
        _commentary(elements, styles, sector)

    elif report_type == "Peer Comparison":
        _stat_cards(elements, styles, revenue, ratios.get('roce'), score, label)
        _peer_table(elements, styles, company_name, peer_rows or [])
        _commentary(elements, styles, sector)

    elif report_type == "Board Presentation":
        _stat_cards(elements, styles, revenue, ratios.get('roce'), score, label)
        _strengths_weaknesses(elements, styles, strengths or [], weaknesses or [])
        _commentary(elements, styles, sector)

    else:  # Executive Summary (default)
        _stat_cards(elements, styles, revenue, ratios.get('roce'), score, label)
        _percentile_bars(elements, percentiles)
        _commentary(elements, styles, sector)

    _footer(elements, from_date, to_date)

    doc.build(elements)
    buffer.seek(0)
    return buffer