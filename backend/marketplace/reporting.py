"""Reporting & Analytics (FR4.1 - FR4.5, NFR1.3).

All report figures are calculated on the server from COMPLETED order records
only (FR4.3). Every entry point calls require_admin() first (FR4.5 / NFR2.4).
"""
from collections import defaultdict
from .category_catalog import canonical_category_name
from datetime import datetime, time, timedelta, timezone as dt_timezone
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from django.utils import timezone
from django.utils.dateparse import parse_date

from .exceptions import ApiError
from .queries import visible_purchases
from .services import require_admin

VALID_PERIODS = {"daily", "weekly", "monthly"}
TOP_ITEMS_LIMIT = 5


def _parse_range(date_from, date_to):
    start = parse_date(date_from) if date_from else None
    end = parse_date(date_to) if date_to else None
    if date_from and not start:
        raise ApiError("From date must be YYYY-MM-DD", 400)
    if date_to and not end:
        raise ApiError("To date must be YYYY-MM-DD", 400)
    if start and end and start > end:
        raise ApiError("From date cannot be after To date", 400)
    return start, end


def _completed_orders(start, end):
    """Completed orders only (FR4.3), optionally limited to a date range (FR4.2)."""
    query = visible_purchases().filter(status="completed")
    if start:
        query = query.filter(purchased_at__gte=datetime.combine(start, time.min, tzinfo=dt_timezone.utc))
    if end:
        query = query.filter(purchased_at__lt=datetime.combine(end + timedelta(days=1), time.min, tzinfo=dt_timezone.utc))
    return query.values("item_id", "item_name", "category", "quantity", "total_amount", "price", "purchased_at")


def _period_key(purchased_at, period):
    day = purchased_at.date()
    if period == "monthly":
        return day.strftime("%Y-%m")
    if period == "weekly":
        year, week, _ = day.isocalendar()
        return f"{year}-W{week:02d}"
    return day.isoformat()


def build_report(admin_id, period="daily", date_from="", date_to=""):
    admin = require_admin(admin_id)
    period = period if period in VALID_PERIODS else "daily"
    start, end = _parse_range(date_from, date_to)

    rows = defaultdict(lambda: {"orders": 0, "items_sold": 0, "total_sales": 0.0})
    items = {}
    total_orders = total_items = 0
    total_revenue = 0.0

    for order in _completed_orders(start, end):
        if not order["purchased_at"]:
            continue
        quantity = order["quantity"] or 1
        amount = float(order["total_amount"] or (order["price"] or 0) * quantity)

        total_orders += 1
        total_items += quantity
        total_revenue += amount

        row = rows[_period_key(order["purchased_at"], period)]
        row["orders"] += 1
        row["items_sold"] += quantity
        row["total_sales"] += amount

        item = items.setdefault(
            order["item_id"],
            {"item_name": order["item_name"], "category": canonical_category_name(order["category"]), "units_sold": 0, "revenue": 0.0},
        )
        item["units_sold"] += quantity
        item["revenue"] += amount

    top_items = sorted(items.values(), key=lambda i: (-i["units_sold"], -i["revenue"], i["item_name"]))[:TOP_ITEMS_LIMIT]

    return {
        "period": period,
        "date_from": start.isoformat() if start else "",
        "date_to": end.isoformat() if end else "",
        "generated_at": timezone.now().isoformat(),
        "generated_by": admin.username,
        "total_orders": total_orders,
        "total_items_sold": total_items,
        "total_sales": round(total_revenue, 2),
        "average_order_value": round(total_revenue / total_orders, 2) if total_orders else 0,
        "rows": [
            {"date": key, "orders": v["orders"], "items_sold": v["items_sold"], "total_sales": round(v["total_sales"], 2)}
            for key, v in sorted(rows.items(), reverse=True)
        ],
        "top_items": [{**i, "revenue": round(i["revenue"], 2)} for i in top_items],
    }


def build_report_pdf(admin_id, period="daily", date_from="", date_to=""):
    """Build a branded, paginated A4 report using the same server-side totals."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    report = build_report(admin_id, period, date_from, date_to)
    navy = colors.HexColor("#082b45")
    teal = colors.HexColor("#2ca3ad")
    muted = colors.HexColor("#526779")
    border = colors.HexColor("#dce6ed")
    pale = colors.HexColor("#f2f7fa")
    width = A4[0] - 36 * mm
    generated = datetime.fromisoformat(report["generated_at"])
    generated_local = timezone.localtime(generated, timezone.get_fixed_timezone(720))
    generated_label = generated_local.strftime("%d %b %Y, %I:%M %p") + " Fiji time"
    logo = ImageReader(str(Path(__file__).resolve().parent / "assets" / "usp-logo.png"))
    logo_width, logo_height = logo.getSize()
    styles = {
        "body": ParagraphStyle("ReportBody", fontName="Helvetica", fontSize=9, leading=13, textColor=navy, spaceAfter=0),
        "small": ParagraphStyle("ReportSmall", fontName="Helvetica", fontSize=8, leading=11, textColor=muted),
        "heading": ParagraphStyle("ReportHeading", fontName="Helvetica-Bold", fontSize=12, leading=16, textColor=navy, spaceBefore=16, spaceAfter=10, keepWithNext=True),
        "label": ParagraphStyle("ReportLabel", fontName="Helvetica-Bold", fontSize=7.5, leading=11, textColor=muted),
        "value": ParagraphStyle("ReportValue", fontName="Helvetica-Bold", fontSize=18, leading=24, textColor=navy),
        "header": ParagraphStyle("ReportTableHeader", fontName="Helvetica-Bold", fontSize=8, leading=11, textColor=colors.white),
        "header_number": ParagraphStyle("ReportTableHeaderNumber", fontName="Helvetica-Bold", fontSize=8, leading=11, textColor=colors.white, alignment=TA_RIGHT),
        "number": ParagraphStyle("ReportNumber", fontName="Helvetica", fontSize=9, leading=13, textColor=navy, alignment=TA_RIGHT),
    }

    def para(value, style="body"):
        return Paragraph(escape(str(value)), styles[style])

    def data_table(headings, rows, fractions, numeric_from):
        cells = [[para(text, "header_number" if index >= numeric_from else "header") for index, text in enumerate(headings)]]
        cells += [[para(value, "number" if index >= numeric_from else "body") for index, value in enumerate(row)] for row in rows]
        table = Table(cells, colWidths=[width * value for value in fractions], repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), navy),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, pale]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ("LINEBELOW", (0, 0), (-1, 0), 2, teal),
            ("LINEBELOW", (0, 1), (-1, -1), 0.35, border),
        ]))
        return table

    def page_chrome(canvas, document):
        canvas.saveState()
        page_width, page_height = A4
        image_width = 45 * mm
        image_height = image_width * logo_height / logo_width
        canvas.drawImage(logo, 18 * mm, page_height - 16 * mm - image_height, width=image_width, height=image_height, mask="auto")
        canvas.setFillColor(teal)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(76 * mm, page_height - 19 * mm, "USP BUY & SELL  /  ADMINISTRATION")
        canvas.setFillColor(navy)
        canvas.setFont("Helvetica-Bold", 19)
        canvas.drawString(76 * mm, page_height - 29 * mm, "Sales & Order Report")
        canvas.setFillColor(muted)
        canvas.setFont("Helvetica", 9)
        canvas.drawString(76 * mm, page_height - 36 * mm, f"{report['period'].capitalize()} summary | Completed orders")
        canvas.setStrokeColor(teal)
        canvas.setLineWidth(1.3)
        canvas.line(18 * mm, page_height - 44 * mm, page_width - 18 * mm, page_height - 44 * mm)
        canvas.setStrokeColor(border)
        canvas.setLineWidth(0.5)
        canvas.line(18 * mm, 18 * mm, page_width - 18 * mm, 18 * mm)
        canvas.setFillColor(muted)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(18 * mm, 12 * mm, "USP Buy & Sell | Administrative report | Currency: FJD")
        canvas.drawRightString(page_width - 18 * mm, 12 * mm, f"Page {document.page}")
        canvas.restoreState()

    if report["date_from"] or report["date_to"]:
        range_text = f"{report['date_from'] or 'First recorded order'} to {report['date_to'] or 'Latest recorded order'}"
    else:
        range_text = "All recorded dates"
    metadata = Table([
        [para("REPORTING PERIOD", "label"), para("PREPARED", "label")],
        [para(range_text), para(generated_label)],
        [para(f"Grouped {report['period']} | Date filters use UTC", "small"), para(f"Prepared by: {report['generated_by']}", "small")],
    ], colWidths=[width * 0.52, width * 0.48], hAlign="LEFT")
    metadata.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    metrics = [
        ("TOTAL ORDERS", f"{report['total_orders']:,}"),
        ("ITEMS SOLD", f"{report['total_items_sold']:,}"),
        ("REVENUE (FJD)", f"${report['total_sales']:,.2f}"),
        ("AVERAGE ORDER (FJD)", f"${report['average_order_value']:,.2f}"),
    ]
    summary = Table([[ [para(label, "label"), Spacer(1, 5), para(value, "value")] for label, value in metrics ]], colWidths=[width / 4] * 4, hAlign="LEFT")
    summary.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), pale), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOX", (0, 0), (-1, -1), 0.5, border), ("INNERGRID", (0, 0), (-1, -1), 0.5, border), ("TOPPADDING", (0, 0), (-1, -1), 14), ("BOTTOMPADDING", (0, 0), (-1, -1), 14), ("LEFTPADDING", (0, 0), (-1, -1), 10)]))
    story = [metadata, Spacer(1, 7 * mm), summary, Spacer(1, 4 * mm), para("Completed orders only; pending and cancelled orders are excluded. Average order value is revenue divided by completed orders. All amounts are in Fijian dollars (FJD).", "small"), para("Top-selling items", "heading")]
    if report["top_items"]:
        story.append(data_table(["Item", "Category", "Units sold", "Revenue (FJD)"], [[item["item_name"], item["category"], f"{item['units_sold']:,}", f"${item['revenue']:,.2f}"] for item in report["top_items"]], [0.43, 0.23, 0.14, 0.20], 2))
    else:
        story.append(para("No completed sales were recorded for this reporting period.", "small"))
    story.append(para(f"{report['period'].capitalize()} sales breakdown", "heading"))
    if report["rows"]:
        story.append(data_table(["Period", "Orders", "Items sold", "Revenue (FJD)"], [[row["date"], f"{row['orders']:,}", f"{row['items_sold']:,}", f"${row['total_sales']:,.2f}"] for row in report["rows"]], [0.34, 0.18, 0.20, 0.28], 1))
    else:
        story.append(para("No completed orders are available for this breakdown.", "small"))
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, title="USP Buy & Sell - Sales & Order Report", author="USP Buy & Sell", subject=f"{report['period'].capitalize()} sales and order summary", leftMargin=18 * mm, rightMargin=18 * mm, topMargin=51 * mm, bottomMargin=24 * mm)
    document.build(story, onFirstPage=page_chrome, onLaterPages=page_chrome)
    filename = f"usp-sales-report-{generated_local.strftime('%Y%m%d-%H%M')}.pdf"
    return buffer.getvalue(), filename
