"""Model domain Sub. Kredensial — asesmen, privilege, rekomendasi, SPK, monitoring, event."""
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


# ==========================================
# ASESMEN KOMPETENSI
# ==========================================
class CompetencyAssessment(models.Model):
    """Sesi asesmen kompetensi untuk sebuah pengajuan.

    Mendukung banyak metode dan banyak asesor per pengajuan.
    """

    METODE_CHOICES = [
        ('wawancara', 'Wawancara'),
        ('portofolio', 'Review Portofolio'),
        ('observasi', 'Observasi Praktik'),
        ('uji_keterampilan', 'Uji Keterampilan'),
        ('review_dokumen', 'Review Dokumen'),
        ('lainnya', 'Metode Lain yang Disetujui'),
    ]

    STATUS_CHOICES = [
        ('dijadwalkan', 'Dijadwalkan'),
        ('berlangsung', 'Berlangsung'),
        ('selesai', 'Selesai'),
        ('dibatalkan', 'Dibatalkan'),
    ]

    application = models.ForeignKey(
        'kredensial.CredentialApplication',
        on_delete=models.CASCADE,
        related_name='assessments',
        verbose_name='Pengajuan',
    )
    asesor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='kredensial_asesmen',
        verbose_name='Asesor',
    )
    nama_asesor_eksternal = models.CharField(
        'Nama Asesor Eksternal', max_length=200, blank=True,
        help_text='Diisi jika asesor bukan user sistem.',
    )
    metode = models.CharField('Metode Asesmen', max_length=20, choices=METODE_CHOICES)
    tanggal_asesmen = models.DateField('Tanggal Asesmen', default=timezone.now)
    ruang_lingkup = models.TextField(
        'Ruang Lingkup / Kompetensi yang Dinilai', blank=True,
        help_text='Kompetensi atau privilege spesifik yang dievaluasi dalam sesi ini.',
    )
    kriteria = models.TextField('Kriteria Penilaian', blank=True)
    temuan = models.TextField('Temuan', blank=True)
    bukti_pendukung = models.TextField('Bukti Pendukung', blank=True)
    rekomendasi_asesor = models.TextField('Rekomendasi Asesor', blank=True)
    status = models.CharField('Status Asesmen', max_length=20, choices=STATUS_CHOICES, default='dijadwalkan')
    catatan_reviewer = models.TextField('Catatan Reviewer', blank=True)
    pernyataan_benturan_kepentingan = models.BooleanField(
        'Pernyataan Bebas Benturan Kepentingan', default=False,
        help_text='Asesor menyatakan tidak memiliki benturan kepentingan.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Asesmen Kompetensi'
        verbose_name_plural = 'Asesmen Kompetensi'
        ordering = ['-tanggal_asesmen']

    def __str__(self):
        return f"{self.get_metode_display()} — {self.application.nomor_pengajuan}"

    @property
    def asesor_display(self):
        if self.asesor:
            return self.asesor.get_full_name() or self.asesor.username
        return self.nama_asesor_eksternal or '-'


class AssessmentResult(models.Model):
    """Hasil asesmen per kompetensi/privilege dalam satu sesi."""

    HASIL_CHOICES = [
        ('kompeten', 'Kompeten'),
        ('kompeten_supervisi', 'Kompeten dengan Supervisi'),
        ('perlu_pengembangan', 'Memerlukan Pengembangan'),
        ('belum_kompeten', 'Belum Kompeten'),
        ('tidak_dinilai', 'Tidak Dapat Dinilai'),
    ]

    assessment = models.ForeignKey(
        CompetencyAssessment,
        on_delete=models.CASCADE,
        related_name='results',
        verbose_name='Sesi Asesmen',
    )
    kompetensi = models.CharField('Kompetensi / Privilege', max_length=300)
    hasil = models.CharField('Hasil', max_length=25, choices=HASIL_CHOICES)
    skor = models.DecimalField(
        'Skor (jika dirubrikasi)', max_digits=5, decimal_places=2,
        null=True, blank=True,
        help_text='Isi hanya jika metode asesmen memakai rubrik skoring berversi.',
    )
    catatan = models.TextField('Catatan Hasil', blank=True)

    class Meta:
        verbose_name = 'Hasil Asesmen'
        verbose_name_plural = 'Hasil Asesmen'
        ordering = ['assessment', 'kompetensi']

    def __str__(self):
        return f"{self.kompetensi} — {self.get_hasil_display()}"

    @property
    def hasil_color(self):
        return {
            'kompeten': 'success',
            'kompeten_supervisi': 'info',
            'perlu_pengembangan': 'warning',
            'belum_kompeten': 'danger',
            'tidak_dinilai': 'secondary',
        }.get(self.hasil, 'secondary')


# ==========================================
# MASTER: KATALOG KEWENANGAN KLINIS
# ==========================================
class ClinicalPrivilege(models.Model):
    """Master katalog kewenangan klinis/teknis per profesi.

    Dikonfigurasi administrator dari standar profesi tervalidasi dan
    regulasi internal — tidak di-hardcode dari asumsi.
    """

    kode = models.CharField('Kode Privilege', max_length=50)
    profesi = models.ForeignKey(
        'nakes.Profesi',
        on_delete=models.CASCADE,
        related_name='kredensial_privileges',
        verbose_name='Profesi',
    )
    nama = models.CharField('Nama Kewenangan', max_length=300)
    deskripsi = models.TextField('Deskripsi', blank=True)
    ruang_lingkup = models.TextField('Ruang Lingkup Praktik', blank=True)
    kompetensi_wajib = models.TextField('Kompetensi yang Wajib Dimiliki', blank=True)
    bukti_wajib = models.TextField('Bukti Pendukung yang Wajib', blank=True)
    pembatasan = models.TextField('Pembatasan yang Berlaku', blank=True)
    aturan_supervisi = models.TextField('Aturan Supervisi', blank=True)
    aktif = models.BooleanField('Aktif', default=True)
    versi_kebijakan = models.CharField('Versi Kebijakan', max_length=50, default='1.0')

    class Meta:
        verbose_name = 'Kewenangan Klinis'
        verbose_name_plural = 'Kewenangan Klinis'
        ordering = ['profesi__nama', 'kode']
        unique_together = [('profesi', 'kode', 'versi_kebijakan')]

    def __str__(self):
        return f"{self.kode} — {self.nama} ({self.profesi.nama})"


class RequestedPrivilege(models.Model):
    """Privilege yang diminta pemohon dalam sebuah pengajuan."""

    application = models.ForeignKey(
        'kredensial.CredentialApplication',
        on_delete=models.CASCADE,
        related_name='requested_privileges',
        verbose_name='Pengajuan',
    )
    privilege = models.ForeignKey(
        ClinicalPrivilege,
        on_delete=models.PROTECT,
        related_name='requests',
        verbose_name='Katalog Kewenangan',
    )
    alasan = models.TextField('Alasan Permintaan', blank=True)
    catatan = models.TextField('Catatan', blank=True)

    class Meta:
        verbose_name = 'Kewenangan Diminta'
        verbose_name_plural = 'Kewenangan Diminta'
        ordering = ['application', 'privilege']
        unique_together = [('application', 'privilege')]

    def __str__(self):
        return f"{self.privilege.nama} — {self.application.nomor_pengajuan}"


# ==========================================
# REKOMENDASI RKK
# ==========================================
class PrivilegeRecommendation(models.Model):
    """Rekomendasi subkomite per privilege yang diminta.

    Rekomendasi BUKAN keputusan resmi — belum memberikan kewenangan aktif.
    """

    KEPUTUSAN_CHOICES = [
        ('direkomendasikan', 'Direkomendasikan'),
        ('supervisi', 'Direkomendasikan dengan Supervisi'),
        ('pembatasan', 'Direkomendasikan dengan Pembatasan'),
        ('tidak', 'Tidak Direkomendasikan'),
        ('ditunda', 'Ditunda'),
    ]

    requested_privilege = models.OneToOneField(
        RequestedPrivilege,
        on_delete=models.CASCADE,
        related_name='recommendation',
        verbose_name='Kewenangan Diminta',
    )
    keputusan = models.CharField('Rekomendasi', max_length=25, choices=KEPUTUSAN_CHOICES)
    pembatasan = models.TextField('Pembatasan yang Diusulkan', blank=True)
    kebutuhan_supervisi = models.TextField('Kebutuhan Supervisi', blank=True)
    kualifikasi_supervisor = models.CharField('Kualifikasi / Penugasan Supervisor', max_length=300, blank=True)
    dasar_pertimbangan = models.TextField('Dasar Pertimbangan', blank=True)
    direkomendasikan_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='kredensial_rekomendasi',
        verbose_name='Direkomendasikan Oleh',
    )
    tanggal_rekomendasi = models.DateTimeField('Tanggal Rekomendasi', default=timezone.now)

    class Meta:
        verbose_name = 'Rekomendasi Kewenangan'
        verbose_name_plural = 'Rekomendasi Kewenangan'
        ordering = ['requested_privilege']

    def __str__(self):
        return f"{self.requested_privilege.privilege.nama} — {self.get_keputusan_display()}"

    @property
    def keputusan_color(self):
        return {
            'direkomendasikan': 'success',
            'supervisi': 'info',
            'pembatasan': 'warning',
            'tidak': 'danger',
            'ditunda': 'secondary',
        }.get(self.keputusan, 'secondary')


class CredentialReview(models.Model):
    """Endorsement komite atas sekumpulan rekomendasi (jika diperlukan kebijakan RS)."""

    application = models.OneToOneField(
        'kredensial.CredentialApplication',
        on_delete=models.CASCADE,
        related_name='committee_review',
        verbose_name='Pengajuan',
    )
    tanggal_review = models.DateTimeField('Tanggal Review', default=timezone.now)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='kredensial_review',
        verbose_name='Reviewer',
    )
    catatan = models.TextField('Catatan Review', blank=True)
    disetujui = models.BooleanField('Disetujui untuk Keputusan Final', default=False)

    class Meta:
        verbose_name = 'Review Komite'
        verbose_name_plural = 'Review Komite'

    def __str__(self):
        return f"Review {self.application.nomor_pengajuan}"


# ==========================================
# PENETAPAN SPK / RKK
# ==========================================
class ClinicalAppointment(models.Model):
    """SPK — keputusan formal pejabat berwenang.

    Hanya pejabat dengan otoritas eksplisit yang dapat membuat record ini.
    Finalisasi bersifat transaksional dan tidak dapat diduplikasi.
    """

    KEPUTUSAN_CHOICES = [
        ('disetujui', 'Disetujui'),
        ('disetujui_pembatasan', 'Disetujui dengan Pembatasan'),
        ('kembalikan_revisi', 'Dikembalikan untuk Revisi'),
        ('ditolak', 'Ditolak'),
    ]

    application = models.OneToOneField(
        'kredensial.CredentialApplication',
        on_delete=models.PROTECT,
        related_name='appointment',
        verbose_name='Pengajuan',
    )
    nomor_spk = models.CharField('Nomor SPK', max_length=100, unique=True)
    tanggal_terbit = models.DateField('Tanggal Terbit')
    tanggal_mulai_berlaku = models.DateField('Tanggal Mulai Berlaku')
    tanggal_akhir_berlaku = models.DateField('Tanggal Akhir Berlaku')
    pejabat_berwenang = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='kredensial_keputusan',
        verbose_name='Pejabat Berwenang',
    )
    nama_pejabat_eksternal = models.CharField(
        'Nama Pejabat (eksternal)', max_length=200, blank=True,
        help_text='Diisi jika pejabat penandatangan bukan user sistem.',
    )
    tanggal_keputusan = models.DateTimeField('Tanggal Keputusan', default=timezone.now)
    keputusan = models.CharField('Keputusan', max_length=25, choices=KEPUTUSAN_CHOICES)
    lokasi_penugasan = models.CharField('Lokasi Penugasan', max_length=300, blank=True)
    tanggal_review = models.DateField('Tanggal Review Berikutnya', null=True, blank=True)
    target_rekredensial = models.DateField('Target Rekredensial', null=True, blank=True)
    catatan = models.TextField('Catatan Keputusan', blank=True)
    # Dokumen resmi yang diunggah (tertandu basah) + metadata
    dokumen_spk = models.FileField('Dokumen SPK (PDF)', upload_to='kredensial/spk/%Y/', blank=True)
    lampiran_rkk = models.FileField('Lampiran RKK', upload_to='kredensial/rkk/%Y/', blank=True)
    is_final = models.BooleanField('Final / Terbit', default=False,
                                   help_text='True setelah keputusan difinalisasi, tidak bisa diubah tanpa proses amendment.')
    finalized_at = models.DateTimeField('Waktu Finalisasi', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'SPK / Penetapan Kewenangan'
        verbose_name_plural = 'SPK / Penetapan Kewenangan'
        ordering = ['-tanggal_terbit']

    def __str__(self):
        return f"SPK {self.nomor_spk} — {self.application.nakes.nama}"

    def clean(self):
        if self.tanggal_mulai_berlaku and self.tanggal_akhir_berlaku:
            if self.tanggal_akhir_berlaku < self.tanggal_mulai_berlaku:
                raise ValidationError({
                    'tanggal_akhir_berlaku': 'Tanggal akhir berlaku tidak boleh sebelum tanggal mulai berlaku.',
                })

    @property
    def is_expired(self):
        return bool(self.tanggal_akhir_berlaku and self.tanggal_akhir_berlaku < timezone.now().date())

    @property
    def sisa_hari(self):
        if not self.tanggal_akhir_berlaku:
            return None
        return (self.tanggal_akhir_berlaku - timezone.now().date()).days


class GrantedPrivilege(models.Model):
    """Snapshot privilege efektif hasil keputusan final.

    Bisa berbeda dari rekomendasi — keputusan final yang berlaku.
    """

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Aktif'),
        ('suspended', 'Ditangguhkan'),
        ('expired', 'Kedaluwarsa'),
        ('revoked', 'Dicabut'),
        ('superseded', 'Digantikan'),
    ]

    appointment = models.ForeignKey(
        ClinicalAppointment,
        on_delete=models.PROTECT,
        related_name='granted_privileges',
        verbose_name='SPK',
    )
    privilege = models.ForeignKey(
        ClinicalPrivilege,
        on_delete=models.PROTECT,
        related_name='grants',
        verbose_name='Katalog Kewenangan',
    )
    redaksi_final = models.TextField('Redaksi Final Kewenangan',
                                     help_text='Teks kewenangan sebagaimana ditetapkan pejabat berwenang.')
    tanggal_mulai = models.DateField('Tanggal Mulai')
    tanggal_akhir = models.DateField('Tanggal Akhir', null=True, blank=True)
    pembatasan = models.TextField('Pembatasan', blank=True)
    kebutuhan_supervisi = models.TextField('Kebutuhan Supervisi', blank=True)
    status = models.CharField('Status Efektif', max_length=20, choices=STATUS_CHOICES, default='pending')
    catatan_perubahan = models.TextField('Catatan Perubahan Status', blank=True)

    class Meta:
        verbose_name = 'Kewenangan Diberikan'
        verbose_name_plural = 'Kewenangan Diberikan'
        ordering = ['appointment', 'privilege']
        unique_together = [('appointment', 'privilege')]

    def __str__(self):
        return f"{self.privilege.nama} — {self.get_status_display()}"

    @property
    def status_color(self):
        return {
            'pending': 'secondary',
            'active': 'success',
            'suspended': 'warning',
            'expired': 'muted',
            'revoked': 'danger',
            'superseded': 'info',
        }.get(self.status, 'secondary')


# ==========================================
# MONITORING & FOLLOW-UP
# ==========================================
class CredentialFollowUp(models.Model):
    """Temuan monitoring dan tindak lanjut korektif."""

    STATUS_CHOICES = [
        ('belum', 'Belum Dimulai'),
        ('proses', 'Dalam Proses'),
        ('menunggu', 'Menunggu Verifikasi'),
        ('selesai', 'Selesai'),
        ('dibatalkan', 'Dibatalkan'),
    ]

    application = models.ForeignKey(
        'kredensial.CredentialApplication',
        on_delete=models.CASCADE,
        related_name='follow_ups',
        verbose_name='Pengajuan',
    )
    oppe_terkait = models.ForeignKey(
        'nakes.EvaluasiOPPE',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='kredensial_follow_ups',
        verbose_name='Evaluasi OPPE Terkait',
    )
    temuan = models.TextField('Temuan')
    rekomendasi_tindakan = models.TextField('Rekomendasi Tindakan', blank=True)
    penanggung_jawab = models.CharField('Penanggung Jawab', max_length=200, blank=True)
    tanggal_target = models.DateField('Tanggal Target', null=True, blank=True)
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='belum')
    bukti_penyelesaian = models.TextField('Bukti Penyelesaian', blank=True)
    tanggal_selesai = models.DateField('Tanggal Selesai', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Tindak Lanjut Kredensial'
        verbose_name_plural = 'Tindak Lanjut Kredensial'
        ordering = ['-created_at']

    def __str__(self):
        return f"FollowUp {self.application.nomor_pengajuan} — {self.get_status_display()}"

    @property
    def is_overdue(self):
        return bool(
            self.tanggal_target
            and self.status not in ('selesai', 'dibatalkan')
            and self.tanggal_target < timezone.now().date()
        )


# ==========================================
# IMMUTABLE EVENT HISTORY
# ==========================================
class CredentialEvent(models.Model):
    """Riwayat transisi workflow — append-only, tidak pernah diubah/dihapus."""

    application = models.ForeignKey(
        'kredensial.CredentialApplication',
        on_delete=models.CASCADE,
        related_name='events',
        verbose_name='Pengajuan',
    )
    dari_state = models.CharField('Dari Status', max_length=30, blank=True)
    ke_state = models.CharField('Ke Status', max_length=30)
    aksi = models.CharField('Aksi', max_length=100,
                            help_text='Contoh: submit, verifikasi, asesmen, rekomendasi, keputusan, terbit, tutup.')
    aktor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='kredensial_event',
        verbose_name='Aktor',
    )
    catatan = models.TextField('Catatan', blank=True)
    timestamp = models.DateTimeField('Waktu', default=timezone.now)

    class Meta:
        verbose_name = 'Event Kredensial'
        verbose_name_plural = 'Event Kredensial'
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['application', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} {self.dari_state or '—'} → {self.ke_state}"

    def save(self, *args, **kwargs):
        # Append-only: blok update record yang sudah ada
        if self.pk:
            raise ValidationError('CredentialEvent bersifat append-only dan tidak dapat diubah.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('CredentialEvent bersifat append-only dan tidak dapat dihapus.')
