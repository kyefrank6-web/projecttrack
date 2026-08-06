from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.models import AssessmentScheme, Competency, Role, School, SchoolRegistrationStatus, UserProfile


User = get_user_model()


DEFAULT_UGANDA_COMPETENCIES = [
    "Project planning",
    "Project implementation",
    "Project reporting",
    "Project dissemination",
]


class Command(BaseCommand):
    help = "Create the first school + overall supervisor, and seed a default competency scheme."

    def add_arguments(self, parser):
        parser.add_argument("--school-name", required=True)
        parser.add_argument("--overall-username", required=True)
        parser.add_argument("--overall-password", required=True)
        parser.add_argument("--overall-email", default="")

    def handle(self, *args, **opts):
        school_name = opts["school_name"]
        username = opts["overall_username"]
        password = opts["overall_password"]
        email = opts["overall_email"]

        user, created = User.objects.get_or_create(username=username, defaults={"email": email})
        if created:
            user.set_password(password)
            user.save()
        else:
            self.stdout.write(self.style.WARNING("Overall user already existed; leaving password unchanged."))

        school, school_created = School.objects.get_or_create(
            name=school_name,
            defaults={"overall_supervisor": user, "status": SchoolRegistrationStatus.APPROVED},
        )
        if not school_created:
            school.overall_supervisor = user
            school.status = SchoolRegistrationStatus.APPROVED
            school.save(update_fields=["overall_supervisor", "status"])

        UserProfile.objects.get_or_create(
            user=user,
            school=school,
            defaults={"role": Role.OVERALL_SUPERVISOR, "school_password": user.password},
        )

        scheme, _ = AssessmentScheme.objects.get_or_create(name="Uganda Secondary Project (Default)", defaults={"active": True})
        if scheme.competencies.count() == 0:
            for i, name in enumerate(DEFAULT_UGANDA_COMPETENCIES, start=1):
                Competency.objects.create(scheme=scheme, name=name, order=i)

        self.stdout.write(self.style.SUCCESS("Bootstrap complete. You can now login as the overall supervisor."))

