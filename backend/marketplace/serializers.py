from .models import User


def user_display_name(user_id, fallback):
    user = User.objects.filter(id=user_id).first()
    if not user:
        return fallback
    return user.name or user.username or fallback


def serialize_user(user):
    return {
        "id": user.id,
        "name": user.name,
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


def serialize_message(message, conversation=None, current_user_id=None):
    is_seen_by_recipient = False
    if conversation and current_user_id == message.sender_id:
        if message.sender_id == conversation.buyer_id:
            is_seen_by_recipient = conversation.seller_last_read_message_id >= message.id
        elif message.sender_id == conversation.seller_id:
            is_seen_by_recipient = conversation.buyer_last_read_message_id >= message.id

    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "sender_id": message.sender_id,
        "sender_username": message.sender_username,
        "sender_name": user_display_name(message.sender_id, message.sender_username),
        "body": message.body,
        "created_at": message.created_at,
        "is_seen_by_recipient": is_seen_by_recipient,
    }


def serialize_conversation(conversation, latest_message=None, messages=None, current_user_id=None, unread_count=0):
    buyer_name = user_display_name(conversation.buyer_id, conversation.buyer_username)
    seller_name = user_display_name(conversation.seller_id, conversation.seller_username)
    data = {
        "id": conversation.id,
        "buyer_id": conversation.buyer_id,
        "buyer_username": conversation.buyer_username,
        "buyer_name": buyer_name,
        "seller_id": conversation.seller_id,
        "seller_username": conversation.seller_username,
        "seller_name": seller_name,
        "item_id": conversation.item_id,
        "item_name": conversation.item_name,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
        "buyer_read_at": conversation.buyer_read_at,
        "seller_read_at": conversation.seller_read_at,
        "buyer_last_read_message_id": conversation.buyer_last_read_message_id,
        "seller_last_read_message_id": conversation.seller_last_read_message_id,
        "unread_count": unread_count,
        "has_unread": unread_count > 0,
        "latest_message": serialize_message(latest_message, conversation, current_user_id) if latest_message else None,
    }
    if current_user_id is not None:
        data["current_user_id"] = current_user_id
    if messages is not None:
        data["messages"] = [
            serialize_message(message, conversation, current_user_id)
            for message in messages
        ]
    return data

