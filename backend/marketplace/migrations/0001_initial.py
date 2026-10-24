import django.core.serializers.json
import django.db.models.deletion
from django.db import migrations, models


class CreateModelIfMissing(migrations.CreateModel):
    """Apply a create-model operation only when its table is absent."""

    reversible = False

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.name)
        existing_tables = schema_editor.connection.introspection.table_names()
        if model._meta.db_table not in existing_tables:
            super().database_forwards(app_label, schema_editor, from_state, to_state)


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        CreateModelIfMissing(
            name='AdminNotification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=128)),
                ('message', models.CharField(max_length=1000)),
                ('category', models.CharField(default='activity', max_length=40)),
                ('actor_id', models.IntegerField(blank=True, null=True)),
                ('actor_username', models.CharField(blank=True, max_length=64, null=True)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'admin_notifications',
            },
        ),
        CreateModelIfMissing(
            name='Category',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=64, unique=True)),
                ('icon', models.CharField(blank=True, default='More', max_length=32)),
                ('image', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'categories',
            },
        ),
        CreateModelIfMissing(
            name='Item',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=256)),
                ('price', models.FloatField()),
                ('description', models.CharField(max_length=1000)),
                ('category', models.CharField(max_length=64)),
                ('contact', models.CharField(max_length=128)),
                ('payment_method', models.CharField(default='cash', max_length=16)),
                ('payment_number', models.CharField(blank=True, default='', max_length=32)),
                ('photo', models.TextField(blank=True, null=True)),
                ('stock', models.IntegerField(default=1)),
                ('multiple_units', models.BooleanField(default=False)),
                ('status', models.CharField(default='available', max_length=32)),
                ('seller_id', models.IntegerField(db_index=True)),
                ('seller_username', models.CharField(max_length=64)),
                ('reserved_buyer_id', models.IntegerField(blank=True, db_index=True, null=True)),
                ('reserved_buyer_username', models.CharField(blank=True, max_length=64, null=True)),
                ('removed_reason', models.CharField(blank=True, max_length=255, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'items',
            },
        ),
        CreateModelIfMissing(
            name='Message',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('conversation_id', models.IntegerField(db_index=True)),
                ('sender_id', models.IntegerField(db_index=True)),
                ('receiver_id', models.IntegerField(db_index=True)),
                ('body', models.CharField(max_length=1000)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'messages',
            },
        ),
        CreateModelIfMissing(
            name='PendingRegistration',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(db_index=True, max_length=64, unique=True)),
                ('student_id', models.CharField(blank=True, db_index=True, max_length=32, null=True, unique=True)),
                ('email', models.CharField(db_index=True, max_length=128, unique=True)),
                ('password_hash', models.CharField(max_length=255)),
                ('code_hash', models.CharField(max_length=64)),
                ('expires_at', models.DateTimeField()),
                ('attempts', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'pending_registrations',
            },
        ),
        CreateModelIfMissing(
            name='Purchase',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('buyer_id', models.IntegerField(db_index=True)),
                ('checkout_id', models.CharField(blank=True, db_index=True, max_length=64, null=True)),
                ('buyer_username', models.CharField(max_length=64)),
                ('item_id', models.IntegerField(db_index=True)),
                ('item_name', models.CharField(max_length=256)),
                ('price', models.FloatField()),
                ('category', models.CharField(max_length=64)),
                ('seller_id', models.IntegerField(db_index=True)),
                ('seller_username', models.CharField(max_length=64)),
                ('seller_contact', models.CharField(default='', max_length=128)),
                ('quantity', models.IntegerField(default=1)),
                ('total_amount', models.FloatField(default=0)),
                ('payment_method', models.CharField(default='cash', max_length=32)),
                ('delivery_method', models.CharField(default='self_pickup', max_length=32)),
                ('delivery_fee', models.FloatField(default=0)),
                ('subtotal', models.FloatField(default=0)),
                ('included_tax_amount', models.FloatField(default=0)),
                ('final_total', models.FloatField(default=0)),
                ('status', models.CharField(default='completed', max_length=32)),
                ('order_stage', models.CharField(default='payment_confirmed', max_length=32)),
                ('payment_status', models.CharField(blank=True, default='', max_length=20)),
                ('payment_reference', models.CharField(blank=True, default='', max_length=64)),
                ('purchased_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'purchases',
            },
        ),
        CreateModelIfMissing(
            name='RatingReview',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('purchase_id', models.IntegerField(blank=True, db_index=True, null=True)),
                ('reviewer_id', models.IntegerField(db_index=True)),
                ('reviewer_username', models.CharField(max_length=64)),
                ('item_id', models.IntegerField(db_index=True)),
                ('item_name', models.CharField(max_length=256)),
                ('seller_id', models.IntegerField(db_index=True)),
                ('seller_username', models.CharField(max_length=64)),
                ('rating', models.IntegerField(default=5)),
                ('review', models.CharField(max_length=1000)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'rating_reviews',
            },
        ),
        CreateModelIfMissing(
            name='User',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('student_id', models.CharField(blank=True, db_index=True, max_length=32, null=True, unique=True)),
                ('name', models.CharField(blank=True, default='', max_length=128)),
                ('username', models.CharField(db_index=True, max_length=64, unique=True)),
                ('email', models.CharField(db_index=True, max_length=128, unique=True)),
                ('password_hash', models.CharField(max_length=255)),
                ('role', models.CharField(default='student', max_length=20)),
                ('status', models.CharField(default='active', max_length=20)),
                ('suspension_reason', models.CharField(blank=True, default='', max_length=1000)),
                ('suspended_until', models.DateTimeField(blank=True, null=True)),
                ('verified', models.BooleanField(default=False)),
                ('confirmation_code', models.CharField(blank=True, max_length=64, null=True)),
                ('authenticator_enabled', models.BooleanField(default=False)),
                ('authenticator_secret', models.CharField(blank=True, max_length=32, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'users',
            },
        ),
        CreateModelIfMissing(
            name='UserNotification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.IntegerField(db_index=True)),
                ('title', models.CharField(max_length=128)),
                ('message', models.CharField(max_length=1000)),
                ('category', models.CharField(default='activity', max_length=40)),
                ('actor_id', models.IntegerField(blank=True, null=True)),
                ('actor_username', models.CharField(blank=True, max_length=64, null=True)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'user_notifications',
            },
        ),
        CreateModelIfMissing(
            name='UserReport',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reporter_id', models.IntegerField(db_index=True)),
                ('reporter_username', models.CharField(max_length=64)),
                ('target_type', models.CharField(max_length=32)),
                ('target_id', models.IntegerField(blank=True, null=True)),
                ('target_label', models.CharField(max_length=256)),
                ('reason', models.CharField(max_length=1000)),
                ('status', models.CharField(default='open', max_length=32)),
                ('listing_id', models.IntegerField(blank=True, db_index=True, null=True)),
                ('listing_snapshot', models.JSONField(blank=True, default=dict, encoder=django.core.serializers.json.DjangoJSONEncoder)),
                ('review_notes', models.CharField(blank=True, default='', max_length=1000)),
                ('reviewed_by_id', models.IntegerField(blank=True, null=True)),
                ('reviewed_by_username', models.CharField(blank=True, default='', max_length=64)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('email_status', models.CharField(blank=True, default='', max_length=16)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'user_reports',
            },
        ),
        CreateModelIfMissing(
            name='Conversation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_id', models.IntegerField(db_index=True)),
                ('buyer_id', models.IntegerField(db_index=True)),
                ('seller_id', models.IntegerField(db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'conversations',
                'constraints': [models.UniqueConstraint(fields=('item_id', 'buyer_id', 'seller_id'), name='marketplace_conversation_triplet_uniq')],
            },
        ),
        CreateModelIfMissing(
            name='PasswordReset',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code_hash', models.CharField(max_length=64)),
                ('expires_at', models.DateTimeField()),
                ('attempts', models.IntegerField(default=0)),
                ('used_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketplace.user')),
            ],
            options={
                'db_table': 'password_resets',
            },
        ),
        CreateModelIfMissing(
            name='EmailVerification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code_hash', models.CharField(max_length=64)),
                ('expires_at', models.DateTimeField()),
                ('attempts', models.IntegerField(default=0)),
                ('used_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marketplace.user')),
            ],
            options={
                'db_table': 'email_verifications',
            },
        ),
    ]
