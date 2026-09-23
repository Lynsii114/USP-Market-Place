from django.urls import path

from . import views

urlpatterns = [
    path("health", views.health),
    path("users/signup", views.signup),
    path("users/verify-email", views.verify_email),
    path("users/resend-verification", views.resend_verification),
    path("users/cancel-verification", views.cancel_verification),
    path("users/request-password-reset", views.request_password_reset),
    path("users/reset-password", views.reset_password),
    path("users/login", views.login),
    path("users/verify-authenticator", views.verify_authenticator),
    path("users/<int:buyer_id>/purchases", views.list_buyer_purchases),
    path("users/<int:seller_id>/items", views.list_seller_items),
    path("items", views.items_collection),
    path("items/<int:item_id>", views.item_detail),
    path("items/<int:item_id>/purchase", views.purchase_item),
    path("admin/dashboard", views.admin_dashboard),
    path("admin/students", views.admin_students),
    path("admin/students/<int:student_id>/suspend", views.admin_suspend_student),
    path("admin/students/<int:student_id>/reactivate", views.admin_reactivate_student),
    path("admin/listings", views.admin_listings),
    path("admin/listings/<int:item_id>/remove", views.admin_remove_listing),
    path("admin/listings/<int:item_id>/restore", views.admin_restore_listing),
    path("admin/orders", views.admin_orders),
    path("admin/reports", views.admin_reports),
]
