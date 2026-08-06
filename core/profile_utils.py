from __future__ import annotations

from django.http import HttpRequest

from .models import UserProfile


def get_active_profile(request: HttpRequest) -> UserProfile | None:
    if not request.user.is_authenticated:
        return None
    profile = getattr(request, "active_profile", None)
    if profile is not None:
        return profile
    mid = request.session.get("active_membership_id")
    if mid:
        profile = (
            UserProfile.objects.filter(pk=mid, user_id=request.user.id)
            .select_related("school")
            .first()
        )
        if profile:
            return profile
    return (
        UserProfile.objects.filter(user_id=request.user.id)
        .select_related("school")
        .order_by("id")
        .first()
    )


def set_active_membership(request: HttpRequest, membership: UserProfile) -> None:
    request.session["active_membership_id"] = membership.id
    request.active_profile = membership
