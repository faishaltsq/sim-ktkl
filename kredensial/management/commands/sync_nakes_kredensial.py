"""Sinkronkan field ringkasan kredensial pada model Nakes.

Field `status_kredensial` dan `kewenangan_klinis` pada Nakes adalah ringkasan
turunan — bukan sumber kebenaran. Command ini menurunkan nilainya dari
keputusan kredensial final.

Jalankan: py -3.12 manage.py sync_nakes_kredensial [--dry-run]
"""
from django.core.management.base import BaseCommand

from kredensial.services.summary_sync import compute_summary, sync_all


class Command(BaseCommand):
    help = 'Sinkronkan status_kredensial & kewenangan_klinis Nakes dari keputusan kredensial final.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Tampilkan perubahan tanpa menyimpan.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            from nakes.models import Nakes
            from kredensial.models import CredentialApplication

            nakes_ids = CredentialApplication.objects.values_list(
                'nakes_id', flat=True,
            ).distinct()
            changes = 0
            for nakes in Nakes.objects.filter(pk__in=list(nakes_ids)):
                summary = compute_summary(nakes)
                diffs = {
                    f: (getattr(nakes, f), v)
                    for f, v in summary.items()
                    if getattr(nakes, f) != v
                }
                if diffs:
                    changes += 1
                    self.stdout.write(
                        f'  {nakes.nama}: '
                        + ', '.join(f'{f} {old} → {new}' for f, (old, new) in diffs.items())
                    )
            self.stdout.write(self.style.WARNING(
                f'DRY RUN: {changes} nakes akan diperbarui.'
            ))
            return

        updated, checked = sync_all()
        self.stdout.write(self.style.SUCCESS(
            f'Sinkronisasi selesai: {updated} dari {checked} nakes diperbarui.'
        ))
