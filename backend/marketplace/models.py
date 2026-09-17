from django.db import models


class User(models.Model):
    username = models.CharField(max_length=64, unique=True, db_index=True)
    email = models.CharField(max_length=128, unique=True, db_index=True)
    password_hash = models.CharField(max_length=255)
    role = models.CharField(max_length=20, default="student")
    status = models.CharField(max_length=20, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "users"


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
