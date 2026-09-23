from django.db import models


class User(models.Model):
    student_id = models.CharField(max_length=32, unique=True, db_index=True, null=True, blank=True)
    name = models.CharField(max_length=128, default="", blank=True)
    username = models.CharField(max_length=64, unique=True, db_index=True)
    email = models.CharField(max_length=128, unique=True, db_index=True)
    password_hash = models.CharField(max_length=255)
    role = models.CharField(max_length=20, default="student")
    status = models.CharField(max_length=20, default="active")
    verified = models.BooleanField(default=False)
    confirmation_code = models.CharField(max_length=64, null=True, blank=True)
    authenticator_enabled = models.BooleanField(default=False)
    authenticator_secret = models.CharField(max_length=32, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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


class AdminNotification(models.Model):
    title = models.CharField(max_length=128)
    message = models.CharField(max_length=1000)
    category = models.CharField(max_length=40, default="activity")
    actor_id = models.IntegerField(null=True, blank=True)
    actor_username = models.CharField(max_length=64, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "admin_notifications"


class UserReport(models.Model):
    reporter_id = models.IntegerField(db_index=True)
    reporter_username = models.CharField(max_length=64)
    target_type = models.CharField(max_length=32)
    target_id = models.IntegerField(null=True, blank=True)
    target_label = models.CharField(max_length=256)
    reason = models.CharField(max_length=1000)
    status = models.CharField(max_length=32, default="open")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_reports"


class RatingReview(models.Model):
    reviewer_id = models.IntegerField(db_index=True)
    reviewer_username = models.CharField(max_length=64)
    item_id = models.IntegerField(db_index=True)
    item_name = models.CharField(max_length=256)
    seller_id = models.IntegerField(db_index=True)
    seller_username = models.CharField(max_length=64)
    rating = models.IntegerField(default=5)
    review = models.CharField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rating_reviews"
