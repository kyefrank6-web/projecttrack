from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.models import Role, UserProfile

User = get_user_model()


class Command(BaseCommand):
    help = "Create or reset a platform superadmin account (approves schools, can delete schools)."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--password", required=True)
        parser.add_argument("--email", default="")

    def handle(self, *args, **opts):
        username = (opts["username"] or "").strip()
        password = opts["password"]
        email = (opts["email"] or "").strip()

        if not username or not password:
            self.stderr.write(self.style.ERROR("Username and password are required."))
            return

        user = User.objects.filter(username__iexact=username).first()
        created = False
        if user is None:
            user = User.objects.create_user(username=username, email=email, password=password)
            created = True
        else:
            user.set_password(password)
            if email:
                user.email = email

        user.is_staff = True
        user.is_superuser = True
        user.save()

        profile = UserProfile.objects.filter(user=user, school__isnull=True).first()
        if profile is None:
            profile = UserProfile.objects.create(
                user=user,
                school=None,
                role=Role.SUPERADMIN,
                school_password=user.password,
                must_change_password=False,
            )
            self.stdout.write(self.style.SUCCESS(f"Created superadmin profile for '{user.username}'."))
        else:
            profile.role = Role.SUPERADMIN
            profile.school_password = user.password
            profile.must_change_password = False
            profile.save(update_fields=["role", "school_password", "must_change_password"])
            self.stdout.write(self.style.SUCCESS(f"Updated superadmin profile for '{user.username}'."))

        action = "created" if created else "updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"Superadmin {action}. Login at /login/ with username '{user.username}'."
            )
        )
