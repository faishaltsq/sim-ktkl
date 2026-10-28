"""Seed master data Sub. Kredensial — syarat dokumen & katalog kewenangan.

Data ini ACUAN AWAL yang dapat dikonfigurasi administrator RS. Dasar:
- UU No. 17/2023 tentang Kesehatan
- Permenkes No. 13/2025 tentang Pengelolaan SDM Kesehatan
- Permenkes No. 6/2026 tentang Rumah Sakit
- Standar profesi masing-masing (Konsil/Organisasi Profesi)

CATATAN: Daftar kewenangan klinis bersifat CONFIGURABLE. Administrator WAJIB
meninjau dan menyesuaikan dengan SOP serta regulasi internal RS sebelum
digunakan operasional. Seeder ini idempoten (get_or_create) sehingga aman
dijalankan berulang.

Jalankan: py -3.12 manage.py seed_kredensial_master
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

from nakes.models import Profesi
from kredensial.models import (
    CredentialRequirement,
    ClinicalPrivilege,
)
from kredensial.permissions import ROLE_GROUPS

# ==========================================
# SYARAT DOKUMEN PER PROFESI
# ==========================================
# Format: (kategori, nama_syarat, wajib, masa_berlaku_hari, referensi_regulasi)
# masa_berlaku_hari=None → tidak ada aturan kedaluwarsa dokumen

SYARAT_UMUM = [
    ('identitas', 'KTP / Kartu Identitas Resmi', True, None,
     'UU No. 17/2023 Pasal 233 — identitas prakter'),
    ('str', 'Surat Tanda Registrasi (STR)', True, 1825,
     'Permenkes No. 13/2025 — STR wajib bagi seluruh tenaga kesehatan'),
    ('pendidikan', 'Ijazah Terakhir yang Dilegali', True, None,
     'Permenkes No. 13/2025 — verifikasi kualifikasi pendidikan'),
    ('kompetensi', 'Sertifikat Kompetensi Profesi', True, 1825,
     'Standar Konsil/Organisasi Profesi masing-masing'),
    ('pelatihan', 'Sertifikat Pelatihan / Diklat Terkait', False, None,
     'SOP Internal RS — pengembangan kompetensi berkelanjutan'),
    ('pengalaman', 'Bukti Pengalaman Kerja / Surat Keterangan Kerja', False, None,
     'SOP Internal RS'),
]

SYARAT_SIP = ('sip', 'Surat Izin Praktik (SIP)', True, 1825,
              'UU No. 17/2023 Pasal 234 — SIP wajib bagi tenaga yang memberikan pelayanan langsung')

# Profesi yang WAJIB memiliki SIP (memberikan pelayanan kesehatan langsung)
PROFESI_WAJIB_SIP = [
    'Radiografer', 'Fisioterapis', 'Apoteker', 'Nutrisionis', 'Dietisien',
    'Terapis Wicara', 'Ortotik Prostetik', 'Penata Anestesi',
    'Terapis Gigi & Mulut', 'Perawat Gigi & Mulut', 'Psikolog Klinis',
    'Tenaga Teknik Kefarmasian', 'Sanitarian',
]

# Profesi teknis/administratif — SIP tidak selalu dipersyaratkan
PROFESI_TEKNIS = ['ATLM', 'Perekam Medis', 'Elektromedis', 'Teknis Bank Darah']

# ==========================================
# KATALOG KEWENANGAN KLINIS PER PROFESI
# ==========================================
# Format: (kode, nama, deskripsi, ruang_lingkup, kompetensi_wajib, aturan_supervisi)
# ACUAN AWAL — administrator RS harus meninjau & menyesuaikan.

KATALOG = {
    'ATLM': [
        ('ATLM-01', 'Pemeriksaan Hematologi Dasar',
         'Pemeriksaan darah lengkap, hitung jenis leukosit, dan uji hemostatik dasar',
         'Laboratorium Klinik — bagian hematologi',
         'Sertifikat kompetensi ATLM; pelatihan hematologi dasar',
         'Supervisi penanggung jawab laboratorium untuk hasil kritis'),
        ('ATLM-02', 'Pemeriksaan Kimia Klinik',
         'Analisis kadar glukosa, fungsi hati, fungsi ginjal, elektrolit, dan lipid',
         'Laboratorium Klinik — bagian kimia klinik',
         'Sertifikat kompetensi ATLM; pelatihan kimia klinik',
         'Verifikasi hasil abnormal oleh penanggung jawab'),
        ('ATLM-03', 'Pemeriksaan Mikrobiologi Dasar',
         'Pewarnaan Gram, kultur dasar, dan uji kepekaan antimikroba',
         'Laboratorium Klinik — bagian mikrobiologi',
         'Sertifikat kompetensi ATLM; pelatihan biosafety',
         'Supervisi wajib untuk identifikasi organisme patogen'),
        ('ATLM-04', 'Pemeriksaan Urinalisis & Cairan Tubuh',
         'Analisis urin lengkap dan analisis cairan tubuh (CSF, pleura, sendi)',
         'Laboratorium Klinik',
         'Sertifikat kompetensi ATLM',
         'Tidak memerlukan supervisi khusus'),
    ],
    'Radiografer': [
        ('RAD-01', 'Pemeriksaan Radiografi Konvensional',
         'Pemotretan radiografi dada, abdomen, ekstremitas, dan tengkorak',
         'Instalasi Radiologi — ruang radiografi konvensional',
         'Sertifikat kompetensi radiografer; pelatihan radioprotection',
         'Supervisi radiolog untuk kontras dan kasus pediatrik'),
        ('RAD-02', 'Pemeriksaan CT-Scan',
         'Akuisisi gambar tomografi terkomputerisasi sesuai protokol',
         'Instalasi Radiologi — ruang CT',
         'Sertifikat kompetensi radiografer; pelatihan CT khusus',
         'Supervisi radiolog untuk protokol kontras'),
        ('RAD-03', 'Pemeriksaan Ultrasonografi',
         'Pemeriksaan USG abdomen, obstetri, dan bagian lunak',
         'Instalasi Radiologi — ruang USG',
         'Sertifikat kompetensi radiografer; pelatihan USG',
         'Interpretasi oleh dokter radiologi'),
        ('RAD-04', 'Pemeriksaan Mamografi',
         'Pemeriksaan mamografi sesuai protokol skrining/diagnostik',
         'Instalasi Radiologi',
         'Sertifikat kompetensi radiografer; pelatihan mamografi',
         'Supervisi radiolog untuk hasil BI-RADS tinggi'),
    ],
    'Fisioterapis': [
        ('FIS-01', 'Terapi Latihan Dasar',
         'Latihan rentang gerak, penguatan otot, dan latihan keseimbangan',
         'Instalasi Fisioterapi',
         'Sertifikat kompetensi fisioterapi; STR aktif',
         'Tidak memerlukan supervisi khusus'),
        ('FIS-02', 'Terapi Modalitas Fisik',
         'Penggunaan TENS, US, shortwave, laser terapi, dan krioterapi',
         'Instalasi Fisioterapi',
         'Sertifikat kompetensi fisioterapi; pelatihan modalitas',
         'Supervisi untuk kasus pasca operasi dan kondisi akut'),
        ('FIS-03', 'Fisioterapi Kardiopulmoner',
         'Rehabilitasi pasien gangguan kardiak dan respirasi',
         'Instalasi Fisioterapi / ICU',
         'Sertifikat kompetensi fisioterapi; pelatihan kardiopulmoner',
         'Supervisi wajib — koordinasi dengan dokter spesialis'),
        ('FIS-04', 'Fisioterapi Neurologis',
         'Rehabilitasi pasien stroke, cedera kepala, dan gangguan neuromuskuler',
         'Instalasi Fisioterapi',
         'Sertifikat kompetensi fisioterapi; pelatihan neurologis',
         'Supervisi wajib untuk pasien risiko tinggi'),
    ],
    'Apoteker': [
        ('FAR-01', 'Dispensing Obat',
         'Penyiapan, pemberian, dan informasi obat kepada pasien rawat jalan',
         'Instalasi Farmasi — bagian rawat jalan',
         'Sertifikat kompetensi apoteker; STR aktif',
         'Tidak memerlukan supervisi khusus'),
        ('FAR-02', 'Farmasi Klinik — Review Resep',
         'Review keseuaian dosis, interaksi, dan duplikasi terapi',
         'Instalasi Farmasi — farmasi klinik',
         'Sertifikat kompetensi apoteker; pelatihan farmasi klinik',
         'Supervisi apoteker senior untuk kasus kompleks'),
        ('FAR-03', 'Sterile Compounding',
         'Penyiapan sediaan steril termasuk TPN dan kemoterapi',
         'Instalasi Farmasi — ruang steril',
         'Sertifikat kompetensi apoteker; pelatihan aseptic technique',
         'Supervisi wajib — verifikasi ganda sebelum diserahkan'),
        ('FAR-04', 'Manajemen Obat & Logistik',
         'Pengelolaan stok, pengadaan, dan pengendalian obat narkotika/psikotropika',
         'Instalasi Farmasi',
         'Sertifikat kompetensi apoteker; pelatihan SIPA',
         'Verifikasi bersama kepala instalasi farmasi'),
    ],
    'Nutrisionis': [
        ('NUT-01', 'Asesmen Status Gizi',
         'Skrining dan asesmen status gizi pasien rawat inap dan jalan',
         'Instalasi Gizi',
         'Sertifikat kompetensi nutrisionis; STR aktif',
         'Tidak memerlukan supervisi khusus'),
        ('NUT-02', 'Perencanaan & Evaluasi Diet',
         'Perencanaan diet terapeutik dan evaluasi respons pasien',
         'Instalasi Gizi',
         'Sertifikat kompetensi nutrisionis',
         'Supervisi untuk diet kompleks (renal, hepatik, metabolik)'),
        ('NUT-03', 'Nutrisi Parenteral & Enteral',
         'Perencanaan dan monitoring nutrisi parenteral dan enteral',
         'Instalasi Gizi / rawat inap',
         'Sertifikat kompetensi nutrisionis; pelatihan dukungan nutrisi',
         'Supervisi wajib — koordinasi dengan tim medis'),
    ],
    'Dietisien': [
        ('DIE-01', 'Asesmen & Konseling Gizi',
         'Asesmen gizi individu dan konseling diet pasien',
         'Instalasi Gizi',
         'Sertifikat kompetensi dietisien; STR aktif',
         'Tidak memerlukan supervisi khusus'),
        ('DIE-02', 'Manajemen Menu & Produksi Makanan',
         'Perencanaan menu, pengendalian produksi, dan food safety',
         'Instalasi Gizi — dapur',
         'Sertifikat kompetensi dietisien',
         'Verifikasi bersama kepala instalasi gizi'),
    ],
    'Perekam Medis': [
        ('RM-01', 'Pendaftaran & Rekam Medis',
         'Pendaftaran pasien, pembuatan nomor rekam medis, dan assembly',
         'Instalasi Rekam Medis',
         'Sertifikat kompetensi perekam medis',
         'Tidak memerlukan supervisi khusus'),
        ('RM-02', 'Coding & Klasifikasi Penyakit',
         'Pengkodean diagnosis (ICD-10) dan prosedur (ICD-9-CM)',
         'Instalasi Rekam Medis',
         'Sertifikat kompetensi perekam medis; pelatihan coding',
         'Supervisi untuk kasus kompleks dan audit'),
        ('RM-03', 'Analisis Indikator Mutu Rekam Medis',
         'Analisis kelengkapan, ketepatan, dan ketepatan waktu dokumentasi',
         'Instalasi Rekam Medis',
         'Sertifikat kompetensi perekam medis',
         'Supervisi kepala instalasi rekam medis'),
    ],
    'Elektromedis': [
        ('ELM-01', 'Perawatan Alat Kesehatan Elektromedis',
         'Perawatan preventif dan korektif alat elektromedis',
         'Instalasi IPSRS',
         'Sertifikat kompetensi elektromedis',
         'Supervisi untuk alat berisiko tinggi'),
        ('ELM-02', 'Kalibrasi & Uji Fungsional',
         'Kalibrasi dan uji fungsional alat elektromedis sesuai standar',
         'Instalasi IPSRS',
         'Sertifikat kompetensi elektromedis; pelatihan kalibrasi',
         'Verifikasi bersama kepala instalasi IPSRS'),
    ],
    'Sanitarian': [
        ('SAN-01', 'Pengendalian Infeksi Rumah Sakit',
         'Surveilans infeksi, audit PPI, dan investigasi kluster',
         'Komite PPI',
         'Sertifikat kompetensi sanitarian',
         'Supervisi ketua komite PPI'),
        ('SAN-02', 'Pengelolaan Limbah & Sanitasi Lingkungan',
         'Pengelolaan limbah rumah sakit dan sanitasi lingkungan',
         'Instalasi Sanitasi',
         'Sertifikat kompetensi sanitarian',
         'Tidak memerlukan supervisi khusus'),
    ],
    'Tenaga Teknik Kefarmasian': [
        ('TTK-01', 'Pengelolaan Stok & Logistik Obat',
         'Penerimaan, penyimpanan, dan distribusi obat',
         'Instalasi Farmasi',
         'Sertifikat kompetensi TTK',
         'Supervisi apoteker penanggung jawab'),
        ('TTK-02', 'Pengelolaan Obat Narkotika & Psikotropika',
         'Pencatatan, penyimpanan, dan pelaporan obat terkendali',
         'Instalasi Farmasi',
         'Sertifikat kompetensi TTK; pelatihan SIPA',
         'Supervisi wajib — verifikasi ganda'),
    ],
    'Terapis Wicara': [
        ('TW-01', 'Asesmen & Terapi Gangguan Wicara',
         'Asesmen dan terapi gangguan artikulasi, fluensi, dan suara',
         'Instalasi Terapi Wicara',
         'Sertifikat kompetensi terapis wicara; STR aktif',
         'Supervisi untuk kasus kompleks'),
        ('TW-02', 'Asesmen & Terapi Gangguan Bahasa',
         'Asesmen dan terapi gangguan bahasa reseptif dan ekspresif',
         'Instalasi Terapi Wicara',
         'Sertifikat kompetensi terapis wicara',
         'Supervisi untuk kasus kompleks'),
    ],
    'Ortotik Prostetik': [
        ('OP-01', 'Pembuatan & Penyesuaian Alat Bantu Ortopetik',
         'Perancangan, pembuatan, dan penyesuaian alat bantu ortopetik',
         'Instalasi Ortotik Prostetik',
         'Sertifikat kompetensi ortotik prostetik',
         'Supervisi untuk kasus kompleks'),
        ('OP-02', 'Pembuatan & Penyesuaian Alat Bantu Prostetik',
         'Perancangan, pembuatan, dan penyesuaian anggota tubuh tiruan',
         'Instalasi Ortotik Prostetik',
         'Sertifikat kompetensi ortotik prostetik',
         'Supervisi wajib — koordinasi dengan tim rehabilitasi'),
    ],
    'Penata Anestesi': [
        ('PA-01', 'Asistensi Anestesi Umum',
         'Persiapan dan asistensi tindakan anestesi umum',
         'Instalasi Kamar Operasi',
         'Sertifikat kompetensi penata anestesi; STR aktif',
         'Supervisi wajib — di bawah dokter anestesi'),
        ('PA-02', 'Pemantauan Pasien Intraoperatif',
         'Pemantauan tanda vital dan kondisi pasien selama operasi',
         'Instalasi Kamar Operasi',
         'Sertifikat kompetensi penata anestesi',
         'Supervisi wajib — di bawah dokter anestesi'),
        ('PA-03', 'Pemulihan Pascaanestesi',
         'Perawatan pasien di ruang pemulihan pascaanestesi',
         'Ruang Pemulihan (RR)',
         'Sertifikat kompetensi penata anestesi',
         'Supervisi wajib — di bawah dokter anestesi'),
    ],
    'Terapis Gigi & Mulut': [
        ('TG-01', 'Perawatan Gigi Dasar',
         'Penambalan, pencabutan sederhana, dan pembersihan karang gigi',
         'Instalasi Kedokteran Gigi',
         'Sertifikat kompetensi terapis gigi; STR aktif',
         'Supervisi dokter gigi untuk tindakan bedah'),
        ('TG-02', 'Pencegahan Penyakit Gigi & Mulut',
         'Edukasi kesehatan gigi, aplikasi fluoride, dan sealant',
         'Instalasi Kedokteran Gigi',
         'Sertifikat kompetensi terapis gigi',
         'Tidak memerlukan supervisi khusus'),
    ],
    'Perawat Gigi & Mulut': [
        ('PG-01', 'Asistensi Tindakan Kedokteran Gigi',
         'Asistensi dokter gigi dalam berbagai tindakan',
         'Instalasi Kedokteran Gigi',
         'Sertifikat kompetensi perawat gigi; STR aktif',
         'Supervisi dokter gigi'),
        ('PG-02', 'Sterilisasi Instrumen Kedokteran Gigi',
         'Pengelolaan sterilisasi dan desinfeksi instrumen',
         'Instalasi Kedokteran Gigi',
         'Sertifikat kompetensi perawat gigi',
         'Tidak memerlukan supervisi khusus'),
    ],
    'Teknis Bank Darah': [
        ('TBD-01', 'Pemeriksaan Golongan Darah & Kompatibilitas',
         'Pemeriksaan ABO, Rhesus, dan uji kompatibilitas (crossmatch)',
         'Unit Transfusi Darah',
         'Sertifikat kompetensi teknis bank darah',
         'Supervisi wajib — verifikasi ganda sebelum transfusi'),
        ('TBD-02', 'Pengelolaan Komponen Darah',
         'Pemisahan, penyimpanan, dan distribusi komponen darah',
         'Unit Transfusi Darah',
         'Sertifikat kompetensi teknis bank darah',
         'Verifikasi bersama kepala UTD'),
    ],
    'Psikolog Klinis': [
        ('PSK-01', 'Asesmen Psikologis',
         'Asesmen psikologis menggunakan instrumen tervalidasi',
         'Instalasi Psikologi',
         'Sertifikat kompetensi psikolog klinis; STR aktif',
         'Tidak memerlukan supervisi khusus'),
        ('PSK-02', 'Intervensi & Psikoterapi',
         'Intervensi psikologis dan sesi psikoterapi individu/kelompok',
         'Instalasi Psikologi',
         'Sertifikat kompetensi psikolog klinis',
         'Supervisi untuk kasus risiko tinggi'),
    ],
}

# Profesi yang belum punya katalog spesifik — pakai katalog generik
KATALOG_GENERIK = [
    ('GEN-01', 'Pelaksanaan Tugas Sesuai Kompetensi',
     'Pelaksanaan tugas profesi sesuai lingkup kompetensi yang dimiliki',
     'Unit penempatan sesuai struktur organisasi RS',
     'Sertifikat kompetensi profesi; STR aktif',
     'Sesuai penetapan atasan langsung'),
]


class Command(BaseCommand):
    help = (
        'Seed master data Sub. Kredensial: group role, syarat dokumen per profesi, '
        'dan katalog kewenangan klinis. Idempoten — aman dijalankan berulang.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-update',
            action='store_true',
            help='Perbarui deskripsi/referensi master yang sudah ada.',
        )

    def handle(self, *args, **options):
        force = options['force_update']
        self._seed_groups()
        self._seed_requirements(force)
        self._seed_privileges(force)
        self.stdout.write(self.style.SUCCESS('Seed master kredensial selesai.'))

    def _seed_groups(self):
        for role, group_name in ROLE_GROUPS.items():
            _, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Group "{group_name}" dibuat'))

    def _seed_requirements(self, force):
        profesi_qs = Profesi.objects.all()
        total_created = 0
        total_skipped = 0

        for profesi in profesi_qs:
            syarat_list = list(SYARAT_UMUM)
            if profesi.nama in PROFESI_WAJIB_SIP:
                syarat_list.append(SYARAT_SIP)
            elif profesi.nama in PROFESI_TEKNIS:
                syarat_list.append(('sip', 'SIP (jika dipersyaratkan unit kerja)', False, 1825,
                                    'SOP Internal RS — SIP opsional untuk profesi teknis'))

            for kategori, nama, wajib, masa, referensi in syarat_list:
                _, created = CredentialRequirement.objects.get_or_create(
                    profesi=profesi,
                    kategori=kategori,
                    nama_syarat=nama,
                    versi_kebijakan='1.0',
                    defaults={
                        'wajib': wajib,
                        'masa_berlaku_hari': masa,
                        'referensi_regulasi': referensi,
                        'deskripsi': f'Syarat {nama} untuk profesi {profesi.nama}.',
                    },
                )
                if created:
                    total_created += 1
                else:
                    total_skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f'  Syarat dokumen: {total_created} dibuat, {total_skipped} sudah ada'
        ))

    def _seed_privileges(self, force):
        total_created = 0
        total_skipped = 0

        for profesi in Profesi.objects.all():
            katalog = KATALOG.get(profesi.nama, KATALOG_GENERIK)
            for kode, nama, deskripsi, lingkup, kompetensi, supervisi in katalog:
                _, created = ClinicalPrivilege.objects.get_or_create(
                    profesi=profesi,
                    kode=kode,
                    versi_kebijakan='1.0',
                    defaults={
                        'nama': nama,
                        'deskripsi': deskripsi,
                        'ruang_lingkup': lingkup,
                        'kompetensi_wajib': kompetensi,
                        'aturan_supervisi': supervisi,
                        'aktif': True,
                    },
                )
                if created:
                    total_created += 1
                else:
                    total_skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f'  Katalog kewenangan: {total_created} dibuat, {total_skipped} sudah ada'
        ))
        self.stdout.write(self.style.WARNING(
            '  PERHATIAN: Katalog kewenangan bersifat ACUAN AWAL. '
            'Administrator RS WAJIB meninjau dan menyesuaikan dengan SOP '
            'serta regulasi internal sebelum digunakan operasional.'
        ))
