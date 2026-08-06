from __future__ import annotations

from dataclasses import dataclass, field

from django.db import transaction

from .models import AcademicPromotionRun, SecondaryClassLevel, Student

# O-level: S.1–S.4 (S.4 leavers graduate; S.5 is a fresh A-level intake).
O_LEVEL_PROMOTION: dict[str, str] = {
    SecondaryClassLevel.S1: SecondaryClassLevel.S2,
    SecondaryClassLevel.S2: SecondaryClassLevel.S3,
    SecondaryClassLevel.S3: SecondaryClassLevel.S4,
}

# A-level: S.5–S.6 (uploaded separately; only S.5→S.6 is promoted).
A_LEVEL_PROMOTION: dict[str, str] = {
    SecondaryClassLevel.S5: SecondaryClassLevel.S6,
}

O_LEVEL_GRADUATE_CLASS = SecondaryClassLevel.S4
A_LEVEL_GRADUATE_CLASS = SecondaryClassLevel.S6


class PromotionAlreadyRunError(Exception):
    def __init__(self, from_academic_year: int):
        self.from_academic_year = from_academic_year
        super().__init__(f"Promotion for academic year {from_academic_year} was already completed.")


@dataclass
class PromotionMove:
    from_class: str
    to_class: str
    count: int
    track: str = ""  # "O-level" or "A-level"


@dataclass
class PromotionGraduate:
    from_class: str
    label: str
    count: int
    track: str = ""


@dataclass
class PromotionPreview:
    from_academic_year: int
    to_academic_year: int
    moves: list[PromotionMove] = field(default_factory=list)
    graduates: list[PromotionGraduate] = field(default_factory=list)
    already_run: bool = False
    last_run_at: object = None

    @property
    def total_promoted(self) -> int:
        return sum(move.count for move in self.moves)

    @property
    def graduate_count(self) -> int:
        return sum(row.count for row in self.graduates)

    @property
    def o_level_graduate_count(self) -> int:
        return next(
            (row.count for row in self.graduates if row.from_class == O_LEVEL_GRADUATE_CLASS),
            0,
        )

    @property
    def a_level_graduate_count(self) -> int:
        return next(
            (row.count for row in self.graduates if row.from_class == A_LEVEL_GRADUATE_CLASS),
            0,
        )

    @property
    def has_work(self) -> bool:
        return self.total_promoted > 0 or self.graduate_count > 0



def _build_preview_moves(school_id: int) -> list[PromotionMove]:
    moves: list[PromotionMove] = []
    for level, next_level in O_LEVEL_PROMOTION.items():
        count = Student.objects.active_only().filter(school_id=school_id, class_level=level).count()
        moves.append(
            PromotionMove(
                from_class=level,
                to_class=next_level,
                count=count,
                track="O-level",
            )
        )
    for level, next_level in A_LEVEL_PROMOTION.items():
        count = Student.objects.active_only().filter(school_id=school_id, class_level=level).count()
        moves.append(
            PromotionMove(
                from_class=level,
                to_class=next_level,
                count=count,
                track="A-level",
            )
        )
    return moves


def _build_preview_graduates(school_id: int) -> list[PromotionGraduate]:
    o_count = Student.objects.active_only().filter(
        school_id=school_id, class_level=O_LEVEL_GRADUATE_CLASS
    ).count()
    a_count = Student.objects.active_only().filter(
        school_id=school_id, class_level=A_LEVEL_GRADUATE_CLASS
    ).count()
    return [
        PromotionGraduate(
            from_class=O_LEVEL_GRADUATE_CLASS,
            label="O-level graduated",
            count=o_count,
            track="O-level",
        ),
        PromotionGraduate(
            from_class=A_LEVEL_GRADUATE_CLASS,
            label="A-level graduated",
            count=a_count,
            track="A-level",
        ),
    ]


def preview_academic_promotion(school_id: int, from_academic_year: int) -> PromotionPreview:
    to_academic_year = from_academic_year + 1
    existing = (
        AcademicPromotionRun.objects.filter(school_id=school_id, from_academic_year=from_academic_year)
        .order_by("-created_at")
        .first()
    )
    return PromotionPreview(
        from_academic_year=from_academic_year,
        to_academic_year=to_academic_year,
        moves=_build_preview_moves(school_id),
        graduates=_build_preview_graduates(school_id),
        already_run=existing is not None,
        last_run_at=existing.created_at if existing else None,
    )


@transaction.atomic
def run_academic_promotion(
    school_id: int,
    *,
    from_academic_year: int,
    run_by_id: int,
) -> AcademicPromotionRun:
    if AcademicPromotionRun.objects.filter(
        school_id=school_id, from_academic_year=from_academic_year
    ).exists():
        raise PromotionAlreadyRunError(from_academic_year)

    to_academic_year = from_academic_year + 1
    summary: dict[str, int] = {}
    promoted_total = 0

    a_graduated = Student.objects.active_only().filter(
        school_id=school_id, class_level=A_LEVEL_GRADUATE_CLASS
    ).update(active=False, graduated_year=to_academic_year)
    summary["S6_A_level_graduated"] = a_graduated

    updated = Student.objects.active_only().filter(
        school_id=school_id, class_level=SecondaryClassLevel.S5
    ).update(class_level=SecondaryClassLevel.S6)
    summary["S5_to_S6"] = updated
    promoted_total += updated

    o_graduated = Student.objects.active_only().filter(
        school_id=school_id, class_level=O_LEVEL_GRADUATE_CLASS
    ).update(active=False, graduated_year=to_academic_year)
    summary["S4_O_level_graduated"] = o_graduated

    for level in (SecondaryClassLevel.S3, SecondaryClassLevel.S2, SecondaryClassLevel.S1):
        next_level = O_LEVEL_PROMOTION[level]
        updated = Student.objects.active_only().filter(
            school_id=school_id, class_level=level
        ).update(class_level=next_level)
        summary[f"{level}_to_{next_level}"] = updated
        promoted_total += updated

    graduated_total = o_graduated + a_graduated

    return AcademicPromotionRun.objects.create(
        school_id=school_id,
        from_academic_year=from_academic_year,
        to_academic_year=to_academic_year,
        promoted_count=promoted_total,
        graduated_count=graduated_total,
        summary=summary,
        run_by_id=run_by_id,
    )


def latest_promotion_run(school_id: int) -> AcademicPromotionRun | None:
    return AcademicPromotionRun.objects.filter(school_id=school_id).first()
