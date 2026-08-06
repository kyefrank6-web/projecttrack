from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_observation_checklist"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="observationcriterion",
            unique_together=set(),
        ),
        migrations.AddField(
            model_name="observationcriterion",
            name="section_code",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="observationcriterion",
            name="section_preamble",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="observationcriterion",
            name="section_title",
            field=models.CharField(blank=True, default="", max_length=300),
        ),
        migrations.AlterField(
            model_name="observationcriterion",
            name="max_rating",
            field=models.PositiveSmallIntegerField(default=1),
        ),
    ]
