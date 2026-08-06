from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_observation_section_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ClassProjectTheme",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "class_level",
                    models.CharField(
                        choices=[
                            ("S1", "S1"),
                            ("S2", "S2"),
                            ("S3", "S3"),
                            ("S4", "S4"),
                            ("S5", "S5"),
                            ("S6", "S6"),
                        ],
                        max_length=2,
                    ),
                ),
                ("year", models.PositiveIntegerField()),
                ("theme", models.TextField(help_text="Official project theme for this class and year.")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "school",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="class_project_themes",
                        to="core.school",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="updated_class_project_themes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-year", "class_level"],
            },
        ),
        migrations.AddIndex(
            model_name="classprojecttheme",
            index=models.Index(fields=["school", "year", "class_level"], name="core_classp_school__a8f2c1_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="classprojecttheme",
            unique_together={("school", "class_level", "year")},
        ),
    ]
