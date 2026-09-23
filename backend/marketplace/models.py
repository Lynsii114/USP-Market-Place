from django.db import models


class User(models.Model):
    username = models.CharField(max_length=64, unique=True, db_index=True)
    student_id = models.CharField(max_length=32, unique=True, db_index=True, null=True, blank=True)
    email = models.CharField(max_length=128, unique=True, db_index=True)
    password_hash = models.CharField(max_length=255)
    authenticator_secret = models.CharField(max_length=32, null=True, blank=True)
    authenticator_enabled = models.BooleanField(default=False)
    role = models.CharField(max_length=20, default="student")
    status = models.CharField(max_length=20, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "users"


class EmailVerification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    attempts = models.IntegerField(default=0)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "email_verifications"


class PasswordReset(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    attempts = models.IntegerField(default=0)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "password_resets"


class PendingRegistration(models.Model):
    username = models.CharField(max_length=64, unique=True, db_index=True)
    student_id = models.CharField(max_length=32, unique=True, db_index=True, null=True, blank=True)
    email = models.CharField(max_length=128, unique=True, db_index=True)
    password_hash = models.CharField(max_length=255)
    code_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    attempts = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pending_registrations"


class Item(models.Model):
    name = models.CharField(max_length=256)
    price = models.FloatField()
    description = models.CharField(max_length=1000)
    category = models.CharField(max_length=64)
    contact = models.CharField(max_length=128)
    photo = models.TextField(null=True, blank=True)
    stock = models.IntegerField(default=1)
    status = models.CharField(max_length=32, default="available")
    seller_id = models.IntegerField(db_index=True)
    seller_username = models.CharField(max_length=64)
    removed_reason = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "items"


class Purchase(models.Model):
    buyer_id = models.IntegerField(db_index=True)
    buyer_username = models.CharField(max_length=64)
    item_id = models.IntegerField(db_index=True)
    item_name = models.CharField(max_length=256)
    price = models.FloatField()
    category = models.CharField(max_length=64)
    seller_id = models.IntegerField(db_index=True)
    seller_username = models.CharField(max_length=64)
    seller_contact = models.CharField(max_length=128, default="")
    quantity = models.IntegerField(default=1)
    total_amount = models.FloatField(default=0)
    status = models.CharField(max_length=32, default="completed")
    purchased_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "purchases"
