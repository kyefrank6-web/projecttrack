from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner

from .models import Role, UserProfile

User = get_user_model()

_MEMBERSHIP_SIGNER = TimestampSigner(salt="projecttrack-password-reset-membership")


class SchoolPasswordResetTokenGenerator(PasswordResetTokenGenerator):
    """Token tied to user + school membership password hash."""

    def __init__(self, membership_id: int):
        self.membership_id = membership_id
        super().__init__()

    def _make_hash_value(self, user, timestamp):
        membership = UserProfile.objects.filter(pk=self.membership_id, user=user).first()
        school_pw = membership.school_password if membership else ""
        return f"{user.pk}{school_pw}{timestamp}{self.membership_id}"


def sign_membership_id(membership_id: int) -> str:
    return _MEMBERSHIP_SIGNER.sign(str(membership_id))


def unsign_membership_id(signed_value: str, *, max_age: int = 60 * 60 * 24 * 3) -> int | None:
    try:
        return int(_MEMBERSHIP_SIGNER.unsign(signed_value, max_age=max_age))
    except (BadSignature, SignatureExpired, ValueError):
        return None


def find_memberships_for_reset(
    *,
    username: str,
    email: str,
    school_name: str = "",
) -> list[UserProfile]:
    username = (username or "").strip()
    email = (email or "").strip().lower()
    school_name = (school_name or "").strip()
    if not username or not email:
        return []

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return []

    if (user.email or "").strip().lower() != email:
        return []

    qs = UserProfile.objects.filter(user=user).select_related("school")
    if school_name:
        qs = qs.filter(school__name__iexact=school_name)
    return list(qs)


def membership_label(membership: UserProfile) -> str:
    if membership.school_id:
        return membership.school.name
    if membership.role == Role.SUPERADMIN:
        return "Platform administrator"
    return "your account"


def send_password_reset_email(
    *,
    request,
    membership: UserProfile,
    recipient_email: str,
) -> None:
    token_generator = SchoolPasswordResetTokenGenerator(membership.id)
    token = token_generator.make_token(membership.user)
    signed_id = sign_membership_id(membership.id)
    path = request.build_absolute_uri(
        f"/password-reset/confirm/{signed_id}/{token}/"
    )
    school_line = membership_label(membership)
    subject = "Reset your ProjectTrack UG password"
    body = (
        f"Hello {membership.user.get_full_name() or membership.user.username},\n\n"
        f"You requested a password reset for {school_line} on ProjectTrack UG.\n\n"
        f"Open this link to choose a new password (valid for 3 days):\n{path}\n\n"
        "If you did not request this, you can ignore this email.\n\n"
        "— ProjectTrack UG"
    )
    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [recipient_email],
        fail_silently=False,
    )


def set_membership_password(
    membership: UserProfile,
    raw_password: str,
    *,
    must_change: bool | None = None,
) -> None:
    from django.contrib.auth.hashers import make_password

    new_hash = make_password(raw_password)
    update_fields: dict = {"school_password": new_hash}
    if must_change is not None:
        update_fields["must_change_password"] = must_change

    if membership.role in (Role.SUPERVISOR, Role.OVERALL_SUPERVISOR):
        UserProfile.objects.filter(user=membership.user, role=membership.role).update(
            **update_fields
        )
    else:
        membership.school_password = new_hash
        if must_change is not None:
            membership.must_change_password = must_change
            membership.save(update_fields=["school_password", "must_change_password"])
        else:
            membership.save(update_fields=["school_password"])
    _sync_user_password(membership.user, raw_password)


def sync_account_password(user, raw_password: str, *, membership: UserProfile) -> None:
    """Update the account password and keep school membership passwords in sync."""
    from django.contrib.auth.hashers import make_password

    new_hash = make_password(raw_password)
    user.set_password(raw_password)
    user.save(update_fields=["password"])

    if membership.role in (Role.SUPERVISOR, Role.OVERALL_SUPERVISOR):
        UserProfile.objects.filter(user=user, role=membership.role).update(
            school_password=new_hash,
            must_change_password=False,
        )
    else:
        membership.school_password = new_hash
        membership.must_change_password = False
        membership.save(update_fields=["school_password", "must_change_password"])


def clear_must_change_password(membership: UserProfile) -> None:
    """Clear the one-time password flag after a successful password update."""
    if membership.role in (Role.SUPERVISOR, Role.OVERALL_SUPERVISOR):
        UserProfile.objects.filter(user=membership.user, role=membership.role).update(
            must_change_password=False
        )
    else:
        if membership.must_change_password:
            membership.must_change_password = False
            membership.save(update_fields=["must_change_password"])


def _sync_user_password(user, raw_password: str) -> None:
    user.set_password(raw_password)
    user.save(update_fields=["password"])
