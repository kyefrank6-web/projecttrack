from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import core.models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_school_vision_mission_motto"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ObservationChecklist",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=300)),
                ("year", models.PositiveIntegerField()),
                ("term", models.PositiveSmallIntegerField(blank=True, choices=[(1, "Term 1"), (2, "Term 2"), (3, "Term 3")], null=True)),
                ("class_level", models.CharField(blank=True, choices=[("S1", "S1"), ("S2", "S2"), ("S3", "S3"), ("S4", "S4"), ("S5", "S5"), ("S6", "S6")], default="", max_length=2)),
                ("pdf_file", models.FileField(upload_to=core.models._checklist_pdf_upload_to)),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("scheme", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="observation_checklists", to="core.assessmentscheme")),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="observation_checklists", to="core.school")),
                ("uploaded_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="uploaded_checklists", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-year", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ObservationCriterion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order", models.PositiveIntegerField(default=0)),
                ("description", models.TextField()),
                ("max_rating", models.PositiveSmallIntegerField(default=3)),
                ("checklist", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="criteria", to="core.observationchecklist")),
                ("competency", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="observation_criteria", to="core.competency")),
            ],
            options={
                "ordering": ["competency__order", "order", "id"],
                "unique_together": {("checklist", "competency", "order")},
            },
        ),
        migrations.CreateModel(
            name="StudentObservationRating",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("year", models.PositiveIntegerField()),
                ("term", models.PositiveSmallIntegerField(choices=[(1, "Term 1"), (2, "Term 2"), (3, "Term 3")])),
                ("rating", models.PositiveSmallIntegerField(default=0)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assessed_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="observation_ratings_given", to=settings.AUTH_USER_MODEL)),
                ("checklist", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ratings", to="core.observationchecklist")),
                ("criterion", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ratings", to="core.observationcriterion")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="observation_ratings", to="core.student")),
            ],
            options={
                "indexes": [models.Index(fields=["student", "year", "term"], name="core_studen_student_8f0a21_idx")],
                "unique_together": {("student", "criterion", "year", "term")},
            },
        ),
        migrations.AddIndex(
            model_name="observationchecklist",
            index=models.Index(fields=["school", "year", "active"], name="core_observ_school__a8ea0d_idx"),
        ),
    ]
