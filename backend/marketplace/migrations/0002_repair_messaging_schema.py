from django.db import migrations


MESSAGING_COLUMNS = {
    "Conversation": ("item_id", "buyer_id", "seller_id"),
    "Message": ("conversation_id", "sender_id", "receiver_id", "body", "is_read", "created_at"),
}


def repair_messaging_schema(apps, schema_editor):
    connection = schema_editor.connection
    existing_tables = set(connection.introspection.table_names())

    for model_name, required_columns in MESSAGING_COLUMNS.items():
        model = apps.get_model("marketplace", model_name)
        table = model._meta.db_table
        if table not in existing_tables:
            raise RuntimeError(
                f"Expected {table} to exist after the marketplace baseline migration."
            )

        with connection.cursor() as cursor:
            existing_columns = {
                column.name
                for column in connection.introspection.get_table_description(cursor, table)
            }
            missing_fields = [
                model._meta.get_field(field_name)
                for field_name in required_columns
                if model._meta.get_field(field_name).column not in existing_columns
            ]
            if missing_fields:
                cursor.execute(f"SELECT COUNT(*) FROM {schema_editor.quote_name(table)}")
                row_count = cursor.fetchone()[0]
                if row_count:
                    missing_names = ", ".join(field.name for field in missing_fields)
                    raise RuntimeError(
                        f"Cannot safely add {table}.{missing_names}: {row_count} existing rows "
                        "need verified values first. No rows were changed."
                    )

        for field in missing_fields:
            schema_editor.add_field(model, field)

    conversation = apps.get_model("marketplace", "Conversation")
    expected_columns = ["item_id", "buyer_id", "seller_id"]
    with connection.cursor() as cursor:
        indexes = connection.introspection.get_constraints(cursor, conversation._meta.db_table)
        has_composite_unique = any(
            details.get("unique")
            and len(details.get("columns", [])) == len(expected_columns)
            and set(details.get("columns", [])) == set(expected_columns)
            for details in indexes.values()
        )
        if has_composite_unique:
            return

        table = schema_editor.quote_name(conversation._meta.db_table)
        columns = ", ".join(schema_editor.quote_name(name) for name in expected_columns)
        cursor.execute(
            f"SELECT 1 FROM {table} GROUP BY {columns} HAVING COUNT(*) > 1 LIMIT 1"
        )
        if cursor.fetchone():
            raise RuntimeError(
                "Cannot add the conversation composite unique constraint: duplicate "
                "(item_id, buyer_id, seller_id) rows exist. No rows were changed."
            )

    constraint = next(
        constraint
        for constraint in conversation._meta.constraints
        if constraint.fields == tuple(expected_columns)
    )
    schema_editor.add_constraint(conversation, constraint)


class Migration(migrations.Migration):
    dependencies = [("marketplace", "0001_initial")]

    operations = [
        migrations.RunPython(repair_messaging_schema, migrations.RunPython.noop),
    ]
