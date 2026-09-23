import logging

from django.db import DatabaseError, OperationalError, connection

from .models import AdminNotification, EmailVerification, Item, PasswordReset, PendingRegistration, Purchase, RatingReview, User, UserReport


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
        "removed_reason": "VARCHAR(255) NULL",
        "created_at": "DATETIME NULL",
    },
    "users": {
        "student_id": "VARCHAR(32) NULL",
        "authenticator_secret": "VARCHAR(32) NULL",
        "authenticator_enabled": "BOOLEAN NOT NULL DEFAULT 0",
        "role": "VARCHAR(20) NOT NULL DEFAULT 'student'",
        "status": "VARCHAR(20) NOT NULL DEFAULT 'active'",
        "created_at": "DATETIME NULL",
    },
    "purchases": {
        "seller_contact": "VARCHAR(128) NOT NULL DEFAULT ''",
        "quantity": "INTEGER NOT NULL DEFAULT 1",
        "total_amount": "FLOAT NOT NULL DEFAULT 0",
        "status": "VARCHAR(32) NOT NULL DEFAULT 'completed'",
        "purchased_at": "DATETIME NULL",
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
        "created_at": "DATETIME NULL",
    },
}

logger = logging.getLogger(__name__)


def ensure_schema():
    models = [User, EmailVerification, PasswordReset, PendingRegistration, Item, Purchase, AdminNotification, UserReport, RatingReview]

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
    except (DatabaseError, OperationalError) as exc:
        logger.warning("Could not update database schema: %s", exc)
        connection.close()
