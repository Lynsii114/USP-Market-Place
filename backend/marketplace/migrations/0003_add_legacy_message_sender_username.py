from django.db import migrations, models


class AddFieldIfMissing(migrations.AddField):
    """Adopt a legacy column when present, or add it with a safe default."""

    reversible = False

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        with schema_editor.connection.cursor() as cursor:
            columns = {
                column.name
                for column in schema_editor.connection.introspection.get_table_description(
                    cursor, model._meta.db_table
                )
            }
        field = model._meta.get_field(self.name)
        if field.column not in columns:
            super().database_forwards(app_label, schema_editor, from_state, to_state)


class Migration(migrations.Migration):
    dependencies = [("marketplace", "0002_repair_messaging_schema")]

    operations = [
        AddFieldIfMissing(
            model_name="message",
            name="sender_username",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
    ]
