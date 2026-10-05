from __future__ import annotations

from django.conf import settings
from django.db import DatabaseError

from .models import Role, UserProfile


def maintenance_forced_by_env() -> bool:
    return bool(getattr(settings, "MAINTENANCE_MODE", False))


def _platform_settings():
    from .models import PlatformSettings

    try:
        return PlatformSettings.get()
    except DatabaseError:
        return None


def is_maintenance_mode() -> bool:
    if maintenance_forced_by_env():
        return True
    platform = _platform_settings()
    return bool(platform and platform.maintenance_enabled)


def maintenance_message() -> str:
    default = getattr(
        settings,
        "MAINTENANCE_MESSAGE",
        "The system is temporarily unavailable while updates are applied. Please try again later.",
    )
    platform = _platform_settings()
    if platform:
        custom = (platform.maintenance_message or "").strip()
        if custom:
            return custom
    return default


def user_is_platform_superadmin(user) -> bool:
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    return UserProfile.objects.filter(user=user, role=Role.SUPERADMIN).exists()
