from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from .forms import RegisterSchoolForm
from .models import (
    AcademicPromotionRun,
    AssessmentScheme,
    Competency,
    CompetencyScore,
    ProjectAssessment,
    Role,
    School,
    SchoolRegistrationStatus,
    SecondaryClassLevel,
    Student,
    UserProfile,
)
from .project_theme_utils import cohort_year_for_class
from .promotion_utils import PromotionAlreadyRunError, preview_academic_promotion, run_academic_promotion
from .school_utils import clear_registration_blockers, delete_school_completely, school_name_blocks_registration

User = get_user_model()


class AcademicPromotionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="overall", password="test")
        self.school = School.objects.create(name="Test School", status="approved")
        UserProfile.objects.create(
            user=self.user,
            school=self.school,
            role=Role.OVERALL_SUPERVISOR,
        )
        self.supervisor = User.objects.create_user(username="sup1", password="test")
        UserProfile.objects.create(
            user=self.supervisor,
            school=self.school,
            role=Role.SUPERVISOR,
        )

    def _student(self, name: str, level: str) -> Student:
        return Student.objects.create(
            school=self.school,
            full_name=name,
            class_level=level,
            supervisor=self.supervisor,
        )

    def test_o_level_s3_promotes_to_s4_keeps_supervisor(self):
        s3 = self._student("Learner A", SecondaryClassLevel.S3)

        run = run_academic_promotion(
            self.school.id, from_academic_year=2025, run_by_id=self.user.id
        )
        self.assertEqual(run.promoted_count, 1)
        self.assertEqual(run.summary.get("S4_O_level_graduated", 0), 0)
        self.assertEqual(run.summary.get("S6_A_level_graduated", 0), 0)

        s3.refresh_from_db()
        self.assertEqual(s3.class_level, SecondaryClassLevel.S4)
        self.assertEqual(s3.supervisor_id, self.supervisor.id)
        self.assertTrue(s3.active)

    def test_o_level_s4_graduates_not_s5(self):
        s4 = self._student("O-level leaver", SecondaryClassLevel.S4)

        run = run_academic_promotion(
            self.school.id, from_academic_year=2025, run_by_id=self.user.id
        )
        self.assertEqual(run.promoted_count, 0)
        self.assertEqual(run.summary["S4_O_level_graduated"], 1)

        s4.refresh_from_db()
        self.assertEqual(s4.class_level, SecondaryClassLevel.S4)
        self.assertFalse(s4.active)
        self.assertEqual(s4.graduated_year, 2026)

    def test_a_level_s6_graduates_before_s5_promoted(self):
        s6_old = self._student("A-level leaver", SecondaryClassLevel.S6)
        s5 = self._student("A-level rising", SecondaryClassLevel.S5)

        run = run_academic_promotion(
            self.school.id, from_academic_year=2025, run_by_id=self.user.id
        )
        self.assertEqual(run.summary["S6_A_level_graduated"], 1)
        self.assertEqual(run.summary["S5_to_S6"], 1)
        self.assertEqual(run.promoted_count, 1)
        self.assertEqual(run.graduated_count, 1)

        s6_old.refresh_from_db()
        s5.refresh_from_db()
        self.assertFalse(s6_old.active)
        self.assertEqual(s6_old.graduated_year, 2026)
        self.assertEqual(s5.class_level, SecondaryClassLevel.S6)
        self.assertTrue(s5.active)

    def test_cohort_theme_mapping_after_s3_to_s4(self):
        s3 = self._student("Cohort kid", SecondaryClassLevel.S3)
        run_academic_promotion(self.school.id, from_academic_year=2025, run_by_id=self.user.id)
        s3.refresh_from_db()
        self.assertEqual(s3.class_level, SecondaryClassLevel.S4)
        self.assertEqual(cohort_year_for_class(s3.class_level, 2026), 2025)

    def test_preview_shows_o_and_a_tracks(self):
        self._student("S3", SecondaryClassLevel.S3)
        self._student("S5", SecondaryClassLevel.S5)
        preview = preview_academic_promotion(self.school.id, 2025)
        o_moves = [m for m in preview.moves if m.track == "O-level"]
        a_moves = [m for m in preview.moves if m.track == "A-level"]
        self.assertEqual(len(o_moves), 3)
        self.assertEqual(len(a_moves), 1)
        self.assertEqual(preview.o_level_graduate_count, 0)
        self.assertEqual(preview.a_level_graduate_count, 0)

    def test_duplicate_promotion_blocked(self):
        self._student("One", SecondaryClassLevel.S1)
        run_academic_promotion(self.school.id, from_academic_year=2025, run_by_id=self.user.id)
        self.assertEqual(AcademicPromotionRun.objects.filter(school=self.school).count(), 1)
        with self.assertRaises(PromotionAlreadyRunError):
            run_academic_promotion(self.school.id, from_academic_year=2025, run_by_id=self.user.id)


class SchoolReRegistrationTests(TestCase):
    def _create_pending_school(self, *, name: str, username: str) -> School:
        user = User.objects.create_user(username=username, password="secret123")
        school = School.objects.create(
            name=name,
            overall_supervisor=user,
            status=SchoolRegistrationStatus.PENDING,
        )
        UserProfile.objects.create(
            user=user,
            school=school,
            role=Role.OVERALL_SUPERVISOR,
        )
        return school

    def test_rejected_school_name_can_register_again(self):
        school = self._create_pending_school(name="Makerere SS", username="makerere")
        school.status = SchoolRegistrationStatus.REJECTED
        school.save(update_fields=["status"])

        self.assertFalse(school_name_blocks_registration("Makerere SS"))
        form = RegisterSchoolForm(
            {
                "school_name": "Makerere SS",
                "overall_username": "makerere",
                "overall_password": "newpass123",
            }
        )
        self.assertTrue(form.is_valid())

    def test_deleted_school_can_register_again(self):
        school = self._create_pending_school(name="Kololo SS", username="kololo")
        delete_school_completely(school)

        self.assertFalse(School.objects.filter(name="Kololo SS").exists())
        self.assertFalse(User.objects.filter(username="kololo").exists())

        client = Client()
        response = client.post(
            "/register/",
            {
                "school_name": "Kololo SS",
                "overall_username": "kololo",
                "overall_password": "newpass123",
            },
        )
        self.assertEqual(response.status_code, 302)

        new_school = School.objects.get(name="Kololo SS")
        self.assertEqual(new_school.status, SchoolRegistrationStatus.PENDING)
        self.assertTrue(User.objects.filter(username="kololo").exists())

    def test_clear_registration_blockers_removes_rejected_school(self):
        school = self._create_pending_school(name="Ntare SS", username="ntare")
        school.status = SchoolRegistrationStatus.REJECTED
        school.save(update_fields=["status"])

        clear_registration_blockers(school_name="Ntare SS", username="ntare")

        self.assertFalse(School.objects.filter(name="Ntare SS").exists())
        self.assertFalse(User.objects.filter(username="ntare").exists())


class SupervisorUploadTests(TestCase):
    def test_read_name_only_supervisor_list(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from .upload_utils import read_supervisor_upload_table

        csv_content = "Mr. Were Matayo\nJane Okello\n"
        uploaded = SimpleUploadedFile(
            "supervisors.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )
        rows = read_supervisor_upload_table(uploaded)
        self.assertEqual(len(rows), 2)
        self.assertEqual(
            rows[0].get("full_name") or next(iter(rows[0].values())),
            "Mr. Were Matayo",
        )

    def test_name_only_upload_creates_safe_usernames(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.urls import reverse

        from .models import Role, School, SchoolRegistrationStatus, UserProfile

        school = School.objects.create(name="Upload HS", status=SchoolRegistrationStatus.APPROVED)
        overall = User.objects.create_user("overall_up", "", "pass12345")
        profile = UserProfile.objects.create(
            user=overall,
            school=school,
            role=Role.OVERALL_SUPERVISOR,
            school_password=overall.password,
        )
        self.client.force_login(overall)
        session = self.client.session
        session["active_membership_id"] = profile.id
        session.save()

        uploaded = SimpleUploadedFile(
            "supervisors.csv",
            b"Name\nMr. Were Matayo\nJane Okello\n",
            content_type="text/csv",
        )
        response = self.client.post(reverse("upload_supervisors"), {"file": uploaded})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        usernames = set(
            User.objects.filter(memberships__school=school, memberships__role=Role.SUPERVISOR).values_list(
                "username", flat=True
            )
        )
        self.assertTrue(usernames)
        for username in usernames:
            self.assertNotIn(" ", username)
            self.assertTrue(username.replace(".", "").replace("_", "").replace("-", "").isalnum())
        self.assertIn("matayo", usernames)
        self.assertIn("okello", usernames)


class OverallSupervisorAsSupervisorTests(TestCase):
    def test_overall_username_can_be_added_as_supervisor(self):
        from .school_utils import ensure_supervisor_membership
        from .views import _provision_school_supervisor

        school = School.objects.create(
            name="Dual Role HS",
            status=SchoolRegistrationStatus.APPROVED,
        )
        overall = User.objects.create_user("head_teacher", "", "OverallPass123!")
        school.overall_supervisor = overall
        school.save(update_fields=["overall_supervisor"])
        UserProfile.objects.create(
            user=overall,
            school=school,
            role=Role.OVERALL_SUPERVISOR,
            school_password=overall.password,
        )
        from django.contrib.auth.hashers import make_password

        ensure_supervisor_membership(
            school=school,
            user=overall,
            password_hash=make_password("SupervisorOnly123!"),
        )
        self.assertEqual(
            UserProfile.objects.filter(user=overall, school=school).count(),
            2,
        )

        creds = _provision_school_supervisor(
            school=school,
            full_name="Head Teacher",
            username="head_teacher",
        )
        self.assertEqual(creds["username"], "head_teacher")
        self.assertEqual(
            UserProfile.objects.filter(
                user=overall, school=school, role=Role.SUPERVISOR
            ).count(),
            1,
        )
        self.assertIn("supervisor", creds["note"].lower())


class MaintenanceModePlatformToggleTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("toggle_admin", password="AdminPass123!")
        self.profile = UserProfile.objects.create(
            user=self.admin,
            school=None,
            role=Role.SUPERADMIN,
            school_password=self.admin.password,
        )
        self.overall = User.objects.create_user("toggle_overall", password="SchoolPass123!")
        school = School.objects.create(name="Toggle HS", status=SchoolRegistrationStatus.APPROVED)
        UserProfile.objects.create(
            user=self.overall,
            school=school,
            role=Role.OVERALL_SUPERVISOR,
            school_password=self.overall.password,
        )

    def test_superadmin_can_toggle_maintenance_from_dashboard(self):
        from django.urls import reverse

        from .models import PlatformSettings

        self.client.force_login(self.admin)
        session = self.client.session
        session["active_membership_id"] = self.profile.id
        session.save()

        response = self.client.post(
            reverse("superadmin_toggle_maintenance"),
            {"action": "enable", "maintenance_message": "Upgrading now."},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(PlatformSettings.get().maintenance_enabled)

        response = self.client.post("/login/", {"username": "toggle_overall", "password": "SchoolPass123!"})
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            reverse("superadmin_toggle_maintenance"),
            {"action": "disable"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(PlatformSettings.get().maintenance_enabled)

        response = self.client.post("/login/", {"username": "toggle_overall", "password": "SchoolPass123!"})
        self.assertEqual(response.status_code, 302)


class MaintenanceModeTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="Maint HS", status=SchoolRegistrationStatus.APPROVED)
        self.overall = User.objects.create_user("maint_overall", password="SchoolPass123!")
        UserProfile.objects.create(
            user=self.overall,
            school=self.school,
            role=Role.OVERALL_SUPERVISOR,
            school_password=self.overall.password,
        )
        self.admin = User.objects.create_user("maint_admin", password="AdminPass123!")
        UserProfile.objects.create(
            user=self.admin,
            school=None,
            role=Role.SUPERADMIN,
            school_password=self.admin.password,
        )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from django.test import override_settings

        cls._settings = override_settings(MAINTENANCE_MODE=True)
        cls._settings.enable()

    @classmethod
    def tearDownClass(cls):
        cls._settings.disable()
        super().tearDownClass()

    def test_school_user_cannot_login(self):
        response = self.client.post(
            "/login/",
            {"username": "maint_overall", "password": "SchoolPass123!"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_superadmin_can_login(self):
        response = self.client.post(
            "/login/",
            {"username": "maint_admin", "password": "AdminPass123!"},
        )
        self.assertEqual(response.status_code, 302)

    def test_logged_in_school_user_is_signed_out_on_request(self):
        self.client.force_login(self.overall)
        response = self.client.get("/overall/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)


class SchoolDeactivationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="platform", password="test")
        self.school = School.objects.create(
            name="Grace High",
            status=SchoolRegistrationStatus.APPROVED,
        )

    def test_deactivate_then_restore(self):
        from .school_utils import deactivate_school, restore_deactivated_school

        deactivate_school(school=self.school, by_user=self.admin)
        self.school.refresh_from_db()
        self.assertEqual(self.school.status, SchoolRegistrationStatus.DEACTIVATED)
        self.assertIsNotNone(self.school.deactivated_at)

        restore_deactivated_school(school=self.school)
        self.school.refresh_from_db()
        self.assertEqual(self.school.status, SchoolRegistrationStatus.APPROVED)
        self.assertIsNone(self.school.deactivated_at)

    def test_purge_after_grace_period(self):
        from datetime import timedelta

        from django.utils import timezone

        from .school_utils import purge_expired_deactivated_schools

        self.school.status = SchoolRegistrationStatus.DEACTIVATED
        self.school.deactivated_at = timezone.now() - timedelta(days=31)
        self.school.save(update_fields=["status", "deactivated_at"])

        removed = purge_expired_deactivated_schools()
        self.assertEqual(removed, ["Grace High"])
        self.assertFalse(School.objects.filter(name="Grace High").exists())


class SupervisorMarkStorageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="marker", password="test")
        self.school = School.objects.create(name="Mark School", status="approved")
        self.student = Student.objects.create(
            school=self.school,
            full_name="Learner",
            class_level=SecondaryClassLevel.S3,
        )
        self.old_scheme = AssessmentScheme.objects.create(name="Old scheme", active=False)
        self.sheet_scheme = AssessmentScheme.objects.create(name="Sheet scheme", active=True)
        self.old_comp = Competency.objects.create(
            scheme=self.old_scheme, name="Project planning", order=1
        )
        self.sheet_comp = Competency.objects.create(
            scheme=self.sheet_scheme, name="Project planning", order=1
        )

    def test_term1_marks_move_to_term3_without_overwriting(self):
        from .observation_utils import move_scores_between_terms

        assessment = ProjectAssessment.objects.create(
            student=self.student,
            scheme=self.sheet_scheme,
            year=2026,
            term=1,
            created_by=self.user,
        )
        CompetencyScore.objects.create(
            assessment=assessment, competency=self.sheet_comp, score=Decimal("80.00")
        )
        kept = ProjectAssessment.objects.create(
            student=self.student,
            scheme=self.old_scheme,
            year=2026,
            term=3,
            created_by=self.user,
        )

        moved = move_scores_between_terms(year=2026, from_term=1, to_term=3)
        self.assertEqual(moved, 1)
        assessment.refresh_from_db()
        kept.refresh_from_db()
        self.assertEqual(assessment.term, 3)
        self.assertEqual(kept.term, 3)
        self.assertEqual(assessment.scores.get().score, Decimal("80.00"))

    def test_marks_saved_on_another_scheme_show_on_the_score_sheet(self):
        from .observation_utils import student_display_score_maps

        assessment = ProjectAssessment.objects.create(
            student=self.student,
            scheme=self.old_scheme,
            year=2026,
            term=3,
            created_by=self.user,
        )
        CompetencyScore.objects.create(
            assessment=assessment,
            competency=self.old_comp,
            score=Decimal("64.50"),
            submitted_at=self.student.created_at,
        )

        maps = student_display_score_maps(
            [self.student],
            self.sheet_scheme,
            2026,
            3,
            checklist_for=lambda _student: None,
        )
        self.assertEqual(maps[self.student.id][self.sheet_comp.id], Decimal("64.50"))
