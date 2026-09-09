from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from nakes.models import Profesi

DEFAULT_PROFESI = [
    'ATLM', 'Radiografer', 'Fisioterapis', 'Nutrisionis',
    'Perekam Medis', 'Apoteker', 'Sanitarian', 'Lainnya',
]


class Command(BaseCommand):
    help = 'Seed user dan profesi default'

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

        self.stdout.write(self.style.SUCCESS('Seed selesai.'))
