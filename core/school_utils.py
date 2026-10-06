from __future__ import annotations

from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .models import ProjectEvidence, Role, School, SchoolRegistrationStatus, Student, UserProfile

User = get_user_model()

SCHOOL_DELETION_GRACE_DAYS = 30
UGANDA_TZ = ZoneInfo("Africa/Kampala")


def current_school_term(when=None) -> int:
    """
    Current Uganda secondary-school term from the calendar date (East Africa Time).

    Term 1 runs February–May (January, the holiday before the new year, is treated as Term 1).
    Term 2 runs June–August. Term 3 runs September–December.
    """
    moment = when or timezone.now()
    if timezone.is_aware(moment):
        moment = moment.astimezone(UGANDA_TZ)
    month = moment.month
    if month <= 5:
        return 1
    if month <= 8:
        return 2
    return 3


def school_name_blocks_registration(name: str) -> bool:
    """
    School display names are not unique — different schools may share a name.
    Kept for callers/tests; always allows registration by name.
    """
    return False


def username_blocks_registration(username: str) -> bool:
    """Block usernames tied to a pending or approved school account."""
    cleaned = (username or "").strip()
    if not cleaned:
        return False
    user = User.objects.filter(username=cleaned).first()
    if not user:
        return False

    for profile in UserProfile.objects.filter(user_id=user.id).select_related("school"):
        if not profile.school_id:
            return True
        if profile.school.status in (
            SchoolRegistrationStatus.PENDING,
            SchoolRegistrationStatus.APPROVED,
            SchoolRegistrationStatus.DEACTIVATED,
        ):
            return True

    return School.objects.filter(
        overall_supervisor_id=user.id,
        status__in=(
            SchoolRegistrationStatus.PENDING,
            SchoolRegistrationStatus.APPROVED,
            SchoolRegistrationStatus.DEACTIVATED,
        ),
    ).exists()


def permanent_deletion_at(school: School):
    if not school.deactivated_at:
        return None
    from datetime import timedelta

    return school.deactivated_at + timedelta(days=SCHOOL_DELETION_GRACE_DAYS)


@transaction.atomic
def deactivate_school(*, school: School, by_user) -> None:
    """Mark school inactive; permanent deletion happens after the grace period."""
    if school.status == SchoolRegistrationStatus.DEACTIVATED:
        return
    school.deactivated_from_status = school.status
    school.status = SchoolRegistrationStatus.DEACTIVATED
    school.deactivated_at = timezone.now()
    school.reviewed_at = timezone.now()
    school.reviewed_by = by_user
    school.save(
        update_fields=[
            "deactivated_from_status",
            "status",
            "deactivated_at",
            "reviewed_at",
            "reviewed_by",
        ]
    )


@transaction.atomic
def restore_deactivated_school(*, school: School) -> None:
    if school.status != SchoolRegistrationStatus.DEACTIVATED:
        raise ValueError("School is not deactivated.")
    restore_status = school.deactivated_from_status or SchoolRegistrationStatus.APPROVED
    if restore_status not in {
        SchoolRegistrationStatus.PENDING,
        SchoolRegistrationStatus.APPROVED,
        SchoolRegistrationStatus.REJECTED,
    }:
        restore_status = SchoolRegistrationStatus.APPROVED
    school.status = restore_status
    school.deactivated_at = None
    school.deactivated_from_status = ""
    school.save(update_fields=["status", "deactivated_at", "deactivated_from_status"])


@transaction.atomic
def purge_expired_deactivated_schools() -> list[str]:
    """Permanently delete schools that have been deactivated for at least the grace period."""
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(days=SCHOOL_DELETION_GRACE_DAYS)
    removed: list[str] = []
    expired = list(
        School.objects.filter(
            status=SchoolRegistrationStatus.DEACTIVATED,
            deactivated_at__isnull=False,
            deactivated_at__lte=cutoff,
        )
    )
    for school in expired:
        removed.append(school.name)
        delete_school_completely(school)
    return removed


@transaction.atomic
def clear_registration_blockers(*, school_name: str, username: str) -> None:
    """
    Remove rejected school records and orphaned accounts so a deleted or rejected
    school can register again with the same name or username.
    """
    cleaned_name = (school_name or "").strip()
    cleaned_username = (username or "").strip()

    for school in School.objects.filter(
        name__iexact=cleaned_name,
        status=SchoolRegistrationStatus.REJECTED,
    ):
        delete_school_completely(school)

    user = User.objects.filter(username=cleaned_username).first()
    if user and not username_blocks_registration(cleaned_username):
        user.delete()


@transaction.atomic
def delete_school_completely(school: School) -> None:
    user_ids = set(UserProfile.objects.filter(school=school).values_list("user_id", flat=True))
    if school.overall_supervisor_id:
        user_ids.add(school.overall_supervisor_id)

    for ev in ProjectEvidence.objects.filter(student__school=school).iterator():
        if ev.file:
            ev.file.delete(save=False)

    if school.logo:
        school.logo.delete(save=False)

    School.objects.filter(pk=school.pk).update(overall_supervisor=None)
    school.delete()

    for uid in user_ids:
        if UserProfile.objects.filter(user_id=uid).exists():
            continue
        if School.objects.filter(overall_supervisor_id=uid).exists():
            continue
        User.objects.filter(id=uid).delete()


@transaction.atomic
def delete_student_completely(student: Student) -> None:
    """Remove a learner and related scores, observations, and evidence files."""
    for ev in ProjectEvidence.objects.filter(student=student).iterator():
        if ev.file:
            ev.file.delete(save=False)
    student.delete()


@transaction.atomic
def delete_all_students_from_school(*, school: School) -> int:
    """
    Permanently remove every learner at this school, including scores,
    observation ratings, and evidence photo files.
    Returns the number of students deleted.
    """
    students = list(Student.objects.filter(school=school).only("id"))
    if not students:
        return 0

    student_ids = [s.id for s in students]
    for ev in ProjectEvidence.objects.filter(student_id__in=student_ids).iterator():
        if ev.file:
            ev.file.delete(save=False)

    Student.objects.filter(school=school).delete()
    return len(student_ids)


def ensure_supervisor_membership(
    *,
    school: School,
    user: User,
    password_hash: str,
    must_change_password: bool = True,
) -> tuple[UserProfile, bool]:
    """
    Add or refresh a regular supervisor membership at this school.
    Works even when the user is already the overall supervisor here (second role).
    """
    membership, created = UserProfile.objects.get_or_create(
        user=user,
        school=school,
        role=Role.SUPERVISOR,
        defaults={
            "school_password": password_hash,
            "must_change_password": must_change_password,
        },
    )
    if not created:
        membership.school_password = password_hash
        membership.must_change_password = must_change_password
        membership.save(update_fields=["school_password", "must_change_password"])
    return membership, created


@transaction.atomic
def remove_supervisor_from_school(*, school: School, supervisor_user_id: int) -> tuple[str, int]:
    """
    Remove a supervisor's membership at this school.
    Learners they supervised become unassigned (no supervisor).
    Returns (display name, number of students unassigned).
    """
    membership = UserProfile.objects.filter(
        school=school, user_id=supervisor_user_id, role=Role.SUPERVISOR
    ).select_related("user").first()
    if not membership:
        raise ValueError("Supervisor not found at this school.")

    unassigned = Student.objects.filter(school=school, supervisor_id=supervisor_user_id).update(
        supervisor=None
    )

    user = membership.user
    display = (user.get_full_name() or "").strip() or user.username
    membership.delete()

    if not UserProfile.objects.filter(user_id=user.id).exists():
        user.delete()

    return display, unassigned


@transaction.atomic
def remove_all_supervisors_from_school(*, school: School) -> tuple[int, int]:
    """
    Remove every regular supervisor membership at this school.
    Does not remove the overall supervisor.
    Learners they supervised become unassigned.
    Returns (supervisors removed, students unassigned).
    """
    memberships = list(
        UserProfile.objects.filter(school=school, role=Role.SUPERVISOR).select_related("user")
    )
    if not memberships:
        return 0, 0

    supervisor_ids = [m.user_id for m in memberships]
    unassigned = Student.objects.filter(school=school, supervisor_id__in=supervisor_ids).update(
        supervisor=None
    )

    user_ids = supervisor_ids[:]
    UserProfile.objects.filter(school=school, role=Role.SUPERVISOR).delete()

    orphan_ids = [
        uid
        for uid in user_ids
        if not UserProfile.objects.filter(user_id=uid).exists()
        and not School.objects.filter(overall_supervisor_id=uid).exists()
    ]
    if orphan_ids:
        User.objects.filter(id__in=orphan_ids).delete()

    return len(memberships), unassigned
