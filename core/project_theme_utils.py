from __future__ import annotations

from .models import ClassProjectTheme, CohortProjectTheme, Student


def cohort_year_for_class(class_level: str, assessment_year: int) -> int | None:
    """
    Map a learner's current class to the UNEB cohort year (S.3 Term 1 when theme was issued).
    S.3 in 2025 → cohort 2025; S.4 in 2026 → same cohort 2025.
    """
    level = (class_level or "").upper()
    if level == "S3":
        return assessment_year
    if level == "S4":
        return assessment_year - 1
    return None


def get_cohort_project_theme(school_id: int, cohort_year: int) -> CohortProjectTheme | None:
    return (
        CohortProjectTheme.objects.filter(school_id=school_id, cohort_year=cohort_year)
        .select_related("updated_by")
        .first()
    )


def get_student_project_theme(
    student: Student,
    *,
    year: int,
    term: int | None = None,
) -> CohortProjectTheme | ClassProjectTheme | None:
    """Theme for this learner in the given assessment period."""
    cohort_year = cohort_year_for_class(student.class_level, year)
    if cohort_year is not None:
        theme = get_cohort_project_theme(student.school_id, cohort_year)
        if theme:
            return theme
    return get_class_project_theme(
        student.school_id,
        class_level=student.class_level,
        year=year,
    )


def get_class_project_theme(
    school_id: int,
    *,
    class_level: str,
    year: int,
) -> CohortProjectTheme | ClassProjectTheme | None:
    class_level = (class_level or "").upper()
    if not class_level:
        return None

    cohort_year = cohort_year_for_class(class_level, year)
    if cohort_year is not None:
        theme = get_cohort_project_theme(school_id, cohort_year)
        if theme:
            return theme

    return (
        ClassProjectTheme.objects.filter(
            school_id=school_id,
            class_level=class_level,
            year=year,
        )
        .select_related("updated_by")
        .first()
    )


def project_themes_by_class(
    school_id: int,
    *,
    year: int,
    class_levels: list[str] | None = None,
) -> dict[str, CohortProjectTheme | ClassProjectTheme]:
    levels = [(c or "").upper() for c in (class_levels or ["S3", "S4"]) if c]
    result: dict[str, CohortProjectTheme | ClassProjectTheme] = {}
    for level in levels:
        theme = get_class_project_theme(school_id, class_level=level, year=year)
        if theme:
            result[level] = theme
    return result


def theme_display_year(theme) -> int:
    if isinstance(theme, CohortProjectTheme):
        return theme.cohort_year
    return theme.year
