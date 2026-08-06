from django.db import migrations, models


def set_s3_checklist_cohort_years(apps, schema_editor):
    ObservationChecklist = apps.get_model("core", "ObservationChecklist")
    for cl in ObservationChecklist.objects.filter(class_level="S3", cohort_year__isnull=True):
        cl.cohort_year = cl.year
        cl.save(update_fields=["cohort_year"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_cohort_project_theme"),
    ]

    operations = [
        migrations.AddField(
            model_name="observationchecklist",
            name="cohort_year",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="UNEB cohort (S.3 Term 1 year). S.3 and S.4 learners in this cohort use this checklist.",
                null=True,
            ),
        ),
        migrations.AddIndex(
            model_name="observationchecklist",
            index=models.Index(
                fields=["school", "cohort_year", "class_level", "active"],
                name="core_observ_school__b7e4a2_idx",
            ),
        ),
        migrations.RunPython(set_s3_checklist_cohort_years, migrations.RunPython.noop),
    ]
