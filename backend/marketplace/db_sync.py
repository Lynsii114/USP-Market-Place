import logging
import os
import threading

import pymysql
from django.db import connection


logger = logging.getLogger(__name__)

APP_TABLES = [
    "users",
    "email_verifications",
    "password_resets",
    "pending_registrations",
    "items",
    "purchases",
    "admin_notifications",
    "user_notifications",
    "conversations",
    "messages",
    "user_reports",
    "rating_reviews",
]

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_sync_lock = threading.Lock()


def local_sync_enabled():
    return os.getenv("LOCAL_DB_SYNC", "0") == "1"


def should_sync_request(request, response):
    return (
        local_sync_enabled()
        and request.method in MUTATING_METHODS
        and response.status_code < 400
    )


def _local_connection():
    return pymysql.connect(
        host=os.getenv("LOCAL_DB_HOST", "localhost"),
        port=int(os.getenv("LOCAL_DB_PORT", "3306")),
        user=os.getenv("LOCAL_DB_USERNAME", "root"),
        password=os.getenv("LOCAL_DB_PASSWORD", ""),
        database=os.getenv("LOCAL_DB_DATABASE", "usp_marketplace"),
        autocommit=False,
    )


def _table_columns(cursor, table_name):
    cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
    return [row[0] for row in cursor.fetchall()]


def _select_sql(table_name, destination_columns):
    derived_columns = {
        "items": {"user_id": "seller_id"},
        "users": {"is_verified": "verified"},
        "conversations": {
            "buyer_username": "COALESCE(buyer.username, '')",
            "seller_username": "COALESCE(seller.username, '')",
            "item_name": "COALESCE(items.name, '')",
            "buyer_read_at": "NULL",
            "seller_read_at": "NULL",
            "buyer_last_read_message_id": "0",
            "seller_last_read_message_id": "0",
        },
        "messages": {
            "sender_username": "COALESCE(sender.username, '')",
        },
    }
    joins = {
        "conversations": """
            LEFT JOIN users buyer ON buyer.id = conversations.buyer_id
            LEFT JOIN users seller ON seller.id = conversations.seller_id
            LEFT JOIN items ON items.id = conversations.item_id
        """,
        "messages": "LEFT JOIN users sender ON sender.id = messages.sender_id",
    }

    cloud_columns = _table_columns(connection.cursor(), table_name)
    table_derived = derived_columns.get(table_name, {})
    expressions = []
    selected_columns = []
    for column in destination_columns:
        if column in cloud_columns:
            expressions.append(f"`{table_name}`.`{column}`")
            selected_columns.append(column)
        elif column in table_derived:
            expressions.append(table_derived[column])
            selected_columns.append(column)

    if not expressions:
        return None, []

    return (
        f"SELECT {', '.join(expressions)} FROM `{table_name}` {joins.get(table_name, '')}",
        selected_columns,
    )


def sync_cloud_to_local():
    if not local_sync_enabled():
        return

    if not _sync_lock.acquire(blocking=False):
        return

    local = None
    try:
        local = _local_connection()
        local_cursor = local.cursor()
        cloud_cursor = connection.cursor()
        cloud_tables = set(connection.introspection.table_names())

        local.begin()
        local_cursor.execute("SET FOREIGN_KEY_CHECKS=0")
        try:
            for table_name in APP_TABLES:
                if table_name not in cloud_tables:
                    continue

                local_columns = _table_columns(local_cursor, table_name)
                select_sql, columns = _select_sql(table_name, local_columns)
                if not select_sql:
                    continue

                cloud_cursor.execute(select_sql)
                rows = cloud_cursor.fetchall()
                local_cursor.execute(f"DELETE FROM `{table_name}`")
                if rows:
                    column_sql = ", ".join(f"`{column}`" for column in columns)
                    placeholders = ", ".join(["%s"] * len(columns))
                    local_cursor.executemany(
                        f"INSERT INTO `{table_name}` ({column_sql}) VALUES ({placeholders})",
                        rows,
                    )
            local_cursor.execute("SET FOREIGN_KEY_CHECKS=1")
            local.commit()
        except Exception:
            local.rollback()
            raise
    except Exception as exc:
        logger.warning("Could not sync Aiven database to local MySQL: %s", exc)
    finally:
        if local is not None:
            local.close()
        _sync_lock.release()
