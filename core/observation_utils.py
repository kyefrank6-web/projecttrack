from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from django.db import transaction
from django.utils import timezone

from .models import (
    Competency,
    CompetencyScore,
    ObservationChecklist,
    ObservationCriterion,
    ProjectAssessment,
    Student,
    StudentObservationRating,
)
from .observation_defaults import (
    CHECKBOX_MAX_RATING,
    parse_observation_item,
)
from .builtin_checklists import structured_checklist_for


def section_code_sort_key(section_code: str) -> tuple:
    """Numeric ordering for codes like 1.9, 1.10 (not lexicographic 1.10 before 1.2)."""
    code = (section_code or "").strip()
    if not code:
        return (9999,)
    parts: list[int | str] = []
    for piece in code.split("."):
        piece = piece.strip()
        if piece.isdigit():
            parts.append(int(piece))
        elif piece:
            parts.append(piece)
    return tuple(parts) if parts else (9999,)


def seed_checklist_criteria(checklist: ObservationChecklist) -> int:
    """Create observation sections from the built-in structure for this checklist's cohort."""
    structure = structured_checklist_for(checklist)
    by_name = {
        c.name.lower(): c
        for c in Competency.objects.filter(scheme=checklist.scheme).order_by("order", "id")
    }
    ObservationCriterion.objects.filter(checklist=checklist).delete()
    order = 0
    created = 0
    for comp_name, code, title, preamble, observations in structure:
        comp = by_name.get(comp_name.lower())
        if not comp:
            continue
        for obs_item in observations:
            obs_text, max_rating = parse_observation_item(obs_item)
            order += 1
            ObservationCriterion.objects.create(
                checklist=checklist,
                competency=comp,
                section_code=code,
                section_title=title,
                section_preamble=preamble,
                description=obs_text,
                order=order,
                max_rating=max_rating,
            )
            created += 1
    return created


def resolve_checklist(
    school_id: int,
    *,
    year: int,
    term: int,
    class_level: str,
    cohort_year: int | None = None,
) -> ObservationChecklist | None:
    """
    Return the active checklist for this school, class, and UNEB cohort.
    S.3 in 2026 → cohort 2026; S.4 in 2026 → cohort 2025 (previous year's checklist).
    """
    from .project_theme_utils import cohort_year_for_class

    class_level = (class_level or "").upper()
    if not class_level:
        return None

    cy = cohort_year if cohort_year is not None else cohort_year_for_class(class_level, year)

    candidates: list[ObservationChecklist] = []
    if cy is not None:
        candidates = list(
            ObservationChecklist.objects.filter(
                school_id=school_id,
                active=True,
                class_level=class_level,
                cohort_year=cy,
            ).select_related("scheme")
        )

    if not candidates:
        candidates = list(
            ObservationChecklist.objects.filter(
                school_id=school_id,
                year=year,
                active=True,
                class_level=class_level,
                cohort_year__isnull=True,
            ).select_related("scheme")
        )

    if not candidates and cy is not None:
        candidates = list(
            ObservationChecklist.objects.filter(
                school_id=school_id,
                year=cy,
                active=True,
                class_level=class_level,
                cohort_year__isnull=True,
            ).select_related("scheme")
        )

    if not candidates:
        return None

    def score(cl: ObservationChecklist) -> tuple[int, float]:
        s = 0
        if cl.term and cl.term == term:
            s += 2
        elif cl.term is None:
            s += 1
        return (s, cl.created_at.timestamp())

    return max(candidates, key=score)


def resolve_checklist_for_student(
    student: Student,
    *,
    year: int,
    term: int,
) -> ObservationChecklist | None:
    return resolve_checklist(
        student.school_id,
        year=year,
        term=term,
        class_level=student.class_level,
    )


def active_checklist_class_levels(school_id: int, *, year: int) -> set[str]:
    """Class levels that have a resolvable observation checklist for the given year."""
    from .models import SecondaryClassLevel

    result: set[str] = set()
    for level, _ in SecondaryClassLevel.choices:
        if resolve_checklist(school_id, year=year, term=1, class_level=level):
            result.add(level)
    return result


def get_observation_structure(checklist: ObservationChecklist) -> list[dict[str, Any]]:
    """
    Returns competencies with nested sections matching the official checklist layout.
    """
    criteria = list(
        ObservationCriterion.objects.filter(checklist=checklist).select_related("competency")
    )
    criteria.sort(
        key=lambda c: (
            c.competency.order,
            c.competency_id,
            section_code_sort_key(c.section_code),
            c.order,
            c.id,
        )
    )
    by_comp: dict[int, dict[str, Any]] = {}
    for c in criteria:
        if c.competency_id not in by_comp:
            by_comp[c.competency_id] = {
                "competency": c.competency,
                "sections": [],
                "_section_keys": {},
            }
        bucket = by_comp[c.competency_id]
        sec_key = (c.section_code, c.section_title, c.section_preamble)
        if sec_key not in bucket["_section_keys"]:
            section = {
                "code": c.section_code,
                "title": c.section_title,
                "preamble": c.section_preamble,
                "items": [],
            }
            bucket["_section_keys"][sec_key] = section
            bucket["sections"].append(section)
        bucket["_section_keys"][sec_key]["items"].append(c)

    out: list[dict[str, Any]] = []
    for comp in Competency.objects.filter(scheme=checklist.scheme).order_by("order", "id"):
        if comp.id in by_comp:
            entry = by_comp[comp.id]
            del entry["_section_keys"]
            entry["sections"].sort(key=lambda s: section_code_sort_key(s["code"]))
            out.append(entry)
    return out


def get_criteria_grouped(checklist: ObservationChecklist):
    """Backwards-compatible flat grouping."""
    structure = get_observation_structure(checklist)
    return [(entry["competency"], [item for sec in entry["sections"] for item in sec["items"]]) for entry in structure]


def uses_checkbox_scoring(checklist: ObservationChecklist) -> bool:
    scorable = ObservationCriterion.objects.filter(checklist=checklist).exclude(max_rating=0)
    if not scorable.exists():
        return True
    return scorable.exclude(max_rating=CHECKBOX_MAX_RATING).count() == 0


def existing_ratings_map(
    student_id: int, checklist_id: int, year: int, term: int
) -> dict[int, int]:
    return {
        r.criterion_id: r.rating
        for r in StudentObservationRating.objects.filter(
            student_id=student_id,
            checklist_id=checklist_id,
            year=year,
            term=term,
        )
    }


def _competency_scorable_items(entry: dict[str, Any]) -> list[ObservationCriterion]:
    return [
        item
        for sec in entry["sections"]
        for item in sec["items"]
        if item.max_rating > 0
    ]


def competency_has_met_observations(
    entry: dict[str, Any],
    ratings_by_criterion: dict[int, int],
) -> bool:
    """True if at least one observation in this competency is ticked met."""
    return any(
        ratings_by_criterion.get(item.id, 0) > 0 for item in _competency_scorable_items(entry)
    )


def percentages_to_persist(
    checklist: ObservationChecklist,
    ratings_by_criterion: dict[int, int],
    existing_competency_ids: set[int],
) -> dict[int, Decimal]:
    """
    Only persist competency % when that competency has been assessed.
    New scores require at least one met observation; existing rows can be updated (including 0%).
    """
    all_pct = compute_competency_percentages(checklist, ratings_by_criterion)
    structure = get_observation_structure(checklist)
    out: dict[int, Decimal] = {}
    for entry in structure:
        comp_id = entry["competency"].id
        if comp_id not in all_pct:
            continue
        if comp_id in existing_competency_ids:
            out[comp_id] = all_pct[comp_id]
        elif competency_has_met_observations(entry, ratings_by_criterion):
            out[comp_id] = all_pct[comp_id]
    return out


def student_has_observation_ratings(
    student_id: int,
    checklist_id: int,
    year: int,
    term: int,
) -> bool:
    return StudentObservationRating.objects.filter(
        student_id=student_id,
        checklist_id=checklist_id,
        year=year,
        term=term,
    ).exists()


def latest_assessor_display_name(
    student_id: int,
    checklist_id: int,
    year: int,
    term: int,
) -> str:
    rating = (
        StudentObservationRating.objects.filter(
            student_id=student_id,
            checklist_id=checklist_id,
            year=year,
            term=term,
        )
        .select_related("assessed_by")
        .order_by("-updated_at")
        .first()
    )
    if not rating or not rating.assessed_by:
        return ""
    u = rating.assessed_by
    return (u.get_full_name() or u.first_name or u.username or "").strip()


def build_display_score_map(
    assessment: ProjectAssessment | None,
    *,
    checklist: ObservationChecklist | None = None,
    student_id: int | None = None,
    year: int | None = None,
    term: int | None = None,
) -> dict[int, Decimal]:
    """
    Score map for tables/exports. Hides mistaken 0% on competencies not yet assessed via checklist.
    """
    if not assessment:
        return {}
    raw = {sc.competency_id: sc.score for sc in assessment.scores.all()}
    if not checklist or student_id is None or year is None or term is None:
        return raw

    assessed_comp_ids = set(
        StudentObservationRating.objects.filter(
            student_id=student_id,
            checklist=checklist,
            year=year,
            term=term,
            rating__gt=0,
        )
        .values_list("criterion__competency_id", flat=True)
        .distinct()
    )
    return {
        comp_id: score
        for comp_id, score in raw.items()
        if score > 0 or comp_id in assessed_comp_ids
    }


def compute_competency_percentages(
    checklist: ObservationChecklist,
    ratings_by_criterion: dict[int, int],
) -> dict[int, Decimal]:
    """Each met checkbox counts toward competency % = (met items / total items) × 100."""
    structure = get_observation_structure(checklist)
    result: dict[int, Decimal] = {}
    for entry in structure:
        comp = entry["competency"]
        items = _competency_scorable_items(entry)
        if not items:
            continue
        earned = sum(ratings_by_criterion.get(item.id, 0) for item in items)
        maximum = sum(item.max_rating for item in items)
        if maximum <= 0:
            continue
        pct = (Decimal(earned) / Decimal(maximum)) * Decimal(100)
        result[comp.id] = pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return result


def get_submitted_competency_ids(
    student_id: int,
    checklist: ObservationChecklist,
    year: int,
    term: int,
) -> set[int]:
    """Competencies that already have a saved score for this learner/period."""
    assessment = ProjectAssessment.objects.filter(
        student_id=student_id,
        scheme=checklist.scheme,
        year=year,
        term=term,
    ).first()
    if not assessment:
        return set()
    return submitted_competency_ids_for_assessment(assessment)


def submitted_competency_ids_for_assessment(assessment: ProjectAssessment) -> set[int]:
    return set(
        CompetencyScore.objects.filter(assessment=assessment).values_list(
            "competency_id", flat=True
        )
    )


def compute_single_competency_percentage(
    entry: dict[str, Any],
    ratings_by_criterion: dict[int, int],
) -> Decimal | None:
    items = _competency_scorable_items(entry)
    if not items:
        return None
    earned = sum(ratings_by_criterion.get(item.id, 0) for item in items)
    maximum = sum(item.max_rating for item in items)
    if maximum <= 0:
        return None
    pct = (Decimal(earned) / Decimal(maximum)) * Decimal(100)
    return pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@transaction.atomic
def save_competency_observation_ratings_and_score(
    *,
    student: Student,
    checklist: ObservationChecklist,
    year: int,
    term: int,
    competency_id: int,
    ratings_by_criterion: dict[int, int],
    user,
) -> tuple[Decimal | None, str]:
    """
    Save observations and competency % for one competency only.
    Other competencies are left unchanged.
    """
    structure = get_observation_structure(checklist)
    entry = None
    for e in structure:
        if e["competency"].id == competency_id:
            entry = e
            break
    if not entry:
        raise ValueError("Invalid competency for this checklist.")

    valid_ids = {item.id for item in _competency_scorable_items(entry)}
    for criterion_id, rating in ratings_by_criterion.items():
        if criterion_id not in valid_ids:
            continue
        try:
            criterion = ObservationCriterion.objects.get(
                id=criterion_id, checklist=checklist, competency_id=competency_id
            )
        except ObservationCriterion.DoesNotExist:
            continue
        if rating < 0 or rating > criterion.max_rating:
            continue
        StudentObservationRating.objects.update_or_create(
            student=student,
            criterion=criterion,
            year=year,
            term=term,
            defaults={
                "checklist": checklist,
                "rating": rating,
                "assessed_by": user,
            },
        )

    merged_ratings = existing_ratings_map(student.id, checklist.id, year, term)
    merged_ratings.update(ratings_by_criterion)

    assessment, _ = ProjectAssessment.objects.get_or_create(
        student=student,
        scheme=checklist.scheme,
        year=year,
        term=term,
        defaults={"created_by": user},
    )
    assessment.created_by = user
    assessment.save(update_fields=["created_by", "updated_at"])

    existing_scores = {
        s.competency_id: s
        for s in CompetencyScore.objects.filter(assessment=assessment)
    }
    pct = compute_single_competency_percentage(entry, merged_ratings)
    comp_name = entry["competency"].name

    if pct is None:
        return None, comp_name

    if competency_id in existing_scores or competency_has_met_observations(entry, merged_ratings):
        if competency_id in existing_scores:
            obj = existing_scores[competency_id]
            obj.score = pct
            obj.submitted_at = timezone.now()
            obj.save(update_fields=["score", "submitted_at"])
        else:
            CompetencyScore.objects.create(
                assessment=assessment,
                competency_id=competency_id,
                score=pct,
                submitted_at=timezone.now(),
            )
        return pct, comp_name

    return None, comp_name


@transaction.atomic
def save_observation_ratings_and_scores(
    *,
    student: Student,
    checklist: ObservationChecklist,
    year: int,
    term: int,
    ratings_by_criterion: dict[int, int],
    user,
) -> dict[int, Decimal]:
    for criterion_id, rating in ratings_by_criterion.items():
        try:
            criterion = ObservationCriterion.objects.get(id=criterion_id, checklist=checklist)
        except ObservationCriterion.DoesNotExist:
            continue
        if rating < 0 or rating > criterion.max_rating:
            continue
        StudentObservationRating.objects.update_or_create(
            student=student,
            criterion=criterion,
            year=year,
            term=term,
            defaults={
                "checklist": checklist,
                "rating": rating,
                "assessed_by": user,
            },
        )

    assessment, _ = ProjectAssessment.objects.get_or_create(
        student=student,
        scheme=checklist.scheme,
        year=year,
        term=term,
        defaults={"created_by": user},
    )
    assessment.created_by = user
    assessment.save(update_fields=["created_by", "updated_at"])

    existing = {s.competency_id: s for s in CompetencyScore.objects.filter(assessment=assessment)}
    percentages = percentages_to_persist(
        checklist, ratings_by_criterion, set(existing.keys())
    )

    for comp_id, pct in percentages.items():
        if comp_id in existing:
            obj = existing[comp_id]
            obj.score = pct
            obj.save(update_fields=["score"])
        else:
            CompetencyScore.objects.create(
                assessment=assessment, competency_id=comp_id, score=pct
            )

    for comp_id, obj in list(existing.items()):
        if comp_id not in percentages and obj.score == 0:
            obj.delete()

    return percentages
