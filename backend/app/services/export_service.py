"""
Export Service — export query results to CSV, Excel, and PDF.
"""

import io
import csv
from typing import List


def export_to_csv(columns: List[str], rows: List[dict]) -> bytes:
    """Export data to CSV format."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode('utf-8')


def export_to_excel(columns: List[str], rows: List[dict], sheet_name: str = "Results") -> bytes:
    """Export data to Excel format."""
    import pandas as pd

    df = pd.DataFrame(rows, columns=columns)
    output = io.BytesIO()
    df.to_excel(output, index=False, sheet_name=sheet_name, engine='openpyxl')
    output.seek(0)
    return output.read()


def export_to_pdf(
    columns: List[str],
    rows: List[dict],
    title: str = "Query Results",
    sql: str = None,
) -> bytes:
    """Export data to PDF format using ReportLab."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    output = io.BytesIO()
    page_size = landscape(letter) if len(columns) > 5 else letter
    doc = SimpleDocTemplate(output, pagesize=page_size)
    elements = []
    styles = getSampleStyleSheet()

    # Title
    elements.append(Paragraph(title, styles['Title']))
    elements.append(Spacer(1, 12))

    # SQL query if provided
    if sql:
        elements.append(Paragraph(f"<b>SQL:</b> {sql}", styles['Normal']))
        elements.append(Spacer(1, 12))

    # Row count
    elements.append(Paragraph(f"Total rows: {len(rows)}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Table data
    table_data = [columns]
    for row in rows[:500]:  # Limit to 500 rows for PDF
        table_data.append([str(row.get(col, '')) for col in columns])

    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4F46E5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F1F5F9')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
    ]))
    elements.append(table)

    doc.build(elements)
    output.seek(0)
    return output.read()
