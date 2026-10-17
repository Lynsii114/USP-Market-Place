import re
from pathlib import Path

from django.test import Client, TestCase

from marketplace.authentication import issue_token
from marketplace.category_catalog import BUILTIN_CATEGORIES
from marketplace.models import Category, Item, User
from marketplace import services
from testing_images import TEST_PHOTO


class CategoryTests(TestCase):
    def setUp(self):
        services.CATEGORY_TABLE_READY = True
        self.seller = User.objects.create(username="category_seller", email="seller@example.com", password_hash="hash", verified=True)
        self.admin = User.objects.create(username="category_admin", email="admin@example.com", password_hash="hash", role="admin")
        self.client = Client(HTTP_AUTHORIZATION=f"Bearer {issue_token(self.seller)}")
        self.admin_client = Client(HTTP_AUTHORIZATION=f"Bearer {issue_token(self.admin)}")

    def payload(self, category):
        return {"name": "Campus item", "price": 10, "description": "Used item", "category": category, "contact": "Campus", "stock": 1, "photo": TEST_PHOTO}

    def test_builtin_options_exist_without_database_seeding(self):
        response = Client().get("/api/categories")
        self.assertEqual(response.status_code, 200)
        self.assertEqual({option["name"] for option in response.json()}, {name for name, _ in BUILTIN_CATEGORIES})
        self.assertEqual(response.json()[-1]["name"], "Other")
        self.assertTrue(all(option["built_in"] for option in response.json()))

    def test_each_new_category_can_be_saved_and_edited(self):
        for name in ("Study Supplies", "Sports & Fitness", "Personal Care", "Other"):
            with self.subTest(name=name):
                response = self.client.post("/api/items", self.payload(name), content_type="application/json")
                self.assertEqual(response.status_code, 200, response.content)
                self.assertEqual(response.json()["category"], name)
                edited = self.client.put(f"/api/items/{response.json()['id']}", {"category": "Footwear"}, content_type="application/json")
                self.assertEqual(edited.status_code, 200, edited.content)

    def test_legacy_footwares_listings_display_as_footwear(self):
        item = Item.objects.create(name="Legacy shoes", price=10, description="Used", category="Footwares", contact="Campus", stock=1, seller_id=self.seller.id, seller_username=self.seller.username)
        self.assertEqual(Client().get(f"/api/items/{item.id}").json()["category"], "Footwear")
        item.refresh_from_db()
        self.assertEqual(item.category, "Footwares")  # Compatibility needs no destructive migration.
        response = self.client.post("/api/items", self.payload("footwares"), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Item.objects.get(id=response.json()["id"]).category, "Footwear")

    def test_database_defaults_do_not_duplicate_builtin_options(self):
        for name in ("Footwares", "Footwear", "Other", "Books"):
            Category.objects.create(name=name)
        Category.objects.create(name="Accessories")
        names = [option["name"] for option in Client().get("/api/categories").json()]
        self.assertEqual(names.count("Footwear"), 1)
        self.assertNotIn("Footwares", names)
        self.assertIn("Accessories", names)
        self.assertEqual(names[-1], "Other")

    def test_builtin_duplicates_and_database_mutations_are_blocked(self):
        for name in ("Footwares", "footwear", "Other", "Sports & Fitness"):
            response = self.admin_client.post("/api/admin/categories", {"name": name}, content_type="application/json")
            self.assertEqual(response.status_code, 409)
        legacy = Category.objects.create(name="Footwares")
        self.assertEqual(self.admin_client.put(f"/api/admin/categories/{legacy.id}", {"name": "Shoes"}, content_type="application/json").status_code, 403)
        self.assertEqual(self.admin_client.delete(f"/api/admin/categories/{legacy.id}").status_code, 403)

    def test_custom_categories_remain_manageable_without_stranding_items(self):
        response = self.admin_client.post("/api/admin/categories", {"name": "Accessories"}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        category_id = response.json()["id"]
        listing = self.client.post("/api/items", self.payload("Accessories"), content_type="application/json")
        self.assertEqual(listing.status_code, 200)
        response = self.admin_client.put(f"/api/admin/categories/{category_id}", {"name": "Travel Accessories"}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Item.objects.get(id=listing.json()["id"]).category, "Travel Accessories")
        self.assertEqual(self.admin_client.delete(f"/api/admin/categories/{category_id}").status_code, 409)

    def test_frontend_and_backend_builtin_catalogs_match(self):
        path = Path(__file__).resolve().parents[3] / "frontend" / "src" / "data" / "categories.js"
        frontend_names = set(re.findall(r'name: "([^"]+)"', path.read_text(encoding="utf-8")))
        self.assertEqual(frontend_names, {name for name, _ in BUILTIN_CATEGORIES})
