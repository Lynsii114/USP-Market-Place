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
        "reserved_buyer_id": item.reserved_buyer_id,
        "reserved_buyer_username": item.reserved_buyer_username,
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
        "delivery_method": purchase.delivery_method,
        "delivery_fee": purchase.delivery_fee,
        "subtotal": purchase.subtotal,
        "included_tax_amount": purchase.included_tax_amount,
        "final_total": purchase.final_total,
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


def serialize_message(message):
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "sender_id": message.sender_id,
        "receiver_id": message.receiver_id,
        "body": message.body,
        "is_read": message.is_read,
        "created_at": message.created_at,
    }


def serialize_conversation(conversation, item=None, buyer=None, seller=None, messages=None, current_user_id=None):
    unread_count = 0
    serialized_messages = []
    if messages is not None:
        serialized_messages = [serialize_message(message) for message in messages]
        unread_count = sum(
            1
            for message in messages
            if current_user_id and message.receiver_id == int(current_user_id) and not message.is_read
        )

    return {
        "id": conversation.id,
        "item_id": conversation.item_id,
        "buyer_id": conversation.buyer_id,
        "seller_id": conversation.seller_id,
        "buyer_username": buyer.username if buyer else "",
        "seller_username": seller.username if seller else "",
        "item": serialize_item(item) if item else None,
        "messages": serialized_messages,
        "unread_count": unread_count,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
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

