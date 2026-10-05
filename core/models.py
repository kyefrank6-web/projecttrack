from __future__ import annotations

from django.conf import settings
from django.db import models


class Role(models.TextChoices):
    SUPERADMIN = "superadmin", "Platform Superadmin"
    OVERALL_SUPERVISOR = "overall_supervisor", "Overall Supervisor"
    SUPERVISOR = "supervisor", "Supervisor"


class SchoolRegistrationStatus(models.TextChoices):
    PENDING = "pending", "Pending approval"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    DEACTIVATED = "deactivated", "Deactivated (pending deletion)"


class SecondaryClassLevel(models.TextChoices):
    S1 = "S1", "S1"
    S2 = "S2", "S2"
    S3 = "S3", "S3"
    S4 = "S4", "S4"
    S5 = "S5", "S5"
    S6 = "S6", "S6"


class SchoolTheme(models.TextChoices):
    ROYAL_BLUE = "royal_blue", "Royal Blue"
    FOREST_GREEN = "forest_green", "Forest Green"
    PURPLE_VIOLET = "purple_violet", "Purple Violet"
    SUNSET_ORANGE = "sunset_orange", "Sunset Orange"
    CRIMSON_RED = "crimson_red", "Crimson Red"
    TEAL_OCEAN = "teal_ocean", "Teal Ocean"
    NAVY_GOLD = "navy_gold", "Navy & Gold"
    ROSE_PINK = "rose_pink", "Rose Pink"


class School(models.Model):
    name = models.CharField(max_length=200)
    logo = models.ImageField(upload_to="school_logos/", blank=True, null=True)
    theme = models.CharField(
        max_length=32,
        choices=SchoolTheme.choices,
        default=SchoolTheme.ROYAL_BLUE,
    )
    motto = models.CharField(max_length=300, blank=True, default="")
    vision = models.TextField(blank=True, default="")
    mission = models.TextField(blank=True, default="")
    overall_supervisor = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="overall_for_school",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=SchoolRegistrationStatus.choices,
        default=SchoolRegistrationStatus.PENDING,
    )
    rejection_reason = models.TextField(blank=True, default="")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_schools",
    )
    deactivated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When set, the school is inactive until permanently deleted after the grace period.",
    )
    deactivated_from_status = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Registration status to restore if deactivation is cancelled.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class UserProfile(models.Model):
    """
    One row per user, school, and role. The same person may be overall supervisor and
    regular supervisor at the same school (two memberships). Supervisors can also
    belong to many schools, each with its own password (school_password).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name="user_profiles", null=True, blank=True
    )
    role = models.CharField(max_length=32, choices=Role.choices)
    school_password = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text="Hashed password for this school (allows same username, different passwords per school).",
    )
    must_change_password = models.BooleanField(
        default=False,
        help_text="When True, user must set a new password before using the rest of the app "
        "(used for auto-generated one-time supervisor logins).",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "school", "role"],
                name="unique_user_school_role_membership",
            ),
        ]

    def __str__(self) -> str:
        school_name = self.school.name if self.school_id else "—"
        return f"{self.user.username} @ {school_name} ({self.role})"


class AssessmentScheme(models.Model):
    """
    Lets you model the Ugandan competency assessment as a configurable scheme.
    """

    name = models.CharField(max_length=200, unique=True)
    active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class Competency(models.Model):
    scheme = models.ForeignKey(AssessmentScheme, on_delete=models.CASCADE, related_name="competencies")
    name = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("scheme", "name")]
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.name


class StudentQuerySet(models.QuerySet):
    def active_only(self):
        return self.filter(active=True)


class Student(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="students")
    student_no = models.CharField(max_length=50, blank=True, default="")
    full_name = models.CharField(max_length=200)
    class_level = models.CharField(max_length=2, choices=SecondaryClassLevel.choices)
    stream = models.CharField(max_length=50, blank=True, default="")
    project_title = models.CharField(max_length=300, blank=True, default="")

    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="supervised_students",
        null=True,
        blank=True,
    )
    active = models.BooleanField(
        default=True,
        help_text="False when the learner has graduated (e.g. after S6 end-of-year promotion).",
    )
    graduated_year = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Calendar year when the learner completed S6 and left the active roster.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    objects = StudentQuerySet.as_manager()

    class Meta:
        indexes = [
            models.Index(fields=["school", "class_level"]),
            models.Index(fields=["school", "supervisor"]),
            models.Index(fields=["school", "active"]),
        ]

    def __str__(self) -> str:
        return self.full_name


class ProjectAssessment(models.Model):
    """
    One assessment per student per year/term; scores are stored per competency.
    """

    TERM_CHOICES = [
        (1, "Term 1"),
        (2, "Term 2"),
        (3, "Term 3"),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="assessments")
    scheme = models.ForeignKey(AssessmentScheme, on_delete=models.PROTECT, related_name="assessments")
    year = models.PositiveIntegerField()
    term = models.PositiveSmallIntegerField(choices=TERM_CHOICES)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_assessments"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("student", "scheme", "year", "term")]
        indexes = [
            models.Index(fields=["year", "term"]),
        ]

    def __str__(self) -> str:
        return f"{self.student} {self.year} T{self.term}"


class CompetencyScore(models.Model):
    assessment = models.ForeignKey(ProjectAssessment, on_delete=models.CASCADE, related_name="scores")
    competency = models.ForeignKey(Competency, on_delete=models.PROTECT, related_name="scores")
    score = models.DecimalField(max_digits=5, decimal_places=2)
    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this competency result was submitted (UNEB phase).",
    )

    class Meta:
        unique_together = [("assessment", "competency")]
        indexes = [
            models.Index(fields=["competency"]),
        ]

    def __str__(self) -> str:
        return f"{self.competency}: {self.score}"


def _checklist_pdf_upload_to(instance: "ObservationChecklist", filename: str) -> str:
    return f"observation_checklists/school_{instance.school_id}/{filename}"


class ObservationChecklist(models.Model):
    """Official observation checklist PDF + criteria for a school (by cohort and class)."""

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="observation_checklists")
    scheme = models.ForeignKey(
        AssessmentScheme, on_delete=models.PROTECT, related_name="observation_checklists"
    )
    title = models.CharField(max_length=300)
    year = models.PositiveIntegerField(
        help_text="Calendar year when this checklist was uploaded (for reference).",
    )
    cohort_year = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="UNEB cohort (S.3 Term 1 year). S.3 and S.4 learners in this cohort use this checklist.",
    )
    format_year = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="UNEB checklist format (built-in 2025 or 2026 structure). Can differ from cohort year.",
    )
    term = models.PositiveSmallIntegerField(
        choices=ProjectAssessment.TERM_CHOICES, null=True, blank=True
    )
    class_level = models.CharField(
        max_length=2,
        choices=SecondaryClassLevel.choices,
        blank=True,
        default="",
        help_text="Class this checklist applies to (required on upload).",
    )
    pdf_file = models.FileField(upload_to=_checklist_pdf_upload_to)
    active = models.BooleanField(default=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="uploaded_checklists"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-year", "-created_at"]
        indexes = [
            models.Index(fields=["school", "year", "active"]),
            models.Index(fields=["school", "cohort_year", "class_level", "active"]),
        ]

    def __str__(self) -> str:
        parts = [self.title, str(self.year)]
        if self.class_level:
            parts.append(self.class_level)
        if self.term:
            parts.append(f"T{self.term}")
        return " · ".join(parts)


class ObservationCriterion(models.Model):
    """One checkbox observation under a numbered section (e.g. 1.2) of the official checklist."""

    checklist = models.ForeignKey(
        ObservationChecklist, on_delete=models.CASCADE, related_name="criteria"
    )
    competency = models.ForeignKey(Competency, on_delete=models.PROTECT, related_name="observation_criteria")
    section_code = models.CharField(max_length=20, blank=True, default="")
    section_title = models.CharField(max_length=300, blank=True, default="")
    section_preamble = models.TextField(blank=True, default="")
    order = models.PositiveIntegerField(default=0)
    description = models.TextField()
    max_rating = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["competency__order", "section_code", "order", "id"]

    def __str__(self) -> str:
        label = self.section_code or self.section_title or self.competency.name
        return f"{label}: {self.description[:50]}"


class StudentObservationRating(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="observation_ratings")
    checklist = models.ForeignKey(ObservationChecklist, on_delete=models.CASCADE, related_name="ratings")
    criterion = models.ForeignKey(ObservationCriterion, on_delete=models.CASCADE, related_name="ratings")
    year = models.PositiveIntegerField()
    term = models.PositiveSmallIntegerField(choices=ProjectAssessment.TERM_CHOICES)
    rating = models.PositiveSmallIntegerField(default=0)
    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="observation_ratings_given"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("student", "criterion", "year", "term")]
        indexes = [
            models.Index(fields=["student", "year", "term"]),
        ]

    def __str__(self) -> str:
        return f"{self.student} · {self.criterion_id} = {self.rating}"


class ClassProjectTheme(models.Model):
    """Legacy per-class theme (S1–S6). S3/S4 UNEB cycles use CohortProjectTheme instead."""

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="class_project_themes")
    class_level = models.CharField(max_length=2, choices=SecondaryClassLevel.choices)
    year = models.PositiveIntegerField()
    theme = models.TextField(help_text="Official project theme for this class and year.")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_class_project_themes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("school", "class_level", "year")]
        ordering = ["-year", "class_level"]
        indexes = [
            models.Index(fields=["school", "year", "class_level"]),
        ]

    def __str__(self) -> str:
        return f"{self.school.name} · {self.class_level} · {self.year}"

    @property
    def coverage_label(self) -> str:
        return f"Class {self.class_level} · {self.year}"


class CohortProjectTheme(models.Model):
    """
    UNEB project theme for a Senior 3 cohort.
    Set when UNEB publishes the theme (S3 Term 1); same theme through S4 Term 3 (~November).
    """

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="cohort_project_themes")
    cohort_year = models.PositiveIntegerField(
        help_text="Calendar year when learners enter S.3 Term 1 and UNEB publishes the theme.",
    )
    theme = models.TextField()
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_cohort_project_themes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("school", "cohort_year")]
        ordering = ["-cohort_year"]
        indexes = [
            models.Index(fields=["school", "cohort_year"]),
        ]

    def __str__(self) -> str:
        return f"{self.school.name} · cohort {self.cohort_year}"

    @property
    def coverage_label(self) -> str:
        end_year = self.cohort_year + 1
        return f"S.3 Term 1 ({self.cohort_year}) → S.4 Term 3 ({end_year})"


class AcademicPromotionRun(models.Model):
    """Record of an end-of-year class promotion for a school (prevents duplicate runs)."""

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="promotion_runs")
    from_academic_year = models.PositiveIntegerField(
        help_text="Last academic/calendar year learners were in their previous class.",
    )
    to_academic_year = models.PositiveIntegerField()
    promoted_count = models.PositiveIntegerField(default=0)
    graduated_count = models.PositiveIntegerField(default=0)
    summary = models.JSONField(default=dict, blank=True)
    run_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="academic_promotion_runs",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["school", "from_academic_year"],
                name="unique_school_promotion_from_year",
            ),
        ]
        ordering = ["-from_academic_year"]

    def __str__(self) -> str:
        return f"{self.school.name}: {self.from_academic_year} → {self.to_academic_year}"


def _evidence_upload_to(instance: "ProjectEvidence", filename: str) -> str:
    # Keep files grouped by school/student for easier management.
    return f"evidence/school_{instance.student.school_id}/student_{instance.student_id}/{filename}"


class EvidenceCategory(models.TextChoices):
    MATERIAL_IDENTIFICATION = "material_identification", "Material identification"
    PROJECT_PROCESS = "project_process", "Project process"
    FINAL_PRODUCT = "final_product", "Final product"


class ProjectEvidence(models.Model):
    """
    One photo per category per student (3 categories total).
    """

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="evidence_photos")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="uploaded_evidence"
    )
    category = models.CharField(max_length=40, choices=EvidenceCategory.choices)
    file = models.FileField(upload_to=_evidence_upload_to)
    caption = models.CharField(max_length=300, blank=True, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category", "-uploaded_at"]
        unique_together = [("student", "category")]
        indexes = [
            models.Index(fields=["student"]),
            models.Index(fields=["student", "category"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_category_display()} — {self.student}"


class PlatformSettings(models.Model):
    """Singleton platform flags toggled from the superadmin dashboard."""

    maintenance_enabled = models.BooleanField(
        default=False,
        help_text="When enabled, only platform superadmins can sign in.",
    )
    maintenance_message = models.TextField(
        blank=True,
        default="",
        help_text="Optional message shown to users during maintenance.",
    )
    maintenance_updated_at = models.DateTimeField(null=True, blank=True)
    maintenance_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="maintenance_updates",
    )

    class Meta:
        verbose_name = "Platform settings"
        verbose_name_plural = "Platform settings"

    @classmethod
    def get(cls) -> PlatformSettings:
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
