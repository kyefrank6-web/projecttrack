from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0019_school_name_not_unique"),
    ]

    operations = [
        migrations.AddField(
            model_name="school",
            name="deactivated_at",
            field=models.DateTimeField(
                blank=True,
                help_text="When set, the school is inactive until permanently deleted after the grace period.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="school",
            name="deactivated_from_status",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Registration status to restore if deactivation is cancelled.",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="school",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending approval"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                    ("deactivated", "Deactivated (pending deletion)"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
    ]
