from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .checklist_structures import cohort_2025, cohort_2026
from .checklist_structures.common import ObsItem

CHECKLIST_PDF_DIR = Path(__file__).resolve().parent / "checklist_pdfs"


@dataclass(frozen=True)
class BuiltinChecklist:
    """UNEB checklist format (structure + PDF), not necessarily the same as learner cohort year."""

    format_year: int
    label: str
    default_title: str
    document: dict
    competency_headings: dict[str, str]
    structured_checklist: list[tuple[str, str, str, str, list[ObsItem]]]
    pdf_filename: str | None = None

    @property
    def pdf_path(self) -> Path | None:
        if not self.pdf_filename:
            return None
        return CHECKLIST_PDF_DIR / self.pdf_filename


BUILTIN_CHECKLISTS: dict[int, BuiltinChecklist] = {
    2025: BuiltinChecklist(
        format_year=2025,
        label="2025 format — Continuous Assessment checklist",
        default_title="Continuous Assessment Observation Checklist",
        document=cohort_2025.CHECKLIST_DOCUMENT,
        competency_headings=cohort_2025.CHECKLIST_COMPETENCY_HEADINGS,
        structured_checklist=cohort_2025.STRUCTURED_CHECKLIST,
        pdf_filename="cohort_2025.pdf",
    ),
    2026: BuiltinChecklist(
        format_year=2026,
        label="2026 format — Revised Project Observation Checklist",
        default_title="Revised Project Observation Checklist 2026–2027",
        document=cohort_2026.CHECKLIST_DOCUMENT,
        competency_headings=cohort_2026.CHECKLIST_COMPETENCY_HEADINGS,
        structured_checklist=cohort_2026.STRUCTURED_CHECKLIST,
        pdf_filename="cohort_2026.pdf",
    ),
}


def get_builtin_format(format_year: int | None) -> BuiltinChecklist | None:
    if format_year is None:
        return None
    return BUILTIN_CHECKLISTS.get(int(format_year))


def get_builtin_for_cohort(cohort_year: int | None) -> BuiltinChecklist | None:
    """Backward-compatible alias — prefer get_builtin_format for checklist structure."""
    return get_builtin_format(cohort_year)


def builtin_format_years() -> list[int]:
    return sorted(BUILTIN_CHECKLISTS.keys(), reverse=True)


def builtin_cohort_years() -> list[int]:
    return builtin_format_years()


def builtin_choice_options() -> list[tuple[str, str]]:
    options = [("", "— Custom — upload your own PDF and structure file")]
    for year in builtin_format_years():
        builtin = BUILTIN_CHECKLISTS[year]
        options.append((str(year), builtin.label))
    return options


def checklist_format_year(checklist=None, *, format_year: int | None = None) -> int | None:
    if format_year is not None:
        return int(format_year)
    if checklist is None:
        return None
    fy = getattr(checklist, "format_year", None)
    if fy:
        return int(fy)
    cy = getattr(checklist, "cohort_year", None)
    return int(cy) if cy else None


def cohort_upload_guide(*, calendar_year: int) -> list[dict]:
    rows = []
    for class_level, cohort_year in (("S3", calendar_year), ("S4", calendar_year - 1)):
        rows.append(
            {
                "class_level": class_level,
                "calendar_year": calendar_year,
                "cohort_year": cohort_year,
                "suggested_formats": builtin_format_years(),
            }
        )
    return rows


def resolve_builtin_for_checklist(checklist) -> BuiltinChecklist | None:
    return get_builtin_format(checklist_format_year(checklist))


def checklist_document_for(checklist=None, *, cohort_year: int | None = None, format_year: int | None = None) -> dict:
    fy = checklist_format_year(checklist, format_year=format_year or cohort_year)
    builtin = get_builtin_format(fy)
    if builtin:
        return builtin.document
    return cohort_2026.CHECKLIST_DOCUMENT


def checklist_headings_for(checklist=None, *, cohort_year: int | None = None, format_year: int | None = None) -> dict[str, str]:
    fy = checklist_format_year(checklist, format_year=format_year or cohort_year)
    builtin = get_builtin_format(fy)
    if builtin:
        return builtin.competency_headings
    return cohort_2026.CHECKLIST_COMPETENCY_HEADINGS


def structured_checklist_for(checklist=None, *, cohort_year: int | None = None, format_year: int | None = None):
    fy = checklist_format_year(checklist, format_year=format_year or cohort_year)
    builtin = get_builtin_format(fy)
    if builtin:
        return builtin.structured_checklist
    return cohort_2026.STRUCTURED_CHECKLIST


def default_title_for_upload(*, cohort_year: int, format_year: int) -> str:
    builtin = get_builtin_format(format_year)
    if not builtin:
        return ""
    if cohort_year == format_year:
        return builtin.default_title
    return f"{builtin.default_title} (cohort {cohort_year})"
