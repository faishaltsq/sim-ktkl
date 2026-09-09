from datetime import date as date_type
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class Profesi(models.Model):
    nama = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = 'Profesi'
        verbose_name_plural = 'Profesi'
        ordering = ['nama']

    def __str__(self):
        return self.nama


class Nakes(models.Model):
    STATUS_KREDENSIAL_CHOICES = [
        ('Belum Pengajuan', 'Belum Pengajuan'),
        ('Dalam Proses', 'Dalam Proses'),
        ('Selesai', 'Selesai'),
    ]

    KEWENANGAN_CHOICES = [
        ('Aktif', 'Aktif'),
        ('Evaluasi', 'Evaluasi'),
        ('Proses', 'Proses'),
        ('Tidak Aktif', 'Tidak Aktif'),
    ]

    nama = models.CharField(max_length=200)
    profesi = models.ForeignKey(Profesi, on_delete=models.PROTECT, related_name='nakes_list')
    unit_kerja = models.CharField(max_length=200)
    no_str = models.CharField('Nomor STR', max_length=50, unique=True)
    masa_berlaku_str = models.DateField('Masa Berlaku STR')
    no_sip = models.CharField('Nomor SIP', max_length=50, unique=True)
    masa_berlaku_sip = models.DateField('Masa Berlaku SIP')
    status_kredensial = models.CharField(max_length=20, choices=STATUS_KREDENSIAL_CHOICES, default='Belum Pengajuan')
    kewenangan_klinis = models.CharField(max_length=20, choices=KEWENANGAN_CHOICES, default='Proses')
    catatan = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='nakes_created',
    )

    class Meta:
        verbose_name = 'Tenaga Kesehatan'
        verbose_name_plural = 'Tenaga Kesehatan'
        ordering = ['nama']

    def __str__(self):
        return f"{self.nama} - {self.profesi}"

    @property
    def str_sisa_hari(self):
        from datetime import date
        return (self.masa_berlaku_str - date.today()).days

    @property
    def sip_sisa_hari(self):
        from datetime import date
        return (self.masa_berlaku_sip - date.today()).days


class DokumenNakes(models.Model):
    JENIS_CHOICES = [
        ('STR', 'Surat Tanda Registrasi'),
        ('SIP', 'Surat Izin Praktik'),
        ('Sertifikat', 'Sertifikat Kredensial'),
        ('Lainnya', 'Lainnya'),
    ]

    nakes = models.ForeignKey(Nakes, on_delete=models.CASCADE, related_name='dokumen')
    jenis = models.CharField(max_length=20, choices=JENIS_CHOICES)
    nama_file = models.CharField(max_length=200)
    file = models.FileField(upload_to='dokumen/%Y/%m/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )

    class Meta:
        verbose_name = 'Dokumen'
        verbose_name_plural = 'Dokumen'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.jenis} - {self.nakes.nama}"

    @property
    def file_extension(self):
        import os
        return os.path.splitext(self.file.name)[1].lower() if self.file else ''

    @property
    def file_size_display(self):
        try:
            size = self.file.size
            if size < 1024:
                return f"{size} B"
            elif size < 1024 * 1024:
                return f"{size / 1024:.1f} KB"
            else:
                return f"{size / (1024 * 1024):.1f} MB"
        except (FileNotFoundError, ValueError):
            return '-'


class AuditLog(models.Model):
    AKSI_CHOICES = [
        ('CREATE', 'Tambah'),
        ('UPDATE', 'Ubah'),
        ('DELETE', 'Hapus'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    aksi = models.CharField(max_length=10, choices=AKSI_CHOICES)
    model_name = models.CharField(max_length=50)
    object_id = models.IntegerField(null=True)
    object_repr = models.CharField(max_length=200)
    detail = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Log Audit'
        verbose_name_plural = 'Log Audit'

    def __str__(self):
        return f"{self.timestamp} - {self.user} - {self.aksi} {self.object_repr}"


class DokumenUmum(models.Model):
    KATEGORI_CHOICES = [
        ('SOP', 'SOP (Standar Operasional Prosedur)'),
        ('SK', 'Surat Keputusan'),
        ('Panduan', 'Panduan / Pedoman'),
        ('Formulir', 'Formulir'),
        ('Kebijakan', 'Kebijakan'),
        ('Lainnya', 'Lainnya'),
    ]

    judul = models.CharField(max_length=200)
    kategori = models.CharField(max_length=20, choices=KATEGORI_CHOICES)
    deskripsi = models.TextField(blank=True)
    file = models.FileField(upload_to='dokumen_umum/%Y/%m/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )

    class Meta:
        verbose_name = 'Dokumen Umum'
        verbose_name_plural = 'Dokumen Umum'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.judul} ({self.kategori})"

    @property
    def file_extension(self):
        import os
        return os.path.splitext(self.file.name)[1].lower() if self.file else ''

    @property
    def file_size_display(self):
        try:
            size = self.file.size
            if size < 1024:
                return f"{size} B"
            elif size < 1024 * 1024:
                return f"{size / 1024:.1f} KB"
            else:
                return f"{size / (1024 * 1024):.1f} MB"
        except (FileNotFoundError, ValueError):
            return '-'


def _skor_field():
    return models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )


class EvaluasiOPPE(models.Model):
    GRADE_CHOICES = [
        ('B', 'Baik'),
        ('C', 'Cukup'),
        ('K', 'Kurang'),
    ]

    INDIKATOR_LABELS = [
        ('perilaku', 'A. Perilaku', [
            'Komunikasi dengan pasien',
            'Komunikasi dengan keluarga pasien',
            'Komunikasi dengan sejawat',
            'Komunikasi dengan pimpinan',
            'Kemampuan memahami dan menghargai sejawat, tenaga medis, paramedis serta seluruh pegawai RS',
            'Keaktifan dalam menjalankan budaya 5R (Ringkas, Rapi, Resik, Rawat, Rajin)',
            'Ketepatan waktu dalam semua kegiatan RS serta komitmen terhadap pekerjaan dan peraturan',
        ]),
        ('profesional', 'B. Pengembangan Profesional', [
            'Komitmen mengembangkan profesionalitas secara berkelanjutan',
            'Komitmen mengembangkan praktik-praktik etika',
            'Pemahaman terhadap peraturan perundang-undangan tentang pelayanan kesehatan',
            'Kepatuhan terhadap kebijakan dan prosedur pelayanan rumah sakit',
        ]),
        ('kinerja', 'C. Kinerja Klinik', [
            'Memberikan asuhan pasien dengan profesional, santun dan islami',
            'Memberikan edukasi pada pasien',
            'Memahami dan menghargai hak pasien dan keluarga',
            'Kemampuan menjalankan tugas individu sesuai dengan kompetensi',
            'Kemampuan mengelola sejumlah tugas dalam satu pekerjaan',
            'Kemampuan merespon dan mengelola kejadian irregular dan masalah',
            'Kemampuan menyesuaikan diri dengan tanggung jawab dan harapan lingkungan',
            'Keterlibatan dalam peningkatan mutu dan keselamatan pasien',
            'Kepatuhan terhadap Standar Prosedur Operasional (SPO)',
        ]),
    ]

    nakes = models.ForeignKey(Nakes, on_delete=models.CASCADE, related_name='oppe_set', verbose_name='Tenaga Kesehatan')
    tahun = models.PositiveIntegerField('Tahun Evaluasi')
    tanggal_evaluasi = models.DateField('Tanggal Evaluasi')

    skor_perilaku_1 = _skor_field()
    skor_perilaku_2 = _skor_field()
    skor_perilaku_3 = _skor_field()
    skor_perilaku_4 = _skor_field()
    skor_perilaku_5 = _skor_field()
    skor_perilaku_6 = _skor_field()
    skor_perilaku_7 = _skor_field()
    skor_profesional_1 = _skor_field()
    skor_profesional_2 = _skor_field()
    skor_profesional_3 = _skor_field()
    skor_profesional_4 = _skor_field()
    skor_kinerja_1 = _skor_field()
    skor_kinerja_2 = _skor_field()
    skor_kinerja_3 = _skor_field()
    skor_kinerja_4 = _skor_field()
    skor_kinerja_5 = _skor_field()
    skor_kinerja_6 = _skor_field()
    skor_kinerja_7 = _skor_field()
    skor_kinerja_8 = _skor_field()
    skor_kinerja_9 = _skor_field()

    total_nilai = models.DecimalField('Total Nilai', max_digits=7, decimal_places=2, default=0, editable=False)
    poin_penilaian = models.DecimalField('Poin Penilaian', max_digits=5, decimal_places=2, default=0, editable=False)
    grade = models.CharField('Grade', max_length=1, choices=GRADE_CHOICES, default='K', editable=False)

    penilai_nama = models.CharField('Nama Penilai / Atasan Langsung', max_length=200, blank=True)
    penilai_nip = models.CharField('NIP Penilai', max_length=50, blank=True)
    mengetahui_nama = models.CharField('Nama Manajer / Ka. Instalasi', max_length=200, blank=True)
    mengetahui_nip = models.CharField('NIP Manajer / Ka. Instalasi', max_length=50, blank=True)
    pegawai_nip = models.CharField('NIP Pegawai yang Dinilai', max_length=50, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='oppe_created')

    class Meta:
        verbose_name = 'Evaluasi OPPE'
        verbose_name_plural = 'Evaluasi OPPE'
        ordering = ['-tahun', '-tanggal_evaluasi']
        unique_together = [('nakes', 'tahun')]

    def __str__(self):
        return f"OPPE {self.nakes.nama} - {self.tahun}"

    def get_all_scores(self):
        return [
            self.skor_perilaku_1, self.skor_perilaku_2, self.skor_perilaku_3,
            self.skor_perilaku_4, self.skor_perilaku_5, self.skor_perilaku_6,
            self.skor_perilaku_7, self.skor_profesional_1, self.skor_profesional_2,
            self.skor_profesional_3, self.skor_profesional_4, self.skor_kinerja_1,
            self.skor_kinerja_2, self.skor_kinerja_3, self.skor_kinerja_4,
            self.skor_kinerja_5, self.skor_kinerja_6, self.skor_kinerja_7,
            self.skor_kinerja_8, self.skor_kinerja_9,
        ]

    def compute_and_save_results(self):
        scores = self.get_all_scores()
        total = sum(scores)
        poin = total / 20
        if poin >= 80:
            g = 'B'
        elif poin > 60:
            g = 'C'
        else:
            g = 'K'
        self.total_nilai = total
        self.poin_penilaian = poin
        self.grade = g

    def save(self, *args, **kwargs):
        self.compute_and_save_results()
        super().save(*args, **kwargs)

    @property
    def grade_display(self):
        return {'B': 'Baik', 'C': 'Cukup', 'K': 'Kurang'}.get(self.grade, '-')

    @property
    def grade_color(self):
        return {'B': 'success', 'C': 'warning', 'K': 'danger'}.get(self.grade, 'secondary')


class EvaluasiMutuKlinis(models.Model):
    BULAN_CHOICES = [
        (1, 'Januari'), (2, 'Februari'), (3, 'Maret'), (4, 'April'),
        (5, 'Mei'), (6, 'Juni'), (7, 'Juli'), (8, 'Agustus'),
        (9, 'September'), (10, 'Oktober'), (11, 'November'), (12, 'Desember'),
    ]

    unit_kerja = models.CharField('Unit / Instalasi', max_length=200)
    periode_bulan = models.PositiveSmallIntegerField('Bulan', choices=BULAN_CHOICES)
    periode_tahun = models.PositiveIntegerField('Tahun')
    nama_indikator = models.CharField('Nama Indikator Mutu', max_length=300)
    standar_target = models.DecimalField('Standar Target (%)', max_digits=5, decimal_places=2,
                                         validators=[MinValueValidator(0), MaxValueValidator(100)])
    capaian = models.DecimalField('Capaian (%)', max_digits=5, decimal_places=2,
                                  validators=[MinValueValidator(0), MaxValueValidator(100)])
    analisis = models.TextField('Analisis', blank=True)
    rencana_tindak_lanjut = models.TextField('Rencana Tindak Lanjut (RTL)', blank=True)
    penanggung_jawab = models.CharField('Penanggung Jawab / PIC', max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='mutu_created')

    class Meta:
        verbose_name = 'Evaluasi Mutu Layanan Klinis'
        verbose_name_plural = 'Evaluasi Mutu Layanan Klinis'
        ordering = ['-periode_tahun', '-periode_bulan', 'unit_kerja']

    def __str__(self):
        return f"{self.nama_indikator} - {self.get_periode_bulan_display()} {self.periode_tahun}"

    @property
    def is_tercapai(self):
        return self.capaian >= self.standar_target

    @property
    def gap(self):
        return self.capaian - self.standar_target
