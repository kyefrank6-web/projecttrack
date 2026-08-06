from django.db import migrations, models


CATEGORIES = [
    "material_identification",
    "project_process",
    "final_product",
]


def assign_categories(apps, schema_editor):
    ProjectEvidence = apps.get_model("core", "ProjectEvidence")
    student_ids = ProjectEvidence.objects.values_list("student_id", flat=True).distinct()
    for student_id in student_ids:
        rows = list(ProjectEvidence.objects.filter(student_id=student_id).order_by("uploaded_at", "id"))
        for idx, row in enumerate(rows):
            if idx < len(CATEGORIES):
                row.category = CATEGORIES[idx]
                row.save(update_fields=["category"])
            else:
                row.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_projectevidence"),
    ]

    operations = [
        migrations.AddField(
            model_name="projectevidence",
            name="category",
            field=models.CharField(
                choices=[
                    ("material_identification", "Material identification"),
                    ("project_process", "Project process"),
                    ("final_product", "Final product"),
                ],
                default="material_identification",
                max_length=40,
            ),
        ),
        migrations.RunPython(assign_categories, migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name="projectevidence",
            unique_together={("student", "category")},
        ),
        migrations.AddIndex(
            model_name="projectevidence",
            index=models.Index(fields=["student", "category"], name="core_projec_student_8f3a21_idx"),
        ),
    ]
