from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_school_approval_superadmin"),
    ]

    operations = [
        migrations.AddField(
            model_name="school",
            name="theme",
            field=models.CharField(
                choices=[
                    ("royal_blue", "Royal Blue"),
                    ("forest_green", "Forest Green"),
                    ("purple_violet", "Purple Violet"),
                    ("sunset_orange", "Sunset Orange"),
                    ("crimson_red", "Crimson Red"),
                    ("teal_ocean", "Teal Ocean"),
                    ("navy_gold", "Navy & Gold"),
                    ("rose_pink", "Rose Pink"),
                ],
                default="royal_blue",
                max_length=32,
            ),
        ),
    ]
