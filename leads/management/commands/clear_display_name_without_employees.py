from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from leads.models import Lead


class Command(BaseCommand):
    help = "Clear display_name for leads that have no linked employees."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Do not write changes, only show how many leads would be updated.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Process only first N leads for testing.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        limit = options["limit"]

        qs = (
            Lead.objects
            .annotate(employee_count=Count("employees"))
            .filter(employee_count=0)
            .exclude(display_name="")
            .order_by("id")
        )

        total = qs.count()
        if limit and limit > 0:
            qs = qs[:limit]

        lead_ids = list(qs.values_list("id", flat=True))

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"Dry run: would clear display_name for {len(lead_ids)} of {total} matching leads."
            ))
            return

        with transaction.atomic():
            updated = Lead.objects.filter(id__in=lead_ids).update(display_name="")

        self.stdout.write(self.style.SUCCESS(
            f"Done. cleared_display_name={updated}, total_matching={total}"
        ))
