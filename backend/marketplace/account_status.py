from django.utils import timezone

from .models import User


def restore_expired_suspension(user):
    """Restore access on the first login/request after a timed suspension ends."""
    if user and user.status == "suspended" and user.suspended_until and user.suspended_until <= timezone.now():
        User.objects.filter(id=user.id, status="suspended", suspended_until__lte=timezone.now()).update(
            status="active", updated_at=timezone.now(),
        )
        user.refresh_from_db()
    return user
