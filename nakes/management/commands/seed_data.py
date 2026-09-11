from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from nakes.models import Profesi, Nakes

DEFAULT_PROFESI = [
    'ATLM', 'Radiografer', 'Fisioterapis', 'Nutrisionis', 'Perekam Medis',
    'Apoteker', 'Sanitarian',
    'Tenaga Teknik Kefarmasian', 'Dietisien', 'Elektromedis',
    'Terapis Wicara', 'Ortotik Prostetik', 'Penata Anestesi',
    'Terapis Gigi & Mulut', 'Perawat Gigi & Mulut',
    'Teknis Bank Darah', 'Psikolog Klinis',
]

DUMMY_STRS = [
    'STR123456789',
    'STR987654321',
    'STR555666777',
    'STR111222333',
    'STR-001-2021',
    'STR-002-2022',
]

UNIT_TO_PROFESI = {
    'farmasi': 'Tenaga Teknik Kefarmasian',
    'kefarmasian': 'Tenaga Teknik Kefarmasian',
    'apotek': 'Tenaga Teknik Kefarmasian',
    'gizi': 'Dietisien',
    'nutrisi': 'Dietisien',
    'dietisien': 'Dietisien',
    'elektromedis': 'Elektromedis',
    'elektromedik': 'Elektromedis',
    'ipsrs': 'Elektromedis',
    'teknik medis': 'Elektromedis',
    'wicara': 'Terapis Wicara',
    'terapi wicara': 'Terapis Wicara',
    'ortotik': 'Ortotik Prostetik',
    'prostetik': 'Ortotik Prostetik',
    'anestesi': 'Penata Anestesi',
    'kamar operasi': 'Penata Anestesi',
    'ok': 'Penata Anestesi',
    'bedah': 'Penata Anestesi',
    'gigi': 'Terapis Gigi & Mulut',
    'dental': 'Terapis Gigi & Mulut',
    'mulut': 'Terapis Gigi & Mulut',
    'bank darah': 'Teknis Bank Darah',
    'bdrs': 'Teknis Bank Darah',
    'utd': 'Teknis Bank Darah',
    'transfusi': 'Teknis Bank Darah',
    'psikolog': 'Psikolog Klinis',
    'psikologi': 'Psikolog Klinis',
    'jiwa': 'Psikolog Klinis',
    'kesehatan jiwa': 'Psikolog Klinis',
}


class Command(BaseCommand):
    help = 'Seed user, profesi, bersihkan dummy, migrasi profesi Lainnya'

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
                self.stdout.write(self.style.SUCCESS(f'Profesi "{nama}" ditambahkan'))

        # Migrasi nakes berprofesi "Lainnya" ke profesi spesifik
        try:
            profesi_lainnya = Profesi.objects.get(nama='Lainnya')
            nakes_lainnya = Nakes.objects.filter(profesi=profesi_lainnya).select_related('profesi')
            total_lainnya = nakes_lainnya.count()

            if total_lainnya > 0:
                self.stdout.write(f'Migrasi {total_lainnya} nakes dari profesi "Lainnya"...')
                berhasil = 0
                gagal = []

                for nakes in nakes_lainnya:
                    unit = nakes.unit_kerja.lower()
                    target_nama = None
                    for keyword, profesi_nama in UNIT_TO_PROFESI.items():
                        if keyword in unit:
                            target_nama = profesi_nama
                            break

                    if target_nama:
                        target_profesi, _ = Profesi.objects.get_or_create(nama=target_nama)
                        nakes.profesi = target_profesi
                        nakes.save(update_fields=['profesi'])
                        berhasil += 1
                        self.stdout.write(f'  ✓ {nakes.nama} ({nakes.unit_kerja}) → "{target_nama}"')
                    else:
                        gagal.append(nakes)

                if berhasil:
                    self.stdout.write(self.style.SUCCESS(f'Berhasil migrasi {berhasil} nakes ke profesi spesifik'))

                if gagal:
                    self.stdout.write(self.style.WARNING(
                        f'⚠ {len(gagal)} nakes tidak dapat diidentifikasi profesinya (unit kerja tidak dikenali):'
                    ))
                    for n in gagal:
                        self.stdout.write(f'  - {n.nama} | Unit: {n.unit_kerja}')
                    self.stdout.write('  → Silakan ubah manual via Django Admin atau halaman Edit Nakes.')

            # Hapus profesi "Lainnya" jika sudah tidak ada nakes yang memakainya
            profesi_lainnya.refresh_from_db()
            sisa = Nakes.objects.filter(profesi=profesi_lainnya).count()
            if sisa == 0:
                profesi_lainnya.delete()
                self.stdout.write(self.style.SUCCESS('Profesi "Lainnya" berhasil dihapus (sudah tidak ada nakes).'))
            else:
                self.stdout.write(self.style.WARNING(
                    f'Profesi "Lainnya" dipertahankan karena masih ada {sisa} nakes yang belum di-reassign.'
                ))

        except Profesi.DoesNotExist:
            pass  # "Lainnya" sudah tidak ada, tidak perlu migrasi

        deleted_count, _ = Nakes.objects.filter(no_str__in=DUMMY_STRS).delete()
        if deleted_count:
            self.stdout.write(self.style.SUCCESS(f'Berhasil menghapus {deleted_count} data nakes dummy'))

        self.stdout.write(self.style.SUCCESS('Seed selesai.'))
