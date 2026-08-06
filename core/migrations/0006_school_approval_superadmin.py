from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def approve_existing_schools(apps, schema_editor):
    School = apps.get_model("core", "School")
    School.objects.all().update(status="approved")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_student_project_title"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="school",
            name="rejection_reason",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="school",
            name="reviewed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="school",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending approval"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="school",
            name="reviewed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reviewed_schools",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="school",
            name="overall_supervisor",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="overall_for_school",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="school",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="user_profiles",
                to="core.school",
            ),
        ),
        migrations.RunPython(approve_existing_schools, migrations.RunPython.noop),
    ]
