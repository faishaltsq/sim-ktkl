"""Model inti Sub. Kredensial — requirement, application, document, verification.

Model domain lanjutan (asesmen, privilege, rekomendasi, SPK, monitoring, event)
ada di `kredensial_models.py` dan di-re-export di bawah file ini.
"""
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


# ==========================================
# MASTER: SYARAT DOKUMEN PER PROFESI
# ==========================================
class CredentialRequirement(models.Model):
    """Master syarat dokumen kredensial, configurable per profesi.

    Setiap baris = satu jenis dokumen yang disyaratkan untuk profesi tertentu,
    dengan aturan keharusan, kategori, dan referensi regulasi/SOP.
    """

    KATEGORI_CHOICES = [
        ('identitas', 'Dokumen Identitas'),
        ('kualifikasi', 'Kualifikasi Profesi'),
        ('pendidikan', 'Ijazah / Sertifikat Pendidikan'),
        ('kompetensi', 'Sertifikat Kompetensi'),
        ('str', 'STR (Surat Tanda Registrasi)'),
        ('sip', 'SIP (Surat Izin Praktik)'),
        ('pelatihan', 'Sertifikat Pelatihan'),
        ('pengalaman', 'Bukti Pengalaman Kerja'),
        ('portofolio', 'Portofolio'),
        ('spk_rkk', 'SPK / RKK Sebelumnya'),
        ('evaluasi', 'Dokumen Evaluasi Pendukung'),
        ('lainnya', 'Syarat Lain yang Ditentukan RS'),
    ]

    profesi = models.ForeignKey(
        'nakes.Profesi',
        on_delete=models.CASCADE,
        related_name='kredensial_requirements',
        verbose_name='Profesi',
    )
    kategori = models.CharField('Kategori Dokumen', max_length=20, choices=KATEGORI_CHOICES)
    nama_syarat = models.CharField('Nama Syarat', max_length=200)
    deskripsi = models.TextField('Deskripsi / Kriteria Verifikasi', blank=True)
    wajib = models.BooleanField('Wajib', default=True,
                                help_text='Centang jika dokumen ini wajib untuk menyelesaikan verifikasi.')
    berlaku_untuk = models.CharField(
        'Berlaku Untuk Jenis Pengajuan', max_length=200, blank=True,
        help_text='Kosongkan jika berlaku untuk semua jenis pengajuan. Pisahkan dengan koma.',
    )
    masa_berlaku_hari = models.PositiveIntegerField(
        'Masa Berlaku (hari)', null=True, blank=True,
        help_text='Kosongkan jika tidak ada aturan kedaluwarsa dokumen.',
    )
    referensi_regulasi = models.CharField('Referensi Regulasi / SOP', max_length=300, blank=True)
    versi_kebijakan = models.CharField('Versi Kebijakan', max_length=50, default='1.0')
    aktif = models.BooleanField('Aktif', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Syarat Kredensial'
        verbose_name_plural = 'Syarat Kredensial'
        ordering = ['profesi__nama', 'kategori', 'nama_syarat']
        unique_together = [('profesi', 'kategori', 'nama_syarat', 'versi_kebijakan')]

    def __str__(self):
        return f"{self.nama_syarat} ({self.profesi.nama})"

    @property
    def kategori_display(self):
        return self.get_kategori_display()


# ==========================================
# MASTER: PENGAJUAN KREDENSIAL
# ==========================================
class CredentialApplication(models.Model):
    """Master pengajuan kredensial — satu baris per siklus kredensial."""

    JENIS_CHOICES = [
        ('awal', 'Kredensial Awal'),
        ('berkala', 'Rekredensial Berkala'),
        ('tambahan', 'Penambahan Kewenangan'),
        ('perubahan', 'Perubahan / Pembatasan Kewenangan'),
        ('khusus', 'Rekredensial Khusus'),
    ]

    STATE_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Diajukan'),
        ('UNDER_VERIFICATION', 'Dalam Verifikasi'),
        ('REVISION_REQUIRED', 'Perlu Perbaikan'),
        ('RESUBMITTED', 'Diajukan Ulang'),
        ('VERIFIED', 'Terverifikasi'),
        ('UNDER_ASSESSMENT', 'Dalam Asesmen'),
        ('ASSESSMENT_COMPLETED', 'Asesmen Selesai'),
        ('RECOMMENDATION_REVIEW', 'Review Rekomendasi'),
        ('RECOMMENDED', 'Direkomendasikan'),
        ('PENDING_FINAL_DECISION', 'Menunggu Keputusan Final'),
        ('RETURNED_FOR_REVISION', 'Dikembalikan untuk Revisi'),
        ('REJECTED', 'Ditolak'),
        ('APPROVED', 'Disetujui'),
        ('DOCUMENT_ISSUED', 'Dokumen Diterbitkan'),
        ('CLOSED', 'Selesai'),
    ]

    nomor_pengajuan = models.CharField('Nomor Pengajuan', max_length=50, unique=True)
    nakes = models.ForeignKey(
        'nakes.Nakes',
        on_delete=models.PROTECT,
        related_name='kredensial_applications',
        verbose_name='Tenaga Kesehatan',
    )
    # Snapshot profesi & unit — akurasi historis jika data Nakes berubah
    profesi_snapshot = models.ForeignKey(
        'nakes.Profesi',
        on_delete=models.PROTECT,
        related_name='+',
        verbose_name='Profesi (snapshot)',
    )
    unit_kerja_snapshot = models.CharField('Unit Kerja (snapshot)', max_length=200)
    jenis = models.CharField('Jenis Pengajuan', max_length=20, choices=JENIS_CHOICES)
    tanggal_pengajuan = models.DateField('Tanggal Pengajuan', default=timezone.now)
    diajukan_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='kredensial_diajukan',
        verbose_name='Diajukan Oleh',
    )
    verifikator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='kredensial_diverifikasi',
        verbose_name='Verifikator Ditugaskan',
    )
    workflow_state = models.CharField(
        'Status Workflow', max_length=30, choices=STATE_CHOICES, default='DRAFT',
    )
    status = models.CharField(
        'Status Ringkas', max_length=20, default='Aktif',
        help_text='Aktif / Selesai / Ditolak / Dibatalkan',
    )
    lingkup_kewenangan_diminta = models.TextField(
        'Lingkup Kewenangan yang Diminta', blank=True,
        help_text='Deskripsi umum kewenangan klinis/teknis yang diminta.',
    )
    catatan = models.TextField('Catatan', blank=True)
    versi_kebijakan = models.CharField(
        'Versi Kebijakan yang Berlaku', max_length=50, default='1.0',
        help_text='Versi requirement/policy yang dipakai untuk siklus ini.',
    )
    previous_cycle = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='next_cycles',
        verbose_name='Siklus Sebelumnya',
        help_text='Diisi untuk rekredensial, referensi ke pengajuan sebelumnya.',
    )
    # Timestamps penting
    submitted_at = models.DateTimeField('Waktu Submit', null=True, blank=True)
    verified_at = models.DateTimeField('Waktu Verifikasi Selesai', null=True, blank=True)
    assessment_completed_at = models.DateTimeField('Waktu Asesmen Selesai', null=True, blank=True)
    recommended_at = models.DateTimeField('Waktu Rekomendasi', null=True, blank=True)
    decision_at = models.DateTimeField('Waktu Keputusan Final', null=True, blank=True)
    closed_at = models.DateTimeField('Waktu Penutupan', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Pengajuan Kredensial'
        verbose_name_plural = 'Pengajuan Kredensial'
        ordering = ['-tanggal_pengajuan', '-created_at']
        indexes = [
            models.Index(fields=['workflow_state', 'status']),
            models.Index(fields=['nakes', 'jenis']),
        ]

    def __str__(self):
        return f"{self.nomor_pengajuan} — {self.nakes.nama} ({self.get_jenis_display()})"

    @property
    def is_active(self):
        return self.status == 'Aktif'

    @property
    def state_display(self):
        return self.get_workflow_state_display()

    def clean(self):
        if self.pk and self.previous_cycle_id == self.pk:
            raise ValidationError({'previous_cycle': 'Siklus sebelumnya tidak boleh merujuk ke dirinya sendiri.'})


# ==========================================
# DOKUMEN PENGAJUAN + VERSI
# ==========================================
class CredentialDocument(models.Model):
    """Dokumen yang diunggah untuk sebuah pengajuan.

    Setiap unggahan baru dari requirement yang sama membuat baris baru
    (versioning) — verifikasi lama tidak pernah ditimpa.
    """

    application = models.ForeignKey(
        CredentialApplication,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name='Pengajuan',
    )
    requirement = models.ForeignKey(
        CredentialRequirement,
        on_delete=models.PROTECT,
        related_name='submitted_documents',
        verbose_name='Syarat Dokumen',
    )
    nama_file = models.CharField('Nama File', max_length=200)
    file = models.FileField('Berkas', upload_to='kredensial/%Y/%m/')
    versi = models.PositiveIntegerField('Versi', default=1)
    tanggal_berlaku = models.DateField('Tanggal Berlaku Dokumen', null=True, blank=True)
    tanggal_kedaluwarsa = models.DateField('Tanggal Kedaluwarsa Dokumen', null=True, blank=True)
    nomor_dokumen = models.CharField('Nomor Dokumen', max_length=100, blank=True)
    catatan_pengunggah = models.TextField('Catatan Pengunggah', blank=True)
    is_versi_aktif = models.BooleanField('Versi Aktif', default=True,
                                         help_text='Hanya satu versi aktif per requirement per pengajuan.')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='kredensial_dokumen_upload',
    )

    class Meta:
        verbose_name = 'Dokumen Kredensial'
        verbose_name_plural = 'Dokumen Kredensial'
        ordering = ['requirement', '-versi']
        indexes = [
            models.Index(fields=['application', 'requirement', 'is_versi_aktif']),
        ]

    def __str__(self):
        return f"{self.requirement.nama_syarat} v{self.versi} — {self.application.nomor_pengajuan}"

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
            return f"{size / (1024 * 1024):.1f} MB"
        except (FileNotFoundError, ValueError):
            return '-'

    @property
    def is_expired(self):
        return bool(self.tanggal_kedaluwarsa and self.tanggal_kedaluwarsa < timezone.now().date())


# ==========================================
# HASIL VERIFIKASI DOKUMEN (IMMUTABLE HISTORY)
# ==========================================
class DocumentVerification(models.Model):
    """Hasil verifikasi satu dokumen oleh verifikator.

    Setiap pemeriksaan menghasilkan baris baru — riwayat verifikasi tidak
    pernah ditimpa. Baris terbaru = status efektif dokumen.
    """

    HASIL_CHOICES = [
        ('belum', 'Belum Diperiksa'),
        ('valid', 'Valid'),
        ('perbaikan', 'Perlu Perbaikan'),
        ('ditolak', 'Ditolak'),
        ('tidak_berlaku', 'Tidak Berlaku / Tidak Dipersyaratkan'),
    ]

    document = models.ForeignKey(
        CredentialDocument,
        on_delete=models.CASCADE,
        related_name='verifications',
        verbose_name='Dokumen',
    )
    hasil = models.CharField('Hasil Verifikasi', max_length=20, choices=HASIL_CHOICES, default='belum')
    catatan = models.TextField('Catatan Verifikator', blank=True)
    koreksi_diperlukan = models.TextField('Koreksi yang Diperlukan', blank=True)
    tanggal_verifikasi = models.DateTimeField('Tanggal Verifikasi', default=timezone.now)
    diverifikasi_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='kredensial_verifikasi',
        verbose_name='Diverifikasi Oleh',
    )

    class Meta:
        verbose_name = 'Verifikasi Dokumen'
        verbose_name_plural = 'Verifikasi Dokumen'
        ordering = ['-tanggal_verifikasi']
        indexes = [
            models.Index(fields=['document', '-tanggal_verifikasi']),
        ]

    def __str__(self):
        return f"{self.document} — {self.get_hasil_display()}"

    @property
    def hasil_color(self):
        return {
            'belum': 'secondary',
            'valid': 'success',
            'perbaikan': 'warning',
            'ditolak': 'danger',
            'tidak_berlaku': 'muted',
        }.get(self.hasil, 'secondary')


# Re-export model domain lanjutan agar app registry Django tetap happy
from .kredensial_models import (  # noqa: E402,F401
    CompetencyAssessment,
    AssessmentResult,
    ClinicalPrivilege,
    RequestedPrivilege,
    PrivilegeRecommendation,
    CredentialReview,
    ClinicalAppointment,
    GrantedPrivilege,
    CredentialFollowUp,
    CredentialEvent,
)
