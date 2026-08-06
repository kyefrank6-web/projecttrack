from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_school_theme"),
    ]

    operations = [
        migrations.AddField(
            model_name="school",
            name="mission",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="school",
            name="motto",
            field=models.CharField(blank=True, default="", max_length=300),
        ),
        migrations.AddField(
            model_name="school",
            name="vision",
            field=models.TextField(blank=True, default=""),
        ),
    ]
