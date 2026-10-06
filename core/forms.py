from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from django.db.models.functions import Lower
from django.utils import timezone

from .models import (
    AssessmentScheme,
    ClassProjectTheme,
    CohortProjectTheme,
    ObservationChecklist,
    Role,
    School,
    SecondaryClassLevel,
    Student,
    UserProfile,
)
from .school_utils import current_school_term
from .themes import theme_choices
from .builtin_checklists import (
    BUILTIN_CHECKLISTS,
    builtin_choice_options,
    builtin_cohort_years,
    builtin_format_years,
    cohort_upload_guide,
    default_title_for_upload,
    get_builtin_format,
    get_builtin_for_cohort,
)

User = get_user_model()


class SchoolBrandingForm(forms.ModelForm):
    logo = forms.ImageField(required=False)

    class Meta:
        model = School
        fields = ["theme", "logo", "motto", "vision", "mission"]
        labels = {
            "theme": "Color theme",
            "motto": "School motto",
            "vision": "School vision",
            "mission": "School mission",
        }
        widgets = {
            "motto": forms.TextInput(attrs={"placeholder": "e.g. Excellence through innovation"}),
            "vision": forms.Textarea(attrs={"rows": 3, "placeholder": "Where the school aspires to be..."}),
            "mission": forms.Textarea(attrs={"rows": 3, "placeholder": "The school's purpose and commitment..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["theme"].widget = forms.RadioSelect(choices=theme_choices())
        for name in ("logo", "motto", "vision", "mission"):
            if name in self.fields:
                self.fields[name].widget.attrs.setdefault("class", "form-control")


class ObservationChecklistUploadForm(forms.ModelForm):
    builtin_checklist = forms.ChoiceField(
        required=False,
        label="UNEB checklist format (built-in)",
        help_text=(
            "Which UNEB checklist layout to use (2025 or 2026 format). "
            "Can differ from cohort year — e.g. cohort 2027 using 2026 format if UNEB unchanged."
        ),
        widget=forms.Select(attrs={"class": "form-select", "id": "id_builtin_checklist"}),
    )
    structure_file = forms.FileField(
        required=False,
        label="Observation structure (Excel or CSV)",
        help_text="Optional but recommended: one row per checkbox observation from your official checklist.",
    )

    class Meta:
        model = ObservationChecklist
        fields = ["title", "year", "cohort_year", "term", "class_level", "pdf_file"]
        labels = {
            "title": "Checklist name",
            "class_level": "Class",
            "cohort_year": "UNEB cohort year (S.3 Term 1)",
            "term": "Term (optional)",
        }
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Revised Project Observation Checklist 2026–2027",
                }
            ),
            "year": forms.NumberInput(attrs={"class": "form-control"}),
            "term": forms.Select(attrs={"class": "form-select"}),
            "class_level": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["class_level"].required = True
        self.fields["class_level"].choices = list(SecondaryClassLevel.choices)
        self.fields["class_level"].help_text = (
            "Upload a separate checklist per class. S.3 and S.4 use the cohort year below."
        )
        self.fields["cohort_year"].required = False
        self.fields["cohort_year"].widget.attrs.setdefault("class", "form-control")
        self.fields["cohort_year"].widget.attrs["id"] = "id_cohort_year"
        self.fields["cohort_year"].help_text = (
            "Year learners started S.3 Term 1 (who this upload is for). "
            "Independent of the checklist format you pick above."
        )
        self.fields["cohort_year"].initial = timezone.now().year
        self.fields["builtin_checklist"].choices = builtin_choice_options()
        cy = self.initial.get("cohort_year") or self.fields["cohort_year"].initial
        if cy and get_builtin_format(int(cy)):
            self.fields["builtin_checklist"].initial = str(int(cy))
        elif builtin_format_years():
            self.fields["builtin_checklist"].initial = str(builtin_format_years()[0])
        self.fields["term"].required = False
        self.fields["term"].empty_label = "All terms"
        self.fields["pdf_file"].required = False
        self.fields["pdf_file"].widget.attrs.setdefault("class", "form-control")
        self.fields["pdf_file"].widget.attrs.setdefault("accept", ".pdf")
        self.fields["pdf_file"].help_text = (
            "Optional when you pick a built-in version that includes a PDF (e.g. 2025 or 2026). "
            "Required for Custom uploads."
        )

    def clean_class_level(self):
        value = (self.cleaned_data.get("class_level") or "").strip().upper()
        valid = {c for c, _ in SecondaryClassLevel.choices}
        if value not in valid:
            raise forms.ValidationError("Select the class this checklist is for (S1–S6).")
        return value

    def clean_term(self):
        val = self.cleaned_data.get("term")
        if val in (None, ""):
            return None
        return int(val)

    def clean(self):
        cleaned = super().clean()
        class_level = (cleaned.get("class_level") or "").strip().upper()
        cohort_year = cleaned.get("cohort_year")
        year = cleaned.get("year")
        builtin_key = (cleaned.get("builtin_checklist") or "").strip()
        use_builtin = bool(builtin_key)

        if class_level in {SecondaryClassLevel.S3, SecondaryClassLevel.S4}:
            if not cohort_year and year:
                if class_level == SecondaryClassLevel.S3:
                    cleaned["cohort_year"] = int(year)
                else:
                    raise ValidationError(
                        {
                            "cohort_year": (
                                "Required for S.4 — year when these learners started S.3 Term 1 "
                                "(e.g. 2025 for S.4 in 2026)."
                            )
                        }
                    )
            elif not cohort_year:
                raise ValidationError(
                    {"cohort_year": "Enter the learner cohort year (S.3 Term 1)."}
                )

        cohort_year = int(cleaned["cohort_year"]) if cleaned.get("cohort_year") else None
        pdf = cleaned.get("pdf_file")
        builtin = get_builtin_format(int(builtin_key)) if use_builtin else None

        if use_builtin:
            if not builtin:
                raise ValidationError(
                    {
                        "builtin_checklist": (
                            f"No built-in format for year {builtin_key}. "
                            f"Available: {', '.join(str(y) for y in builtin_format_years())}. "
                            "Choose Custom and upload PDF + structure file."
                        )
                    }
                )
            cleaned["format_year"] = int(builtin_key)
            if not pdf and not (builtin.pdf_path and builtin.pdf_path.exists()):
                raise ValidationError(
                    {"pdf_file": "Upload a PDF or pick a built-in format that includes a bundled PDF."}
                )
            if not cleaned.get("title"):
                cleaned["title"] = default_title_for_upload(
                    cohort_year=cohort_year,
                    format_year=int(builtin_key),
                )
        elif not pdf:
            raise ValidationError({"pdf_file": "Upload the official checklist PDF."})
        else:
            cleaned["format_year"] = None

        cleaned["use_builtin_checklist"] = use_builtin
        return cleaned


class ClassProjectThemeForm(forms.ModelForm):
    """Optional per-class themes for S1, S2, S5, S6 (not the UNEB S3→S4 cycle)."""

    class Meta:
        model = ClassProjectTheme
        fields = ["class_level", "year", "theme"]
        labels = {
            "class_level": "Class",
            "year": "Academic year",
            "theme": "Project theme",
        }
        widgets = {
            "class_level": forms.Select(attrs={"class": "form-select"}),
            "year": forms.NumberInput(attrs={"class": "form-control"}),
            "theme": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Theme for this class and year",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["year"].initial = timezone.now().year
        s3_s4 = {SecondaryClassLevel.S3, SecondaryClassLevel.S4}
        self.fields["class_level"].choices = [
            (c, label) for c, label in SecondaryClassLevel.choices if c not in s3_s4
        ]

    def clean_class_level(self):
        value = (self.cleaned_data.get("class_level") or "").strip().upper()
        if value in {SecondaryClassLevel.S3, SecondaryClassLevel.S4}:
            raise forms.ValidationError(
                "S.3 and S.4 use UNEB cohort themes (set in the form above)."
            )
        valid = {c for c, _ in SecondaryClassLevel.choices}
        if value not in valid:
            raise forms.ValidationError("Select a valid class (S1–S6).")
        return value


class CohortProjectThemeForm(forms.ModelForm):
    class Meta:
        model = CohortProjectTheme
        fields = ["cohort_year", "theme"]
        labels = {
            "cohort_year": "Cohort year (S.3 Term 1)",
            "theme": "UNEB project theme",
        }
        widgets = {
            "cohort_year": forms.NumberInput(attrs={"class": "form-control"}),
            "theme": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "e.g. Utilisation of Available Resources for Community Development",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cohort_year"].initial = timezone.now().year
        self.fields["cohort_year"].widget.attrs.setdefault("class", "form-control")
        self.fields["theme"].widget.attrs.setdefault("class", "form-control")

    def clean_cohort_year(self):
        val = self.cleaned_data.get("cohort_year")
        if val is None:
            raise forms.ValidationError("Enter the year learners start S.3 Term 1.")
        if val < 2000 or val > 2100:
            raise forms.ValidationError("Enter a year between 2000 and 2100.")
        return int(val)


class UploadFileForm(forms.Form):
    file = forms.FileField()


class ScoreStudentForm(forms.Form):
    scheme = forms.ModelChoiceField(queryset=AssessmentScheme.objects.all())
    year = forms.IntegerField(min_value=2000, max_value=2100)
    term = forms.ChoiceField(choices=[("1", "Term 1"), ("2", "Term 2"), ("3", "Term 3")])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["term"].initial = str(current_school_term())
        for _, field in self.fields.items():
            field.widget.attrs.setdefault("class", "form-control")


class ClassFilterForm(forms.Form):
    class_level = forms.ChoiceField(choices=SecondaryClassLevel.choices)
    year = forms.IntegerField(min_value=2000, max_value=2100)
    term = forms.ChoiceField(choices=[("1", "Term 1"), ("2", "Term 2"), ("3", "Term 3")])
    scheme_id = forms.IntegerField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["term"].initial = str(current_school_term())


class UsernameChangeForm(forms.Form):
    username = forms.CharField(max_length=150)

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["username"].initial = user.username
        self.fields["username"].widget.attrs.setdefault("class", "form-control")

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if not username:
            raise ValidationError("Username is required.")
        if self.user and User.objects.filter(username=username).exclude(pk=self.user.pk).exists():
            raise ValidationError("That username is already taken.")
        return username

    def save(self):
        if not self.user:
            raise ValidationError("No user to update.")
        self.user.username = self.cleaned_data["username"]
        self.user.save(update_fields=["username"])
        return self.user


class SchoolRejectForm(forms.Form):
    rejection_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        label="Reason (optional)",
    )


class SchoolDeleteConfirmForm(forms.Form):
    school_name_confirm = forms.CharField(
        max_length=200,
        label="Type the school name exactly to confirm",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "autocomplete": "off",
                "placeholder": "School name",
            }
        ),
    )
    understand = forms.BooleanField(
        label="I understand this deactivates the school for 30 days before permanent deletion",
        required=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def __init__(self, *args, expected_name: str = "", **kwargs):
        self.expected_name = (expected_name or "").strip()
        super().__init__(*args, **kwargs)

    def clean_school_name_confirm(self):
        typed = (self.cleaned_data.get("school_name_confirm") or "").strip()
        if not self.expected_name:
            raise ValidationError("Cannot verify school name.")
        if typed.casefold() != self.expected_name.casefold():
            raise ValidationError(
                "The name you entered does not match this school. Deletion was not performed."
            )
        return typed


class RegisterSchoolForm(forms.Form):
    school_name = forms.CharField(max_length=200)
    overall_username = forms.CharField(max_length=150)
    overall_email = forms.EmailField(required=False)
    overall_password = forms.CharField(min_length=8, widget=forms.PasswordInput)

    def clean_school_name(self):
        name = (self.cleaned_data.get("school_name") or "").strip()
        if not name:
            raise ValidationError("School name is required.")
        return name

    def clean_overall_username(self):
        username = (self.cleaned_data.get("overall_username") or "").strip()
        from .school_utils import username_blocks_registration

        if username_blocks_registration(username):
            raise ValidationError(
                "That username is already in use. Choose a different login username "
                "(display names can be the same)."
            )
        return username

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for _, field in self.fields.items():
            field.widget.attrs.setdefault("class", "form-control")


class SchoolPasswordChangeForm(PasswordChangeForm):
    """Validate old password against the active school's membership password."""

    def __init__(self, *args, membership: UserProfile | None = None, **kwargs):
        self.membership = membership
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old = self.cleaned_data.get("old_password")
        if self.membership and self.membership.school_password:
            if not check_password(old, self.membership.school_password):
                raise ValidationError("Your old password was entered incorrectly.")
            return old
        return super().clean_old_password()


class PasswordResetRequestForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        label="Username",
        widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "username"}),
    )
    email = forms.EmailField(
        label="Email on your account",
        widget=forms.EmailInput(attrs={"class": "form-control", "autocomplete": "email"}),
        help_text="Must match the email saved when your account was created.",
    )
    school_name = forms.CharField(
        max_length=200,
        required=False,
        label="School name (if applicable)",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Kololo SS"}),
        help_text="Required if your username is registered at more than one school.",
    )

    def clean(self):
        from .password_reset_utils import find_memberships_for_reset

        cleaned = super().clean()
        memberships = find_memberships_for_reset(
            username=cleaned.get("username", ""),
            email=cleaned.get("email", ""),
            school_name=cleaned.get("school_name", ""),
        )
        if not memberships:
            raise ValidationError(
                "No account matches that username and email"
                + (" and school name." if cleaned.get("school_name") else ". Try adding your school name.")
            )
        if len(memberships) > 1:
            raise ValidationError(
                "Your username is registered at multiple schools. Enter the exact school name."
            )
        cleaned["membership"] = memberships[0]
        return cleaned


class SetNewPasswordForm(forms.Form):
    new_password1 = forms.CharField(
        label="New password",
        min_length=8,
        widget=forms.PasswordInput(attrs={"class": "form-control pe-5", "autocomplete": "new-password"}),
    )
    new_password2 = forms.CharField(
        label="Confirm new password",
        widget=forms.PasswordInput(attrs={"class": "form-control pe-5", "autocomplete": "new-password"}),
    )

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("new_password1")
        p2 = cleaned.get("new_password2")
        if p1 and p2 and p1 != p2:
            raise ValidationError("The two password fields did not match.")
        return cleaned


class ManualSupervisorForm(forms.Form):
    full_name = forms.CharField(
        max_length=150,
        label="Full name",
        widget=forms.TextInput(attrs={"placeholder": "e.g. Mr. Were Matayo"}),
    )
    email = forms.EmailField(required=False, label="Email (optional)")
    username = forms.CharField(
        max_length=150,
        required=False,
        label="Username (optional)",
        help_text="Leave blank to auto-generate a unique login from the name. Same display names are allowed.",
    )
    password = forms.CharField(
        min_length=8,
        required=False,
        label="Password (optional)",
        widget=forms.PasswordInput,
        help_text="Leave blank to auto-generate a one-time password (must be changed on first login).",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_username(self):
        return (self.cleaned_data.get("username") or "").strip()

    def clean_full_name(self):
        name = (self.cleaned_data.get("full_name") or "").strip()
        if not name:
            raise ValidationError("Full name is required.")
        return name


class StudentEditForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ["full_name", "student_no", "class_level", "stream", "supervisor", "project_title"]
        labels = {
            "full_name": "Full name",
            "student_no": "Student number",
            "class_level": "Class",
            "stream": "Stream",
            "supervisor": "Project supervisor",
            "project_title": "Project title",
        }

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        if school is not None:
            supervisor_ids = UserProfile.objects.filter(school=school, role=Role.SUPERVISOR).values_list(
                "user_id", flat=True
            )
            self.fields["supervisor"].queryset = User.objects.filter(id__in=supervisor_ids).order_by(
                Lower("first_name"), Lower("username")
            )
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        self.fields["supervisor"].widget.attrs["class"] = "form-select"
        self.fields["class_level"].widget.attrs["class"] = "form-select"


def _configure_supervisor_field(form, *, school, required: bool = False):
    if school is not None:
        supervisor_ids = UserProfile.objects.filter(school=school, role=Role.SUPERVISOR).values_list(
            "user_id", flat=True
        )
        form.fields["supervisor"].queryset = User.objects.filter(id__in=supervisor_ids).order_by(
            Lower("first_name"), Lower("username")
        )
    form.fields["supervisor"].required = required
    form.fields["supervisor"].empty_label = "— No supervisor —"


class OverallStudentForm(forms.ModelForm):
    """Overall supervisor: roster details only — project title is set by the assigned supervisor."""

    class Meta:
        model = Student
        fields = ["full_name", "student_no", "class_level", "stream", "supervisor"]
        labels = StudentEditForm.Meta.labels

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        _configure_supervisor_field(self, school=school, required=False)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        self.fields["class_level"].widget.attrs["class"] = "form-select"


class AcademicPromotionForm(forms.Form):
    from_academic_year = forms.IntegerField(
        label="Academic year ending",
        min_value=2000,
        max_value=2100,
        widget=forms.NumberInput(attrs={"class": "form-control", "style": "max-width: 8rem"}),
        help_text="Learners move into the next calendar year (this value + 1). Each ending year can only be promoted once.",
    )
    confirm = forms.BooleanField(
        required=True,
        label="I confirm: O-level S.4 and A-level S.6 leavers graduate; S.5 is uploaded separately; supervisors, scores, and cohort themes stay with promoted learners.",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

