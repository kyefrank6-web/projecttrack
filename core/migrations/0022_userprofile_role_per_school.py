from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0021_competencyscore_submitted_at"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="userprofile",
            name="unique_user_school_membership",
        ),
        migrations.AddConstraint(
            model_name="userprofile",
            constraint=models.UniqueConstraint(
                fields=("user", "school", "role"),
                name="unique_user_school_role_membership",
            ),
        ),
    ]
