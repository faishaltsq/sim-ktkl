from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from nakes.models import Profesi, Nakes

DEFAULT_PROFESI = [
    'ATLM', 'Radiografer', 'Fisioterapis', 'Nutrisionis',
    'Perekam Medis', 'Apoteker', 'Sanitarian', 'Lainnya',
]

DUMMY_STRS = [
    'STR123456789',
    'STR987654321',
    'STR555666777',
    'STR111222333',
    'STR-001-2021',
    'STR-002-2022',
]


class Command(BaseCommand):
    help = 'Seed user dan profesi default, bersihkan data nakes dummy'

    def handle(self, *args, **options):
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'is_staff': True,
                'is_superuser': True,
                'first_name': 'Administrator',
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('User admin dibuat (password: admin123)'))

        pengurus, created = User.objects.get_or_create(
            username='pengurus',
            defaults={
                'is_staff': False,
                'first_name': 'Pengurus',
                'last_name': 'Kredensial',
            }
        )
        if created:
            pengurus.set_password('pengurus123')
            pengurus.save()
            self.stdout.write(self.style.SUCCESS('User pengurus dibuat (password: pengurus123)'))

        for nama in DEFAULT_PROFESI:
            _, created = Profesi.objects.get_or_create(nama=nama)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Profesi {nama} ditambahkan'))

        deleted_count, _ = Nakes.objects.filter(no_str__in=DUMMY_STRS).delete()
        if deleted_count:
            self.stdout.write(self.style.SUCCESS(f'Berhasil menghapus {deleted_count} data nakes dummy'))

        self.stdout.write(self.style.SUCCESS('Seed selesai.'))
