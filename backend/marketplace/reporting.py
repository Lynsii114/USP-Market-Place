"""Reporting & Analytics (FR4.1 - FR4.5, NFR1.3).

All report figures are calculated on the server from COMPLETED order records
only (FR4.3). Every entry point calls require_admin() first (FR4.5 / NFR2.4).
"""
from collections import defaultdict
from datetime import datetime, time, timedelta, timezone as dt_timezone
from io import BytesIO
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
            {"item_name": order["item_name"], "category": order["category"], "units_sold": 0, "revenue": 0.0},
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
    """Returns (pdf_bytes, filename) for a single-file PDF summary (FR4.4)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    report = build_report(admin_id, period, date_from, date_to)
    navy = colors.HexColor("#0d2e4d")
    styles = getSampleStyleSheet()

    def para(text, style="Normal"):
        return Paragraph(escape(str(text)), styles[style])

    def table(data, widths, align_right_from=1):
        t = Table(data, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), navy),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (align_right_from, 0), (-1, -1), "RIGHT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f6fa")]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d6e0ea")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        return t

    range_text = f"{report['date_from'] or 'start'} to {report['date_to'] or 'today'}"
    story = [
        para("USP Buy & Sell - Sales & Order Report", "Title"),
        para(f"Date range: {range_text}   |   Grouped: {report['period']}"),
        para(f"Generated: {timezone.now().strftime('%Y-%m-%d %H:%M UTC')} by {report['generated_by']}"),
        para("Figures are calculated from completed orders only."),
        Spacer(1, 8 * mm),
        table(
            [["Total orders", "Items sold", "Total revenue", "Average order"],
             [report["total_orders"], report["total_items_sold"], f"${report['total_sales']:,.2f}", f"${report['average_order_value']:,.2f}"]],
            [42 * mm] * 4, align_right_from=0,
        ),
        Spacer(1, 8 * mm),
        para("Top-selling items", "Heading2"),
    ]

    if report["top_items"]:
        story.append(table(
            [["Item", "Category", "Units sold", "Revenue"]]
            + [[Paragraph(escape(i["item_name"]), styles["Normal"]), i["category"], i["units_sold"], f"${i['revenue']:,.2f}"] for i in report["top_items"]],
            [75 * mm, 40 * mm, 25 * mm, 30 * mm], align_right_from=2,
        ))
    else:
        story.append(para("No completed orders in this date range."))

    story += [Spacer(1, 8 * mm), para(f"Breakdown ({report['period']})", "Heading2")]
    if report["rows"]:
        story.append(table(
            [["Period", "Orders", "Items sold", "Total sales"]]
            + [[r["date"], r["orders"], r["items_sold"], f"${r['total_sales']:,.2f}"] for r in report["rows"]],
            [50 * mm, 30 * mm, 35 * mm, 35 * mm],
        ))

    buffer = BytesIO()
    SimpleDocTemplate(buffer, pagesize=A4, title="USP Buy & Sell Sales Report", leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm).build(story)
    filename = f"usp-sales-report-{timezone.now().strftime('%Y%m%d-%H%M')}.pdf"
    return buffer.getvalue(), filename
