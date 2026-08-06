from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def copy_s3_themes_to_cohorts(apps, schema_editor):
    ClassProjectTheme = apps.get_model("core", "ClassProjectTheme")
    CohortProjectTheme = apps.get_model("core", "CohortProjectTheme")
    for row in ClassProjectTheme.objects.filter(class_level="S3"):
        CohortProjectTheme.objects.get_or_create(
            school_id=row.school_id,
            cohort_year=row.year,
            defaults={
                "theme": row.theme,
                "updated_by_id": row.updated_by_id,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0013_student_supervisor_nullable"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CohortProjectTheme",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "cohort_year",
                    models.PositiveIntegerField(
                        help_text="Calendar year when learners enter S.3 Term 1 and UNEB publishes the theme."
                    ),
                ),
                ("theme", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "school",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cohort_project_themes",
                        to="core.school",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="updated_cohort_project_themes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-cohort_year"],
            },
        ),
        migrations.AddIndex(
            model_name="cohortprojecttheme",
            index=models.Index(fields=["school", "cohort_year"], name="core_cohort_school__a8f2c1_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="cohortprojecttheme",
            unique_together={("school", "cohort_year")},
        ),
        migrations.RunPython(copy_s3_themes_to_cohorts, migrations.RunPython.noop),
    ]
