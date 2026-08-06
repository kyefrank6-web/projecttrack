from django.contrib import admin

from .models import (
    AssessmentScheme,
    ClassProjectTheme,
    CohortProjectTheme,
    Competency,
    CompetencyScore,
    ObservationChecklist,
    ObservationCriterion,
    ProjectAssessment,
    ProjectEvidence,
    School,
    Student,
    StudentObservationRating,
    UserProfile,
)


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "overall_supervisor", "created_at", "reviewed_at")
    list_filter = ("status",)
    search_fields = ("name", "overall_supervisor__username", "overall_supervisor__email")
    fields = ("name", "logo", "theme", "motto", "vision", "mission", "overall_supervisor", "status")


class ObservationCriterionInline(admin.TabularInline):
    model = ObservationCriterion
    extra = 0


@admin.register(ClassProjectTheme)
class ClassProjectThemeAdmin(admin.ModelAdmin):
    list_display = ("school", "class_level", "year", "updated_by", "updated_at")
    list_filter = ("school", "year", "class_level")
    search_fields = ("theme", "school__name")


@admin.register(CohortProjectTheme)
class CohortProjectThemeAdmin(admin.ModelAdmin):
    list_display = ("school", "cohort_year", "updated_by", "updated_at")
    list_filter = ("school", "cohort_year")
    search_fields = ("theme", "school__name")


@admin.register(ObservationChecklist)
class ObservationChecklistAdmin(admin.ModelAdmin):
    list_display = ("title", "school", "cohort_year", "format_year", "year", "class_level", "term", "active", "created_at")
    list_filter = ("school", "year", "active")
    inlines = [ObservationCriterionInline]


@admin.register(StudentObservationRating)
class StudentObservationRatingAdmin(admin.ModelAdmin):
    list_display = ("student", "criterion", "year", "term", "rating", "updated_at")
    list_filter = ("year", "term")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "school", "role", "created_at")
    list_filter = ("role", "school")
    search_fields = ("user__username", "user__email", "school__name")


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("full_name", "student_no", "class_level", "stream", "school", "supervisor", "created_at")
    list_filter = ("school", "class_level")
    search_fields = ("full_name", "student_no", "supervisor__username")


class CompetencyInline(admin.TabularInline):
    model = Competency
    extra = 0


@admin.register(AssessmentScheme)
class AssessmentSchemeAdmin(admin.ModelAdmin):
    list_display = ("name", "active")
    inlines = [CompetencyInline]


class CompetencyScoreInline(admin.TabularInline):
    model = CompetencyScore
    extra = 0


@admin.register(ProjectEvidence)
class ProjectEvidenceAdmin(admin.ModelAdmin):
    list_display = ("student", "category", "uploaded_by", "uploaded_at")
    list_filter = ("category", "uploaded_at")
    search_fields = ("student__full_name", "uploaded_by__username", "caption")


@admin.register(ProjectAssessment)
class ProjectAssessmentAdmin(admin.ModelAdmin):
    list_display = ("student", "scheme", "year", "term", "created_by", "updated_at")
    list_filter = ("scheme", "year", "term")
    search_fields = ("student__full_name", "created_by__username")
    inlines = [CompetencyScoreInline]
