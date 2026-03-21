import io
from datetime import date
from typing import Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from app.core.database import get_supabase_admin

db = get_supabase_admin()

# Ranglar
DARK_BLUE = colors.HexColor("#1E3A5F")
BLUE = colors.HexColor("#2E86C1")
RED = colors.HexColor("#C0392B")
LIGHT_GRAY = colors.HexColor("#F0F3F4")
GREEN = colors.HexColor("#27AE60")


async def generate_report_pdf(
    report_id: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    department_id: Optional[str] = None,
) -> bytes:
    """PDF hisobot generatsiya"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", fontSize=16, fontName="Helvetica-Bold", textColor=DARK_BLUE, spaceAfter=6)
    h2_style = ParagraphStyle("h2", fontSize=12, fontName="Helvetica-Bold", textColor=BLUE, spaceAfter=4)
    h3_style = ParagraphStyle("h3", fontSize=10, fontName="Helvetica-Bold", textColor=WHITE_COLOR(), spaceAfter=2)
    normal = styles["Normal"]

    story = []

    # Sarlavha
    story.append(Paragraph("RESTORAN BOSHQARUV TIZIMI", title_style))
    story.append(Paragraph(f"Hisobot — {date.today().strftime('%d.%m.%Y')}", styles["Normal"]))
    story.append(HRFlowable(width="100%", thickness=2, color=DARK_BLUE))
    story.append(Spacer(1, 0.3 * cm))

    # Ma'lumotlarni olish
    q = db.table("daily_reports").select("*, departments(name)")
    if report_id:
        q = q.eq("id", report_id)
    elif date_from and date_to:
        q = q.gte("report_date", date_from.isoformat()).lte("report_date", date_to.isoformat())
    if department_id:
        q = q.eq("department_id", department_id)
    reports = q.order("report_date").execute().data

    grand_totals = {"revenue": 0, "cost": 0, "expenses": 0, "net_profit": 0}

    for report in reports:
        dept_name = (report.get("departments") or {}).get("name", "")
        story.append(Paragraph(f"📅 {report['report_date']}  |  {dept_name}", h2_style))

        # Sotuvlar jadvali
        sales = db.table("sales").select(
            "quantity, unit_price, total_amount, total_cost, products(name)"
        ).eq("daily_report_id", report["id"]).execute().data

        if sales:
            story.append(Paragraph("SOTUVLAR", ParagraphStyle("sh", fontSize=10, fontName="Helvetica-Bold", textColor=colors.white, backColor=BLUE)))
            sale_data = [["Mahsulot", "Miqdor", "Narx", "Jami", "Tannarx", "Foyda"]]
            for s in sales:
                name = (s.get("products") or {}).get("name", "")
                total = s.get("total_amount", 0) or 0
                cost = s.get("total_cost", 0) or 0
                sale_data.append([
                    name,
                    f"{s.get('quantity', 0):.1f}",
                    f"{s.get('unit_price', 0):,.0f}",
                    f"{total:,.0f}",
                    f"{cost:,.0f}",
                    f"{(total - cost):,.0f}",
                ])
            sale_table = Table(sale_data, colWidths=[5.5*cm, 1.8*cm, 2.2*cm, 2.2*cm, 2.2*cm, 2.2*cm])
            sale_table.setStyle(_table_style())
            story.append(sale_table)
            story.append(Spacer(1, 0.2 * cm))

        # Xarajatlar jadvali
        expenses = db.table("expenses").select(
            "amount, description, expense_categories(name)"
        ).eq("daily_report_id", report["id"]).execute().data

        if expenses:
            story.append(Paragraph("XARAJATLAR", ParagraphStyle("sh2", fontSize=10, fontName="Helvetica-Bold", textColor=colors.white, backColor=RED)))
            exp_data = [["Kategoriya", "Summa", "Izoh"]]
            for e in expenses:
                cat = (e.get("expense_categories") or {}).get("name", "")
                exp_data.append([cat, f"{e.get('amount', 0):,.0f}", e.get("description", "") or ""])
            exp_table = Table(exp_data, colWidths=[4*cm, 3*cm, 9*cm])
            exp_table.setStyle(_table_style(header_color=RED))
            story.append(exp_table)
            story.append(Spacer(1, 0.2 * cm))

        # Yig'ma
        rev = report.get("total_revenue", 0) or 0
        cost = report.get("total_cost", 0) or 0
        gross = report.get("gross_profit", 0) or 0
        exp_total = report.get("total_expenses", 0) or 0
        net = report.get("net_profit", 0) or 0

        grand_totals["revenue"] += rev
        grand_totals["cost"] += cost
        grand_totals["expenses"] += exp_total
        grand_totals["net_profit"] += net

        summary_data = [
            ["Ko'rsatkich", "Summa (so'm)"],
            ["Jami daromad", f"{rev:,.0f}"],
            ["Tannarx", f"{cost:,.0f}"],
            ["Yalpi foyda", f"{gross:,.0f}"],
            ["Xarajatlar", f"{exp_total:,.0f}"],
            ["SOF FOYDA", f"{net:,.0f}"],
            ["Balans", f"{report.get('closing_balance', 0) or 0:,.0f}"],
        ]
        summary_table = Table(summary_data, colWidths=[6*cm, 5*cm])
        summary_table.setStyle(_summary_style())
        story.append(summary_table)
        story.append(Spacer(1, 0.5 * cm))
        story.append(HRFlowable(width="100%", thickness=1, color=LIGHT_GRAY))
        story.append(Spacer(1, 0.3 * cm))

    # Umumiy yig'ma (ko'p hisobot bo'lsa)
    if len(reports) > 1:
        story.append(Paragraph("UMUMIY YIGMA", title_style))
        grand_data = [
            ["Jami daromad", f"{grand_totals['revenue']:,.0f} so'm"],
            ["Jami tannarx", f"{grand_totals['cost']:,.0f} so'm"],
            ["Jami xarajatlar", f"{grand_totals['expenses']:,.0f} so'm"],
            ["Umumiy sof foyda", f"{grand_totals['net_profit']:,.0f} so'm"],
        ]
        grand_table = Table(grand_data, colWidths=[6*cm, 5*cm])
        grand_table.setStyle(_summary_style(highlight_last=True))
        story.append(grand_table)

    doc.build(story)
    return buffer.getvalue()


def WHITE_COLOR():
    return colors.white


def _table_style(header_color=None):
    hc = header_color or BLUE
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), hc),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])


def _summary_style(highlight_last: bool = False):
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if highlight_last:
        style.append(("BACKGROUND", (0, -1), (-1, -1), GREEN))
        style.append(("TEXTCOLOR", (0, -1), (-1, -1), colors.white))
        style.append(("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"))
    return TableStyle(style)
