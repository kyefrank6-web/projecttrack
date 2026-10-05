from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0020_school_deactivation_grace"),
    ]

    operations = [
        migrations.AddField(
            model_name="competencyscore",
            name="submitted_at",
            field=models.DateTimeField(
                blank=True,
                help_text="When this competency result was submitted (UNEB phase).",
                null=True,
            ),
        ),
    ]
