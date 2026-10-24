from django.db import connection
from django.db import DatabaseError
from django.test import TransactionTestCase, Client, override_settings
from unittest.mock import patch

from marketplace.authentication import issue_token
from marketplace.models import Conversation, Item, Message, User


class MessagingTests(TransactionTestCase):
    def setUp(self):
        self.seller = self.make_user("seller")
        self.buyer = self.make_user("buyer")
        self.item = Item.objects.create(
            name="Textbook",
            price=25,
            description="Used textbook",
            category="Books",
            contact="Campus pickup",
            seller_id=self.seller.id,
            seller_username=self.seller.username,
        )
        self.client = Client(HTTP_AUTHORIZATION=f"Bearer {issue_token(self.buyer)}")

    @staticmethod
    def make_user(username):
        return User.objects.create(
            username=username,
            email=f"{username}@example.com",
            password_hash="hash",
            status="active",
            verified=True,
        )

    def test_open_conversation_and_send_message(self):
        opened = self.client.post(
            f"/api/items/{self.item.id}/conversation", {}, content_type="application/json"
        )
        self.assertEqual(opened.status_code, 200, opened.content)
        conversation_id = opened.json()["id"]
        self.assertTrue(
            Conversation.objects.filter(
                id=conversation_id,
                item_id=self.item.id,
                buyer_id=self.buyer.id,
                seller_id=self.seller.id,
            ).exists()
        )

        reopened = self.client.post(
            f"/api/items/{self.item.id}/conversation", {}, content_type="application/json"
        )
        self.assertEqual(reopened.status_code, 200, reopened.content)
        self.assertEqual(Conversation.objects.count(), 1)

        sent = self.client.post(
            f"/api/conversations/{conversation_id}",
            {"body": "Is this still available?"},
            content_type="application/json",
        )
        self.assertEqual(sent.status_code, 200, sent.content)
        self.assertTrue(
            Message.objects.filter(
                conversation_id=conversation_id,
                sender_id=self.buyer.id,
                sender_username=self.buyer.username,
                receiver_id=self.seller.id,
                body="Is this still available?",
                is_read=False,
            ).exists()
        )

    def test_conversation_has_composite_unique_constraint(self):
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(
                cursor, Conversation._meta.db_table
            )
        expected_columns = ["item_id", "buyer_id", "seller_id"]
        self.assertTrue(
            any(
                details.get("unique")
                and len(details.get("columns", [])) == len(expected_columns)
                and set(details.get("columns", [])) == set(expected_columns)
                for details in constraints.values()
            ),
            constraints,
        )

    def test_receiver_can_read_history_and_marks_received_messages_read(self):
        conversation = Conversation.objects.create(
            item_id=self.item.id,
            buyer_id=self.buyer.id,
            seller_id=self.seller.id,
        )
        message = Message.objects.create(
            conversation_id=conversation.id,
            sender_id=self.buyer.id,
            receiver_id=self.seller.id,
            body="Can I collect this tomorrow?",
            is_read=False,
        )
        seller_client = Client(HTTP_AUTHORIZATION=f"Bearer {issue_token(self.seller)}")

        response = seller_client.get(f"/api/conversations/{conversation.id}?user_id={self.seller.id}")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["messages"][0]["id"], message.id)
        message.refresh_from_db()
        self.assertTrue(message.is_read)

    def test_messaging_models_expose_required_columns(self):
        self.assertEqual(
            {field.column for field in Conversation._meta.local_fields},
            {"id", "item_id", "buyer_id", "seller_id", "created_at", "updated_at"},
        )
        self.assertEqual(
            {field.column for field in Message._meta.local_fields},
            {"id", "conversation_id", "sender_id", "sender_username", "receiver_id", "body", "is_read", "created_at"},
        )

    @override_settings(DATABASE_MODE="railway")
    @patch("marketplace.services.notify_user", side_effect=DatabaseError("notification schema mismatch"))
    def test_railway_message_send_succeeds_if_notification_write_fails(self, notify):
        conversation = Conversation.objects.create(
            item_id=self.item.id,
            buyer_id=self.buyer.id,
            seller_id=self.seller.id,
        )

        response = self.client.post(
            f"/api/conversations/{conversation.id}",
            {"body": "A message that should still be delivered"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(
            Message.objects.filter(
                conversation_id=conversation.id,
                sender_id=self.buyer.id,
                body="A message that should still be delivered",
            ).exists()
        )
        notify.assert_called_once()
