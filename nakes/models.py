from django.db import models
from django.conf import settings


class Nakes(models.Model):
    PROFESI_CHOICES = [
        ('ATLM', 'ATLM (Teknisi Laboratorium Medik)'),
        ('Radiografer', 'Radiografer'),
        ('Fisioterapis', 'Fisioterapis'),
        ('Nutrisionis', 'Nutrisionis'),
        ('Perekam Medis', 'Perekam Medis'),
        ('Apoteker', 'Apoteker'),
        ('Sanitarian', 'Sanitarian'),
        ('Lainnya', 'Lainnya'),
    ]

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
    profesi = models.CharField(max_length=50, choices=PROFESI_CHOICES)
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
