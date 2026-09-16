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

        demo_user, created = User.objects.get_or_create(
            username='demo',
            defaults={
                'is_staff': False,
                'first_name': 'Tamu',
                'last_name': '(Demo)',
            }
        )
        demo_user.set_password('demo123')
        demo_user.save()
        self.stdout.write(self.style.SUCCESS('User demo dibuat/diperbarui (password: demo123)'))

        self._seed_demo_records(demo_user)

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

    def _seed_demo_records(self, demo_user):
        from datetime import date, timedelta
        from nakes.models import (
            Profesi, Nakes, EvaluasiOPPE, EvaluasiMutuKlinis,
            PelanggaranEtik, SidangEtik, EvaluasiKinerjaEtik,
            AgendaRapat, Regulasi, NotulenRapat, DokumenUmum
        )

        today = date.today()

        # Profesi
        p_atlm, _ = Profesi.objects.get_or_create(nama='ATLM')
        p_radio, _ = Profesi.objects.get_or_create(nama='Radiografer')
        p_fisio, _ = Profesi.objects.get_or_create(nama='Fisioterapis')

        # Nakes Demo
        nakes_demo_data = [
            {
                'nama': 'Ahmad Fauzi (Demo)',
                'profesi': p_atlm,
                'unit_kerja': 'Laboratorium Terpadu',
                'no_str': 'DEMO-STR-001',
                'masa_berlaku_str': today + timedelta(days=365),
                'no_sip': 'DEMO-SIP-001',
                'masa_berlaku_sip': today + timedelta(days=300),
                'status_kredensial': 'Selesai',
                'kewenangan_klinis': 'Aktif',
                'catatan': 'Contoh data demo untuk evaluasi komite',
            },
            {
                'nama': 'Dewi Lestari (Demo)',
                'profesi': p_radio,
                'unit_kerja': 'Radiologi Sentral',
                'no_str': 'DEMO-STR-002',
                'masa_berlaku_str': today + timedelta(days=45),  # warning near expiry
                'no_sip': 'DEMO-SIP-002',
                'masa_berlaku_sip': today + timedelta(days=60),
                'status_kredensial': 'Dalam Proses',
                'kewenangan_klinis': 'Proses',
                'catatan': 'Contoh STR mendekati masa kedaluwarsa',
            },
            {
                'nama': 'Bambang Pratama (Demo)',
                'profesi': p_fisio,
                'unit_kerja': 'Rehabilitasi Medik',
                'no_str': 'DEMO-STR-003',
                'masa_berlaku_str': today - timedelta(days=10),  # expired
                'no_sip': 'DEMO-SIP-003',
                'masa_berlaku_sip': today + timedelta(days=180),
                'status_kredensial': 'Belum Pengajuan',
                'kewenangan_klinis': 'Evaluasi',
                'catatan': 'Contoh nakes dengan STR kedaluwarsa',
            },
        ]

        created_nakes = []
        for d in nakes_demo_data:
            n, _ = Nakes.objects.update_or_create(
                no_str=d['no_str'],
                defaults={**d, 'created_by': demo_user}
            )
            created_nakes.append(n)

        # OPPE Demo
        if created_nakes:
            EvaluasiOPPE.objects.get_or_create(
                nakes=created_nakes[0],
                tahun=today.year,
                defaults={
                    'tanggal_evaluasi': today,
                    'skor_perilaku_1': 85, 'skor_perilaku_2': 90, 'skor_perilaku_3': 88,
                    'skor_perilaku_4': 85, 'skor_perilaku_5': 92, 'skor_perilaku_6': 88,
                    'skor_perilaku_7': 90, 'skor_profesional_1': 85, 'skor_profesional_2': 88,
                    'skor_profesional_3': 90, 'skor_profesional_4': 85, 'skor_kinerja_1': 90,
                    'skor_kinerja_2': 88, 'skor_kinerja_3': 92, 'skor_kinerja_4': 85,
                    'skor_kinerja_5': 88, 'skor_kinerja_6': 90, 'skor_kinerja_7': 85,
                    'skor_kinerja_8': 90, 'skor_kinerja_9': 88,
                    'penilai_nama': 'dr. Hendra, Sp.PK (Demo)',
                    'created_by': demo_user,
                }
            )

        # Mutu Demo
        EvaluasiMutuKlinis.objects.get_or_create(
            nama_indikator='Waktu Tunggu Hasil Lab Cito < 60 Menit (Demo)',
            periode_tahun=today.year,
            periode_bulan=today.month,
            defaults={
                'unit_kerja': 'Laboratorium',
                'standar_target': 90.0,
                'capaian': 94.5,
                'analisis': 'Capaian melampaui target standar mutu.',
                'rencana_tindak_lanjut': 'Pertahankan performa koordinasi antar analis.',
                'penanggung_jawab': 'PJ Lab Cito',
                'created_by': demo_user,
            }
        )

        # Agenda Rapat Demo
        agenda_demo, _ = AgendaRapat.objects.get_or_create(
            judul_rapat='Rapat Pleno Kredensial Berkala (Demo)',
            tanggal_rapat=today + timedelta(days=7),
            defaults={
                'jenis_rapat': 'Rapat Pleno',
                'waktu_mulai': '09:00',
                'waktu_selesai': '11:30',
                'tempat': 'Ruang Komite KTKL',
                'peserta': 'Seluruh Subkomite & Tim Kredensial',
                'keterangan': 'Contoh agenda rapat simulasi komite.',
                'created_by': demo_user,
            }
        )

        # Pelanggaran Etik Demo
        if len(created_nakes) > 1:
            pelanggaran_demo, _ = PelanggaranEtik.objects.get_or_create(
                nakes=created_nakes[1],
                tanggal_kejadian=today - timedelta(days=14),
                defaults={
                    'kategori': 'Ringan',
                    'deskripsi': 'Contoh pelaporan pelanggaran etika ketepatan waktu serah terima shift.',
                    'pelapor': 'Kepala Ruangan (Demo)',
                    'status': 'Dalam Investigasi',
                    'created_by': demo_user,
                }
            )

        self.stdout.write(self.style.SUCCESS('Data dummy untuk akun demo berhasil disiapkan.'))
