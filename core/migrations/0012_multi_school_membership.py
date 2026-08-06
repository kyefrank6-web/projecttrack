from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def copy_user_password_to_membership(apps, schema_editor):
    UserProfile = apps.get_model("core", "UserProfile")
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    for profile in UserProfile.objects.select_related("user").all():
        if profile.school_password:
            continue
        try:
            user = User.objects.get(pk=profile.user_id)
        except User.DoesNotExist:
            continue
        if user.password:
            profile.school_password = user.password
            profile.save(update_fields=["school_password"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_class_project_theme"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="school_password",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Hashed password for this school (allows same username, different passwords per school).",
                max_length=128,
            ),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="memberships",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(copy_user_password_to_membership, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="userprofile",
            constraint=models.UniqueConstraint(
                fields=("user", "school"),
                name="unique_user_school_membership",
            ),
        ),
    ]
