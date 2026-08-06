from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from .forms import RegisterSchoolForm
from .models import AcademicPromotionRun, Role, School, SchoolRegistrationStatus, SecondaryClassLevel, Student, UserProfile
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
