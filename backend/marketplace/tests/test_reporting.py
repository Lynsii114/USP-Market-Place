"""Automated tests for Reporting & Analytics (FR4.1 - FR4.5)."""
from datetime import datetime, timezone

from django.test import Client, TestCase

from marketplace.authentication import issue_token
from marketplace.models import Purchase, User


class ReportingTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create(username="report_admin", email="report_admin@example.com", password_hash="hash", role="admin", verified=True)
        self.student = User.objects.create(username="report_student", email="report_student@example.com", password_hash="hash", verified=True)
        self.admin_client = Client(HTTP_AUTHORIZATION=f"Bearer {issue_token(self.admin)}")
        self.student_client = Client(HTTP_AUTHORIZATION=f"Bearer {issue_token(self.student)}")

    def order(self, item_id, name, quantity, total, status="completed", purchased_at=None):
        purchase = Purchase.objects.create(
            buyer_id=self.student.id, buyer_username=self.student.username,
            item_id=item_id, item_name=name, price=total / quantity, category="Books",
            seller_id=self.admin.id, seller_username=self.admin.username,
            quantity=quantity, total_amount=total, status=status, payment_status="paid",
        )
        if purchased_at:
            # purchased_at is set automatically, so overwrite it for date-range tests.
            Purchase.objects.filter(pk=purchase.pk).update(purchased_at=purchased_at)
        return purchase

    def report(self, query=""):
        return self.admin_client.get(f"/api/admin/reports?admin_id={self.admin.id}&{query}")

    def test_totals_count_completed_orders_only(self):
        """FR4.1 and FR4.3: totals come only from completed orders."""
        self.order(1, "Maths textbook", 2, 40.00)
        self.order(2, "Calculator", 1, 20.00)
        self.order(3, "Pending item", 1, 99.00, status="pending")
        self.order(4, "Cancelled item", 1, 50.00, status="cancelled")
        data = self.report().json()
        self.assertEqual(data["total_orders"], 2)
        self.assertEqual(data["total_items_sold"], 3)
        self.assertEqual(data["total_sales"], 60.00)
        self.assertEqual(data["average_order_value"], 30.00)

    def test_top_items_are_ranked_by_units_sold(self):
        """FR4.1: top-selling items are listed, best seller first."""
        self.order(1, "Maths textbook", 1, 20.00)
        self.order(1, "Maths textbook", 2, 40.00)
        self.order(2, "Calculator", 1, 15.00)
        top = self.report().json()["top_items"]
        self.assertEqual([item["item_name"] for item in top], ["Maths textbook", "Calculator"])
        self.assertEqual(top[0]["units_sold"], 3)
        self.assertEqual(top[0]["revenue"], 60.00)

    def test_date_range_uses_fiji_time(self):
        """FR4.2: 22:30 UTC on 20 Oct is 10:30 am on 21 Oct in Fiji."""
        self.order(1, "Morning sale", 1, 25.00, purchased_at=datetime(2026, 10, 20, 22, 30, tzinfo=timezone.utc))
        on_fiji_day = self.report("from=2026-10-21&to=2026-10-21").json()
        self.assertEqual(on_fiji_day["total_orders"], 1)
        self.assertEqual(on_fiji_day["rows"][0]["date"], "2026-10-21")
        day_before = self.report("from=2026-10-20&to=2026-10-20").json()
        self.assertEqual(day_before["total_orders"], 0)

    def test_invalid_dates_return_a_clear_error(self):
        """FR4.2 and NFR3.2: bad input gives a 400 message, not a server crash."""
        for query in ("from=2026-13-45", "to=not-a-date", "from=2026-10-20&to=2026-10-01"):
            response = self.report(query)
            self.assertEqual(response.status_code, 400, query)
            self.assertIn("date", response.json()["detail"].lower())

    def test_pdf_export_returns_a_pdf(self):
        """FR4.4: the export is a single downloadable PDF."""
        self.order(1, "Maths textbook", 1, 20.00)
        response = self.admin_client.get(f"/api/admin/reports/pdf?admin_id={self.admin.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_reports_and_pdf_are_admin_only(self):
        """FR4.5 and NFR2.4: access is enforced on the server."""
        for path in ("/api/admin/reports", "/api/admin/reports/pdf"):
            self.assertEqual(Client().get(f"{path}?admin_id={self.admin.id}").status_code, 401)
            self.assertEqual(self.student_client.get(f"{path}?admin_id={self.student.id}").status_code, 403)
