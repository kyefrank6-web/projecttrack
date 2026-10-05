from __future__ import annotations

from django.db.models import Q

from .models import Role, School, UserProfile


def project_supervisor_profile_q(*, school: School) -> Q:
    """Profiles for users who may be assigned learners as project supervisors."""
    q = Q(school=school, role=Role.SUPERVISOR)
    if school.overall_supervisor_id:
        q |= Q(
            school=school,
            role=Role.OVERALL_SUPERVISOR,
            user_id=school.overall_supervisor_id,
        )
    return q


def project_supervisor_user_ids(*, school: School) -> list[int]:
    ids = list(
        UserProfile.objects.filter(school=school, role=Role.SUPERVISOR).values_list(
            "user_id", flat=True
        )
    )
    if school.overall_supervisor_id and school.overall_supervisor_id not in ids:
        ids.append(school.overall_supervisor_id)
    return ids


def is_project_supervisor_at_school(*, school: School, user_id: int) -> bool:
    if UserProfile.objects.filter(
        school=school, user_id=user_id, role=Role.SUPERVISOR
    ).exists():
        return True
    return bool(
        school.overall_supervisor_id == user_id
        and UserProfile.objects.filter(
            school=school, user_id=user_id, role=Role.OVERALL_SUPERVISOR
        ).exists()
    )


def profile_acts_as_supervisor(profile: UserProfile) -> bool:
    """Supervisor UI (my students, scoring, evidence) for regular and overall leads."""
    if profile.role == Role.SUPERVISOR:
        return True
    if profile.role == Role.OVERALL_SUPERVISOR and profile.school_id:
        school = profile.school
        return bool(school and school.overall_supervisor_id == profile.user_id)
    return False
