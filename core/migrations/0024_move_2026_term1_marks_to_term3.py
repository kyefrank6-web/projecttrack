from django.db import migrations


def forwards(apps, schema_editor):
    """
    The site used to store every supervisor submission as Term 1.
    Marks entered in 2026 belong on Term 3, which is the current school term.
    """
    from core.observation_utils import move_scores_between_terms

    move_scores_between_terms(year=2026, from_term=1, to_term=3)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0023_platformsettings"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
