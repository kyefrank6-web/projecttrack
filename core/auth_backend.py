from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.hashers import check_password

from .models import Role, UserProfile

User = get_user_model()


def _membership_password_ok(membership: UserProfile, password: str) -> bool:
    if membership.school_password:
        return check_password(password, membership.school_password)
    return check_password(password, membership.user.password)


def _password_grants_access(user, membership: UserProfile, password: str) -> bool:
    if _membership_password_ok(membership, password):
        return True
    if membership.role == Role.SUPERVISOR and check_password(password, user.password):
        return True
    # Platform superadmin: accept the Django user password as well.
    if membership.role == Role.SUPERADMIN and check_password(password, user.password):
        return True
    return False


def _matching_school_password_memberships(
    memberships: list[UserProfile], password: str
) -> list[UserProfile]:
    return [
        membership
        for membership in memberships
        if membership.school_password and check_password(password, membership.school_password)
    ]


def _resolve_active_membership(
    request, user, memberships: list[UserProfile], password: str
) -> UserProfile:
    if request is not None:
        active_id = request.session.get("active_membership_id")
        if active_id:
            active = next((m for m in memberships if m.id == active_id), None)
            if active:
                return active

    school_password_matches = _matching_school_password_memberships(memberships, password)
    if len(school_password_matches) == 1:
        return school_password_matches[0]

    supervisor_memberships = [m for m in memberships if m.role == Role.SUPERVISOR]
    if len(supervisor_memberships) > 1 and check_password(password, user.password):
        return min(supervisor_memberships, key=lambda m: m.id)

    if school_password_matches:
        return min(school_password_matches, key=lambda m: m.id)

    return min(memberships, key=lambda m: m.id)


class SchoolScopedBackend(ModelBackend):
    """
    Authenticate using per-school password on UserProfile.

    Supervisors with multiple schools can sign in with their account password;
    the active school stays on the last session school or defaults to their first
    school instead of being switched automatically by password matching.

    Other roles still use per-school passwords where configured.
    Platform superadmins (no school) use username + password only.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        try:
            user = User.objects.get(username__iexact=username.strip())
        except User.DoesNotExist:
            return None
        except User.MultipleObjectsReturned:
            user = User.objects.filter(username__iexact=username.strip()).order_by("id").first()

        memberships = list(
            UserProfile.objects.filter(user=user).select_related("school")
        )

        # Platform admins created with createsuperuser may have no membership yet.
        if not memberships:
            if user.check_password(password) and (user.is_superuser or user.is_staff):
                profile, _ = UserProfile.objects.get_or_create(
                    user=user,
                    school=None,
                    defaults={
                        "role": Role.SUPERADMIN,
                        "school_password": user.password,
                    },
                )
                if profile.role != Role.SUPERADMIN:
                    profile.role = Role.SUPERADMIN
                    profile.school_password = user.password
                    profile.save(update_fields=["role", "school_password"])
                if request is not None:
                    request.session["active_membership_id"] = profile.id
                return user
            return None

        if not any(_password_grants_access(user, m, password) for m in memberships):
            return None

        if request is not None:
            active = _resolve_active_membership(request, user, memberships, password)
            request.session["active_membership_id"] = active.id

        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
