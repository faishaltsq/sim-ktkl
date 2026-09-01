from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from nakes.models import Nakes


class Command(BaseCommand):
    help = 'Seed data dummy untuk development'

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

        data = [
            {
                'nama': 'Siti Rahma, A.Md.AK',
                'profesi': 'ATLM',
                'unit_kerja': 'Laboratorium Patologi Klinik',
                'no_str': 'STR123456789',
                'masa_berlaku_str': '2026-11-30',
                'no_sip': 'SIP/LAB/012/2024',
                'masa_berlaku_sip': '2027-05-15',
                'status_kredensial': 'Selesai',
                'kewenangan_klinis': 'Aktif',
            },
            {
                'nama': 'Ahmad Fauzi, S.Tr.Kes',
                'profesi': 'Radiografer',
                'unit_kerja': 'Instalasi Radiologi',
                'no_str': 'STR987654321',
                'masa_berlaku_str': '2026-08-10',
                'no_sip': 'SIP/RAD/045/2023',
                'masa_berlaku_sip': '2026-09-01',
                'status_kredensial': 'Dalam Proses',
                'kewenangan_klinis': 'Evaluasi',
            },
            {
                'nama': 'Dewi Lestari, S.Ft',
                'profesi': 'Fisioterapis',
                'unit_kerja': 'Instalasi Rehabilitasi Medik',
                'no_str': 'STR555666777',
                'masa_berlaku_str': '2028-03-20',
                'no_sip': 'SIP/FT/078/2024',
                'masa_berlaku_sip': '2028-06-01',
                'status_kredensial': 'Selesai',
                'kewenangan_klinis': 'Aktif',
            },
            {
                'nama': 'Budi Santoso, S.Gz',
                'profesi': 'Nutrisionis',
                'unit_kerja': 'Instalasi Gizi',
                'no_str': 'STR111222333',
                'masa_berlaku_str': '2026-10-15',
                'no_sip': 'SIP/GZ/034/2023',
                'masa_berlaku_sip': '2026-12-01',
                'status_kredensial': 'Selesai',
                'kewenangan_klinis': 'Aktif',
            },
        ]

        for item in data:
            obj, created = Nakes.objects.get_or_create(
                no_str=item['no_str'],
                defaults={**item, 'created_by': admin_user},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Nakes {obj.nama} ditambahkan'))
            else:
                self.stdout.write(f'Nakes {obj.nama} sudah ada, skip')

        self.stdout.write(self.style.SUCCESS('Seed selesai.'))
