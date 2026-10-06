from __future__ import annotations

from django.utils import timezone

from .maintenance_utils import is_maintenance_mode, maintenance_message
from .school_utils import current_school_term
from .models import Role, SecondaryClassLevel, UserProfile
from .themes import DEFAULT_THEME_KEY, get_theme


def _dashboard_url_name(role: str | None) -> str | None:
    if role == Role.SUPERADMIN:
        return "superadmin_dashboard"
    if role == Role.OVERALL_SUPERVISOR:
        return "overall_dashboard"
    if role == Role.SUPERVISOR:
        return "supervisor_dashboard"
    return None


def navigation(request):
    role = None
    dashboard_url_name = None
    nav_school = None
    school_theme = get_theme(DEFAULT_THEME_KEY)

    if request.user.is_authenticated:
        profile = getattr(request, "active_profile", None)
        if not profile:
            profile = (
                UserProfile.objects.select_related("school")
                .filter(user_id=request.user.id)
                .first()
            )
        if profile:
            role = profile.role
            dashboard_url_name = _dashboard_url_name(role)
            if profile.school_id:
                nav_school = profile.school
                school_theme = get_theme(nav_school.theme)

    return {
        "maintenance_mode": is_maintenance_mode(),
        "maintenance_message": maintenance_message(),
        "nav_role": role,
        "Role": Role,
        "nav_class_levels": [c for c, _ in SecondaryClassLevel.choices],
        "dashboard_url_name": dashboard_url_name,
        "nav_school": nav_school,
        "school_theme": school_theme,
        "current_term": current_school_term(),
        "current_year": timezone.now().year,
    }
