from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import AssessmentScheme, Competency


UGANDA_4 = [
    "Project planning",
    "Project implementation",
    "Project reporting",
    "Project dissemination",
]


class Command(BaseCommand):
    help = "Activate a single Uganda scheme with the 4 official competencies (and deactivate other schemes)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--scheme-name",
            default="Uganda Secondary Project (Official)",
            help="Name for the active Uganda scheme.",
        )

    def handle(self, *args, **opts):
        scheme_name: str = opts["scheme_name"]

        with transaction.atomic():
            # Deactivate all schemes first (keeps old data safe).
            AssessmentScheme.objects.update(active=False)

            scheme, _ = AssessmentScheme.objects.get_or_create(name=scheme_name)
            scheme.active = True
            scheme.save(update_fields=["active"])

            existing = {c.name.lower(): c for c in Competency.objects.filter(scheme=scheme)}

            # Ensure the 4 competencies exist in correct order.
            for order, name in enumerate(UGANDA_4, start=1):
                key = name.lower()
                if key in existing:
                    c = existing[key]
                    c.order = order
                    c.save(update_fields=["order"])
                else:
                    Competency.objects.create(scheme=scheme, name=name, order=order)

        self.stdout.write(self.style.SUCCESS(f"Active scheme set to: {scheme.name}"))

