from django.db import migrations, models


def copy_cohort_year_to_format_year(apps, schema_editor):
    ObservationChecklist = apps.get_model("core", "ObservationChecklist")
    for row in ObservationChecklist.objects.filter(cohort_year__isnull=False, format_year__isnull=True):
        row.format_year = row.cohort_year
        row.save(update_fields=["format_year"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0015_observation_checklist_cohort_year"),
    ]

    operations = [
        migrations.AddField(
            model_name="observationchecklist",
            name="format_year",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="UNEB checklist format (built-in 2025 or 2026 structure). Can differ from cohort year.",
                null=True,
            ),
        ),
        migrations.RunPython(copy_cohort_year_to_format_year, migrations.RunPython.noop),
    ]
