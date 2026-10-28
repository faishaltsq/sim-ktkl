"""Seed akun demo per role Sub. Kredensial.

Membuat satu akun per role dengan password seragam agar mudah dikomunikasikan
ke stakeholder untuk pengujian. Idempoten — aman dijalankan berulang.

Password default: Kredensial@123 (ubah via environment KREDENSIAL_DEMO_PASSWORD)

Jalankan: py -3.12 manage.py seed_kredensial_accounts
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group

from kredensial.permissions import ROLE_GROUPS

DEFAULT_PASSWORD = os.environ.get('KREDENSIAL_DEMO_PASSWORD', 'Kredensial@123')

# username, role, nama lengkap
AKUN = [
    ('kred_sekretariat', 'sekretariat', 'Sekretariat Kredensial'),
    ('kred_verifikator', 'verifikator', 'Verifikator Dokumen'),
    ('kred_asesor', 'asesor', 'Asesor Kompetensi'),
    ('kred_subkomite', 'subkomite', 'Anggota Subkomite'),
    ('kred_ketua', 'ketua_komite', 'Ketua Komite'),
    ('kred_pejabat', 'pejabat', 'Pejabat Berwenang'),
    ('kred_auditor', 'auditor', 'Auditor Kredensial'),
]


class Command(BaseCommand):
    help = 'Buat akun demo per role Sub. Kredensial (idempoten).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            default=DEFAULT_PASSWORD,
            help=f'Password untuk semua akun (default: {DEFAULT_PASSWORD})',
        )

    def handle(self, *args, **options):
        password = options['password']

        for username, role, full_name in AKUN:
            group_name = ROLE_GROUPS[role]
            group, _ = Group.objects.get_or_create(name=group_name)

            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': full_name,
                    'is_staff': False,
                    'is_active': True,
                },
            )
            user.set_password(password)
            user.save()

            if not user.groups.filter(name=group_name).exists():
                user.groups.add(group)

            status = 'dibuat' if created else 'diperbarui'
            self.stdout.write(self.style.SUCCESS(
                f'  {username} ({role}) {status} — group: {group_name}'
            ))

        self.stdout.write(self.style.WARNING(
            f'\nPassword semua akun: {password}\n'
            'Ganti password setelah pengujian selesai.'
        ))
