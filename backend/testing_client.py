"""Explicit authenticated actors for existing business-flow tests.

Those tests select their actor via an ID. Issue a real signed credential for
that chosen test account. Authentication/impersonation regressions use the
unmodified Django Client in marketplace/tests/test_inventory.py instead.
"""
import json
import re
from urllib.parse import urlsplit, parse_qs

from django.test import Client

from marketplace.authentication import issue_token
from marketplace.models import User


class ActingUserClient(Client):
    def generic(self, method, path, data="", content_type="application/octet-stream", **extra):
        parsed = urlsplit(path)
        query = parse_qs(parsed.query)
        body = {}
        if content_type == "application/json" and data:
            body = json.loads(data)
        actor_id = None
        for key in ("admin_id", "seller_id", "sender_id", "reporter_id", "reviewer_id", "buyer_id", "user_id", "viewer_id"):
            value = body.get(key) if isinstance(body, dict) else None
            value = value if value is not None else query.get(key, [None])[0]
            if value is not None:
                actor_id = value
                break
        match = re.match(r"/api/users/(\d+)/", parsed.path)
        if match:
            actor_id = match.group(1)
        if actor_id is not None:
            user = User.objects.filter(id=actor_id).first()
            if user:
                extra["HTTP_AUTHORIZATION"] = f"Bearer {issue_token(user)}"
        return super().generic(method, path, data, content_type, **extra)
