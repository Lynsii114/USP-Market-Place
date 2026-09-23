def serialize_user(user):
    return {
        "id": user.id,
        "student_id": user.student_id,
        "name": user.name or user.username,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "verified": user.verified,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


def serialize_item(item):
    return {
        "id": item.id,
        "name": item.name,
        "price": item.price,
        "description": item.description,
        "category": item.category,
        "contact": item.contact,
        "photo": item.photo,
        "stock": item.stock,
        "status": item.status,
        "seller_id": item.seller_id,
        "seller_username": item.seller_username,
        "removed_reason": item.removed_reason,
        "created_at": item.created_at,
    }


def serialize_purchase(purchase):
    return {
        "id": purchase.id,
        "buyer_id": purchase.buyer_id,
        "buyer_username": purchase.buyer_username,
        "item_id": purchase.item_id,
        "item_name": purchase.item_name,
        "price": purchase.price,
        "category": purchase.category,
        "seller_id": purchase.seller_id,
        "seller_username": purchase.seller_username,
        "seller_contact": purchase.seller_contact,
        "quantity": purchase.quantity,
        "total_amount": purchase.total_amount,
        "payment_method": purchase.payment_method,
        "status": purchase.status,
        "order_stage": purchase.order_stage,
        "purchased_at": purchase.purchased_at,
        "updated_at": purchase.updated_at,
    }


def serialize_notification(notification):
    return {
        "id": notification.id,
        "title": notification.title,
        "message": notification.message,
        "category": notification.category,
        "actor_id": notification.actor_id,
        "actor_username": notification.actor_username,
        "is_read": notification.is_read,
        "created_at": notification.created_at,
    }


def serialize_user_report(report):
    return {
        "id": report.id,
        "reporter_id": report.reporter_id,
        "reporter_username": report.reporter_username,
        "target_type": report.target_type,
        "target_id": report.target_id,
        "target_label": report.target_label,
        "reason": report.reason,
        "status": report.status,
        "created_at": report.created_at,
    }


def serialize_rating_review(review):
    return {
        "id": review.id,
        "purchase_id": review.purchase_id,
        "reviewer_id": review.reviewer_id,
        "reviewer_username": review.reviewer_username,
        "item_id": review.item_id,
        "item_name": review.item_name,
        "seller_id": review.seller_id,
        "seller_username": review.seller_username,
        "rating": review.rating,
        "review": review.review,
        "created_at": review.created_at,
    }

