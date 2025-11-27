import pandas as pd
import numpy as np
from django.core.management.base import BaseCommand
from django.utils import timezone
from analytics.models import ProductVersion, VisitSession, PageHit, UXIssue, DailyStat
from datetime import datetime
import os
from analytics.ai_service import analyze_issue_with_ai

class Command(BaseCommand):
    help = 'Ingests Parquet data from Yandex Metrica and runs UX analysis'

    def add_arguments(self, parser):
        parser.add_argument('--visits', type=str, help='Path to visits parquet file')
        parser.add_argument('--hits', type=str, help='Path to hits parquet file')
        parser.add_argument('--product-version', type=str, help='Version name (e.g., "v1.0")')
        parser.add_argument('--year', type=int, help='Year of data (e.g., 2022)')

    def handle(self, *args, **options):
        visits_path = options['visits']
        hits_path = options['hits']
        version_name = options['product_version']
        year = options['year']

        if not visits_path or not hits_path or not version_name:
            self.stdout.write(self.style.ERROR('Please provide --visits, --hits and --product-version'))
            return

        self.stdout.write(f"Starting ingestion for {version_name}...")

        # 1. Create or Get Version
        version, created = ProductVersion.objects.get_or_create(
            name=version_name,
            defaults={'release_date': datetime(year, 1, 1), 'is_active': True}
        )
# ... rest of the file
