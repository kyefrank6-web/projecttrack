from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import Resolver404, resolve

from .maintenance_utils import is_maintenance_mode, maintenance_message, user_is_platform_superadmin
from .models import Role, SchoolRegistrationStatus
from .profile_utils import get_active_profile


ALLOWED_WHILE_PENDING = {
    "home",
    "registration_pending",
    "registration_rejected",
    "registration_deactivated",
    "logout",
    "account_settings",
    "password_change",
    "password_change_done",
    "overall_upload_logo",
    "overall_observation_checklists",
    "overall_class_project_themes",
    "delete_observation_checklist",
}

ALLOWED_WHILE_MUST_CHANGE_PASSWORD = {
    "password_change",
    "password_change_done",
    "logout",
    "login",
}

ALLOWED_DURING_MAINTENANCE = {
    "login",
    "logout",
    "maintenance",
    "home",
}


class ActiveMembershipMiddleware:
    """Attach the active school membership (session) to each request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.active_profile = get_active_profile(request) if request.user.is_authenticated else None
        return self.get_response(request)


class MaintenanceMiddleware:
    """Block access for everyone except platform superadmins while updates run."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not is_maintenance_mode():
            return self.get_response(request)

        if user_is_platform_superadmin(request.user):
            return self.get_response(request)

        try:
            url_name = resolve(request.path_info).url_name
        except Resolver404:
            url_name = None

        if url_name in ALLOWED_DURING_MAINTENANCE:
            return self.get_response(request)

        if request.user.is_authenticated:
            logout(request)
            messages.warning(
                request,
                maintenance_message() + " You have been signed out.",
            )
            return redirect("login")

        return redirect("maintenance")


class SchoolApprovalMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            match = resolve(request.path_info)
            if match.url_name not in ALLOWED_WHILE_PENDING:
                profile = get_active_profile(request)
                if profile and profile.role != Role.SUPERADMIN and profile.school_id:
                    school = profile.school
                    if school.status == SchoolRegistrationStatus.PENDING:
                        return redirect("registration_pending")
                    if school.status == SchoolRegistrationStatus.REJECTED:
                        return redirect("registration_rejected")
                    if school.status == SchoolRegistrationStatus.DEACTIVATED:
                        return redirect("registration_deactivated")
        return self.get_response(request)


class MustChangePasswordMiddleware:
    """Force users with a one-time login password to change it before continuing."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            match = resolve(request.path_info)
            if match.url_name not in ALLOWED_WHILE_MUST_CHANGE_PASSWORD:
                profile = get_active_profile(request)
                if profile and profile.must_change_password:
                    return redirect("password_change")
        return self.get_response(request)
