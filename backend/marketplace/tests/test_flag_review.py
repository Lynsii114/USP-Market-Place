from unittest.mock import patch

from django.test import Client, TestCase, override_settings

from marketplace import services
from marketplace.authentication import issue_token
from marketplace.models import Item, User, UserNotification, UserReport
from testing_images import TEST_PHOTO


@override_settings(EMAIL_PROVIDER="smtp", EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend")
class FlagReviewTests(TestCase):
    def setUp(self):
        email_patch = patch("marketplace.services.send_email")
        self.send_email = email_patch.start()
        self.addCleanup(email_patch.stop)
        self.admin = User.objects.create(username="flag_admin", email="admin@example.com", password_hash="hash", role="admin", verified=True)
        self.reporter = User.objects.create(username="flag_reporter", email="reporter@example.com", password_hash="hash", verified=True)
        self.seller = User.objects.create(username="flag_seller", email="seller@example.com", password_hash="hash", verified=True)
        self.item = Item.objects.create(name="Exact flagged book", price=25, description="Original listing description", category="Books", photo=TEST_PHOTO, contact="Campus", stock=2, seller_id=self.seller.id, seller_username=self.seller.username)
        self.customer = Client(HTTP_AUTHORIZATION=f"Bearer {issue_token(self.reporter)}")
        self.admin_client = Client(HTTP_AUTHORIZATION=f"Bearer {issue_token(self.admin)}")

    def submit(self, **changes):
        return self.customer.post("/api/reports", {"target_type": "listing", "target_id": self.item.id, "listing_id": self.item.id, "reason": "This item appears to be a prohibited listing.", **changes}, content_type="application/json")

    def review(self, record, **changes):
        return self.admin_client.post(f"/api/admin/user-reports/{record.id}", {"action": "warning", "reason": "Please correct the misleading information in your listing.", "expected_status": record.status, **changes}, content_type="application/json")

    def test_listing_report_retains_exact_listing_and_reporter(self):
        response = self.submit(target_label="Spoofed title")
        self.assertEqual(response.status_code, 200, response.content)
        record = UserReport.objects.get()
        self.assertEqual(record.listing_id, self.item.id)
        self.assertEqual(record.target_label, self.item.name)
        self.assertEqual(record.listing_snapshot["photo"], TEST_PHOTO)
        self.assertEqual(record.reporter_id, self.reporter.id)
        data = services.list_user_reports(self.admin.id)[0]
        self.assertEqual(data["reporter"]["email"], self.reporter.email)
        self.assertEqual(data["seller"]["id"], self.seller.id)

    def test_seller_report_links_listing_and_checks_ownership(self):
        response = self.submit(target_type="user", target_id=self.seller.id)
        self.assertEqual(response.status_code, 200, response.content)
        record = UserReport.objects.get()
        self.assertEqual(record.listing_snapshot["id"], self.item.id)
        self.assertEqual(record.target_id, self.seller.id)
        self.assertEqual(self.submit(target_type="user", target_id=self.reporter.id).status_code, 422)
        self.assertEqual(UserReport.objects.count(), 1)

    def test_snapshot_survives_listing_edits_and_deletion(self):
        self.submit()
        original_id = self.item.id
        self.item.name = "Edited after report"
        self.item.description = "Changed description"
        self.item.save()
        data = services.list_user_reports(self.admin.id)[0]
        self.assertEqual(data["listing_snapshot"]["name"], "Exact flagged book")
        self.assertEqual(data["target_item"]["name"], "Edited after report")
        self.item.delete()
        data = services.list_user_reports(self.admin.id)[0]
        self.assertEqual(data["listing_id"], original_id)
        self.assertEqual(data["listing_snapshot"]["description"], "Original listing description")
        self.assertEqual(data["listing_snapshot"]["photo"], TEST_PHOTO)
        self.assertIsNone(data["target_item"])
        self.assertFalse(data["listing_available"])
        self.assertEqual(data["seller"]["id"], self.seller.id)

    def test_legacy_reports_have_clear_current_listing_fallback(self):
        UserReport.objects.create(reporter_id=self.reporter.id, reporter_username=self.reporter.username, target_type="listing", target_id=self.item.id, target_label=self.item.name, reason="An older reported listing")
        data = services.list_user_reports(self.admin.id)[0]
        self.assertEqual(data["listing_snapshot"], {})
        self.assertEqual(data["target_item"]["id"], self.item.id)
        self.assertEqual(data["target_item"]["photo"], TEST_PHOTO)

    def test_warning_keeps_listing_and_emails_reason_to_seller(self):
        self.submit()
        record = UserReport.objects.get()
        reason = "Please correct misleading details in this listing."
        response = self.review(record, reason=reason)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["email_status"], "sent")
        record.refresh_from_db()
        self.assertEqual(record.status, "warned")
        self.assertEqual(record.email_status, "sent")
        self.assertEqual(record.reviewed_by_id, self.admin.id)
        self.assertEqual(record.review_notes, reason)
        self.assertIsNotNone(record.reviewed_at)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, "available")
        self.assertEqual(self.send_email.call_args.args[2], self.seller.email)
        self.assertIn(reason, self.send_email.call_args.args[1])
        self.assertIn(self.item.name, self.send_email.call_args.args[1])
        self.assertTrue(UserNotification.objects.filter(user_id=self.seller.id, title="Marketplace warning").exists())
        self.assertTrue(UserNotification.objects.filter(user_id=self.reporter.id).exists())
        self.assertEqual(self.review(record).status_code, 409)
        self.assertEqual(self.send_email.call_count, 1)

    def test_delete_removes_listing_from_marketplace_and_emails_seller(self):
        self.submit()
        record = UserReport.objects.get()
        response = self.review(record, action="delete", reason="This listing contains a prohibited item.")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(Item.objects.filter(id=self.item.id).exists())
        self.assertFalse(services.public_items().filter(id=self.item.id).exists())
        self.assertEqual(self.send_email.call_args.args[2], self.seller.email)
        self.assertIn("deleted", self.send_email.call_args.args[1])
        record.refresh_from_db()
        self.assertEqual(record.status, "deleted")
        self.assertEqual(record.listing_snapshot["name"], self.item.name)
        self.assertEqual(self.review(record, action="delete").status_code, 409)
        self.assertEqual(self.send_email.call_count, 1)

    def test_warning_can_be_escalated_to_deletion(self):
        self.submit()
        record = UserReport.objects.get()
        self.assertEqual(self.review(record).status_code, 200)
        record.refresh_from_db()
        self.assertEqual(self.review(record, action="delete").status_code, 200)
        self.assertEqual(self.send_email.call_count, 2)

    def test_only_warning_and_delete_with_valid_reasons_are_allowed(self):
        self.submit()
        record = UserReport.objects.get()
        for changes in ({"action": "hide"}, {"action": "resolve"}, {"action": "dismiss"}, {"reason": ""}, {"reason": "x" * 501}):
            with self.subTest(changes=changes):
                self.assertEqual(self.review(record, **changes).status_code, 422)
        self.send_email.assert_not_called()
        self.assertEqual(self.review(record).status_code, 200)
        self.assertEqual(self.review(record, action="delete").status_code, 409)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, "available")

    def test_email_failure_is_reported_and_recorded(self):
        self.send_email.side_effect = RuntimeError("SMTP unavailable")
        self.submit()
        record = UserReport.objects.get()
        response = self.review(record)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["email_status"], "failed")
        record.refresh_from_db()
        self.assertEqual(record.email_status, "failed")
        self.assertEqual(record.status, "warned")
        self.assertIn("listing action succeeded", response.json()["message"])

    def test_unavailable_listing_or_seller_does_not_send_invalid_actions(self):
        self.submit()
        record = UserReport.objects.get()
        self.item.delete()
        self.assertEqual(self.review(record, action="delete").status_code, 409)
        self.seller.delete()
        self.assertEqual(self.review(record).status_code, 409)
        self.send_email.assert_not_called()

    def test_only_admin_can_read_flags_and_send_warning_or_delete(self):
        self.submit()
        record = UserReport.objects.get()
        path = f"/api/admin/user-reports/{record.id}"
        self.assertEqual(self.customer.get("/api/admin/user-reports").status_code, 403)
        for action in ("warning", "delete"):
            self.assertEqual(self.customer.post(path, {"action": action, "reason": "A valid test reason."}, content_type="application/json").status_code, 403)
        self.assertEqual(Client().get("/api/admin/user-reports").status_code, 401)
        self.assertEqual(self.admin_client.get("/api/admin/user-reports").status_code, 200)
        self.send_email.assert_not_called()

    def test_pending_email_blocks_overlapping_actions(self):
        self.submit()
        record = UserReport.objects.get()
        record.email_status = "pending"
        record.save(update_fields=["email_status"])
        self.assertEqual(self.review(record, action="delete").status_code, 409)
        self.send_email.assert_not_called()
