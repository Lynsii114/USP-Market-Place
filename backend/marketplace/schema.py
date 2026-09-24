import logging

from django.db import DatabaseError, OperationalError, connection

from .models import AdminNotification, Conversation, EmailVerification, Item, Message, PasswordReset, PendingRegistration, Purchase, RatingReview, User, UserReport


TABLE_COLUMNS = {
    "items": {
        "description": "VARCHAR(1000) NOT NULL DEFAULT ''",
        "category": "VARCHAR(64) NOT NULL DEFAULT 'Other'",
        "contact": "VARCHAR(128) NOT NULL DEFAULT ''",
        "photo": "TEXT NULL",
        "stock": "INTEGER NOT NULL DEFAULT 1",
        "status": "VARCHAR(32) NOT NULL DEFAULT 'available'",
        "seller_id": "INTEGER NOT NULL DEFAULT 0",
        "seller_username": "VARCHAR(64) NOT NULL DEFAULT 'Unknown'",
        "reserved_buyer_id": "INTEGER NULL",
        "reserved_buyer_username": "VARCHAR(64) NULL",
        "removed_reason": "VARCHAR(255) NULL",
        "created_at": "DATETIME NULL",
    },
    "users": {
        "student_id": "VARCHAR(32) NULL",
        "name": "VARCHAR(128) NOT NULL DEFAULT ''",
        "role": "VARCHAR(20) NOT NULL DEFAULT 'student'",
        "status": "VARCHAR(20) NOT NULL DEFAULT 'active'",
        "verified": "BOOLEAN NOT NULL DEFAULT 0",
        "confirmation_code": "VARCHAR(64) NULL",
        "authenticator_enabled": "BOOLEAN NOT NULL DEFAULT 0",
        "authenticator_secret": "VARCHAR(32) NULL",
        "created_at": "DATETIME NULL",
        "updated_at": "DATETIME NULL",
    },
    "purchases": {
        "seller_contact": "VARCHAR(128) NOT NULL DEFAULT ''",
        "quantity": "INTEGER NOT NULL DEFAULT 1",
        "total_amount": "FLOAT NOT NULL DEFAULT 0",
        "payment_method": "VARCHAR(32) NOT NULL DEFAULT 'cash'",
        "delivery_method": "VARCHAR(32) NOT NULL DEFAULT 'self_pickup'",
        "delivery_fee": "FLOAT NOT NULL DEFAULT 0",
        "subtotal": "FLOAT NOT NULL DEFAULT 0",
        "included_tax_amount": "FLOAT NOT NULL DEFAULT 0",
        "final_total": "FLOAT NOT NULL DEFAULT 0",
        "status": "VARCHAR(32) NOT NULL DEFAULT 'completed'",
        "order_stage": "VARCHAR(32) NOT NULL DEFAULT 'completed'",
        "purchased_at": "DATETIME NULL",
        "updated_at": "DATETIME NULL",
    },
    "admin_notifications": {
        "category": "VARCHAR(40) NOT NULL DEFAULT 'activity'",
        "actor_id": "INTEGER NULL",
        "actor_username": "VARCHAR(64) NULL",
        "is_read": "BOOLEAN NOT NULL DEFAULT 0",
        "created_at": "DATETIME NULL",
    },
    "user_reports": {
        "status": "VARCHAR(32) NOT NULL DEFAULT 'open'",
        "created_at": "DATETIME NULL",
    },
    "rating_reviews": {
        "purchase_id": "INTEGER NULL",
        "created_at": "DATETIME NULL",
    },
    "conversations": {
        "item_id": "INTEGER NOT NULL DEFAULT 0",
        "buyer_id": "INTEGER NOT NULL DEFAULT 0",
        "seller_id": "INTEGER NOT NULL DEFAULT 0",
        "created_at": "DATETIME NULL",
        "updated_at": "DATETIME NULL",
    },
    "messages": {
        "conversation_id": "INTEGER NOT NULL DEFAULT 0",
        "sender_id": "INTEGER NOT NULL DEFAULT 0",
        "receiver_id": "INTEGER NOT NULL DEFAULT 0",
        "body": "VARCHAR(1000) NOT NULL DEFAULT ''",
        "is_read": "BOOLEAN NOT NULL DEFAULT 0",
        "created_at": "DATETIME NULL",
    },
}

USER_COLUMN_ORDER = [
    ("student_id", "VARCHAR(32) NULL", "id"),
    ("name", "VARCHAR(128) NOT NULL DEFAULT ''", "student_id"),
    ("username", "VARCHAR(64) NOT NULL", "name"),
    ("email", "VARCHAR(128) NOT NULL", "username"),
    ("password_hash", "VARCHAR(255) NOT NULL", "email"),
    ("role", "VARCHAR(20) NOT NULL DEFAULT 'student'", "password_hash"),
    ("status", "VARCHAR(20) NOT NULL DEFAULT 'active'", "role"),
    ("verified", "BOOLEAN NOT NULL DEFAULT 0", "status"),
    ("confirmation_code", "VARCHAR(64) NULL", "verified"),
    ("authenticator_enabled", "BOOLEAN NOT NULL DEFAULT 0", "confirmation_code"),
    ("authenticator_secret", "VARCHAR(32) NULL", "authenticator_enabled"),
    ("created_at", "DATETIME NULL", "authenticator_secret"),
    ("updated_at", "DATETIME NULL", "created_at"),
]

logger = logging.getLogger(__name__)


def ensure_schema():
    models = [User, EmailVerification, PasswordReset, PendingRegistration, Item, Purchase, AdminNotification, Conversation, Message, UserReport, RatingReview]

    for model in models:
        try:
            existing_tables = connection.introspection.table_names()
            if model._meta.db_table not in existing_tables:
                with connection.schema_editor() as schema_editor:
                    schema_editor.create_model(model)
        except (DatabaseError, OperationalError) as exc:
            logger.warning("Could not create database table %s: %s", model._meta.db_table, exc)
            connection.close()
            return

    try:
        with connection.cursor() as cursor:
            for table_name, required_columns in TABLE_COLUMNS.items():
                if table_name not in connection.introspection.table_names():
                    continue

                existing_columns = {
                    column.name
                    for column in connection.introspection.get_table_description(cursor, table_name)
                }
                for column_name, column_definition in required_columns.items():
                    if column_name not in existing_columns:
                        cursor.execute(
                            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
                        )

            # Personal-email demo registrations do not have a student ID. Make the
            # legacy USP field nullable when upgrading an existing database.
            if "pending_registrations" in connection.introspection.table_names():
                cursor.execute(
                    "ALTER TABLE pending_registrations MODIFY COLUMN student_id VARCHAR(32) NULL"
                )
            if "users" in connection.introspection.table_names():
                cursor.execute("UPDATE users SET name = username WHERE name IS NULL OR name = ''")
                cursor.execute("UPDATE users SET verified = 1 WHERE status = 'active'")
                cursor.execute("UPDATE users SET updated_at = COALESCE(updated_at, created_at, NOW())")
                if connection.vendor == "mysql":
                    for column_name, column_definition, previous_column in USER_COLUMN_ORDER:
                        cursor.execute(
                            f"ALTER TABLE users MODIFY COLUMN {column_name} {column_definition} AFTER {previous_column}"
                        )
            if "messages" in connection.introspection.table_names() and "conversations" in connection.introspection.table_names():
                cursor.execute(
                    """
                    UPDATE messages m
                    JOIN conversations c ON c.id = m.conversation_id
                    SET m.receiver_id = CASE
                        WHEN m.sender_id = c.buyer_id THEN c.seller_id
                        ELSE c.buyer_id
                    END
                    WHERE m.receiver_id = 0
                    """
                )
    except (DatabaseError, OperationalError) as exc:
        logger.warning("Could not update database schema: %s", exc)
        connection.close()
