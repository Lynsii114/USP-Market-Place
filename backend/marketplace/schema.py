from django.db import OperationalError, connection

from .models import Conversation, Item, Message, Purchase, User


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
        "name": "VARCHAR(128) NOT NULL DEFAULT ''",
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
    "conversations": {
        "buyer_id": "INTEGER NOT NULL DEFAULT 0",
        "buyer_username": "VARCHAR(64) NOT NULL DEFAULT ''",
        "seller_id": "INTEGER NOT NULL DEFAULT 0",
        "seller_username": "VARCHAR(64) NOT NULL DEFAULT ''",
        "item_id": "INTEGER NULL",
        "item_name": "VARCHAR(256) NULL",
        "created_at": "DATETIME NULL",
        "updated_at": "DATETIME NULL",
        "buyer_read_at": "DATETIME NULL",
        "seller_read_at": "DATETIME NULL",
        "buyer_last_read_message_id": "INTEGER NOT NULL DEFAULT 0",
        "seller_last_read_message_id": "INTEGER NOT NULL DEFAULT 0",
    },
    "messages": {
        "conversation_id": "INTEGER NOT NULL DEFAULT 0",
        "sender_id": "INTEGER NOT NULL DEFAULT 0",
        "sender_username": "VARCHAR(64) NOT NULL DEFAULT ''",
        "body": "VARCHAR(1000) NOT NULL DEFAULT ''",
        "created_at": "DATETIME NULL",
    },
}


def ensure_schema():
    existing_tables = connection.introspection.table_names()
    models = [User, Item, Purchase, Conversation, Message]

    with connection.schema_editor() as schema_editor:
        for model in models:
            if model._meta.db_table not in existing_tables:
                try:
                    schema_editor.create_model(model)
                except OperationalError:
                    pass

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
