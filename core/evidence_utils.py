from __future__ import annotations

from .models import EvidenceCategory, ProjectEvidence, Student


def student_evidence_slots(student: Student) -> list[dict]:
    """Return the three required evidence categories with any existing uploads."""
    existing = {e.category: e for e in ProjectEvidence.objects.filter(student=student)}
    slots = []
    for cat in EvidenceCategory:
        slots.append(
            {
                "category": cat.value,
                "label": cat.label,
                "field_name": f"photo_{cat.value}",
                "photo": existing.get(cat.value),
            }
        )
    return slots


def evidence_completion_count(student: Student) -> int:
    return ProjectEvidence.objects.filter(student=student).count()


def evidence_complete(student: Student) -> bool:
    return evidence_completion_count(student) >= len(EvidenceCategory)
