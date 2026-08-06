from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.models import Role, UserProfile

User = get_user_model()


class Command(BaseCommand):
    help = "Create a platform superadmin account (approves schools, can delete schools)."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--password", required=True)
        parser.add_argument("--email", default="")

    def handle(self, *args, **opts):
        username = opts["username"]
        password = opts["password"]
        email = opts["email"]

        user, created = User.objects.get_or_create(username=username, defaults={"email": email})
        if created:
            user.set_password(password)
        else:
            user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.save()

        profile, profile_created = UserProfile.objects.get_or_create(
            user=user,
            school=None,
            defaults={"role": Role.SUPERADMIN, "school_password": user.password},
        )
        if not profile_created:
            profile.role = Role.SUPERADMIN
            profile.school_password = user.password
            profile.save(update_fields=["role", "school_password"])

        self.stdout.write(self.style.SUCCESS(f"Superadmin ready. Login at /login/ as '{username}'."))
