import time
from django.core.management.base import BaseCommand
from django.db.models import Q
from analytics.models import UXIssue
from analytics.ai_service import (
    analyze_issue_with_ai,
    generate_stub_hypothesis,
    get_stub_text_variants,
)


class Command(BaseCommand):
    help = "Regenerate AI hypotheses for UX issues (useful after adding API keys)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Regenerate for all issues, not only stub/empty ones",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Process only first N issues (default: all matched)",
        )
        parser.add_argument(
            "--sleep",
            type=float,
            default=0.0,
            help="Delay between requests in seconds to avoid rate limits",
        )

    def handle(self, *args, **options):
        force = options["force"]
        limit = options["limit"]
        sleep_interval = options["sleep"]

        # Build list of known stub texts to detect placeholders (новый JSON и легаси-формат)
        stub_texts = get_stub_text_variants(include_legacy=True)

        qs = UXIssue.objects.all().order_by("-created_at")
        if not force:
            qs = qs.filter(
                Q(ai_hypothesis__isnull=True)
                | Q(ai_hypothesis__exact="")
                | Q(ai_hypothesis__in=stub_texts)
            )

        total = qs.count() if limit == 0 else min(qs.count(), limit)
        if total == 0:
            self.stdout.write(self.style.SUCCESS("Nothing to update — all issues already have AI text."))
            return

        self.stdout.write(f"Regenerating AI hypotheses for {total} issue(s)...")

        updated = []
        for idx, issue in enumerate(qs[:limit or None], start=1):
            metrics_context = (
                f"Пользователи: {issue.affected_sessions}, "
                f"Влияние: {issue.impact_score}, "
                f"Критичность: {issue.severity}"
            )
            new_text = analyze_issue_with_ai(issue.issue_type, issue.location_url, metrics_context)
            issue.ai_hypothesis = new_text
            updated.append(issue)

            self.stdout.write(f"[{idx}/{total}] {issue.get_issue_type_display()} @ {issue.location_url} -> updated")
            if sleep_interval > 0:
                time.sleep(sleep_interval)

        UXIssue.objects.bulk_update(updated, ["ai_hypothesis"])
        self.stdout.write(self.style.SUCCESS(f"Updated {len(updated)} issue(s) with AI responses."))
