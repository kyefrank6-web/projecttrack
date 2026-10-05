import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0022_userprofile_role_per_school"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlatformSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "maintenance_enabled",
                    models.BooleanField(
                        default=False,
                        help_text="When enabled, only platform superadmins can sign in.",
                    ),
                ),
                (
                    "maintenance_message",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Optional message shown to users during maintenance.",
                    ),
                ),
                ("maintenance_updated_at", models.DateTimeField(blank=True, null=True)),
                (
                    "maintenance_updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="maintenance_updates",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Platform settings",
                "verbose_name_plural": "Platform settings",
            },
        ),
    ]
