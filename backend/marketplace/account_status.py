from django.utils import timezone

from .models import User
from .exceptions import ApiError


def suspension_error(user):
    if user.suspended_until:
        deadline = timezone.localtime(user.suspended_until, timezone.get_fixed_timezone(720)).strftime("%d %b %Y at %I:%M %p Fiji time (UTC+12)")
        detail = f"Your USP Marketplace account is temporarily suspended until {deadline}. You cannot sign in or use your account during this period. Please check your email for the reason and review options."
    else:
        detail = "Your USP Marketplace account is suspended. You cannot sign in or use your account at this time. Please check your email for details or contact the administration team to request a review."
    return ApiError(detail, 403, code="account_suspended")


def restore_expired_suspension(user):
    """Restore access on the first login/request after a timed suspension ends."""
    if user and user.status == "suspended" and user.suspended_until and user.suspended_until <= timezone.now():
        User.objects.filter(id=user.id, status="suspended", suspended_until__lte=timezone.now()).update(
            status="active", updated_at=timezone.now(),
        )
        user.refresh_from_db()
    return user
