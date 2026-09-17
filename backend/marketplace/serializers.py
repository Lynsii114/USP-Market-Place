def serialize_user(user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "created_at": user.created_at,
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
        "status": purchase.status,
        "purchased_at": purchase.purchased_at,
    }

