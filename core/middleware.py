from __future__ import annotations

from django.shortcuts import redirect
from django.urls import resolve

from .models import Role, SchoolRegistrationStatus
from .profile_utils import get_active_profile


ALLOWED_WHILE_PENDING = {
    "home",
    "registration_pending",
    "registration_rejected",
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


class ActiveMembershipMiddleware:
    """Attach the active school membership (session) to each request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.active_profile = get_active_profile(request) if request.user.is_authenticated else None
        return self.get_response(request)


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
