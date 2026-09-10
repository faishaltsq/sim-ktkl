from django.contrib import admin
from .models import (
    Nakes, DokumenNakes, AuditLog, DokumenUmum, Profesi,
    EvaluasiOPPE, EvaluasiMutuKlinis,
    PelanggaranEtik, SidangEtik, EvaluasiKinerjaEtik,
)


@admin.register(Profesi)
class ProfesiAdmin(admin.ModelAdmin):
    list_display = ['nama', 'nakes_count']
    search_fields = ['nama']

    def nakes_count(self, obj):
        return obj.nakes_list.count()
    nakes_count.short_description = 'Jumlah Nakes'


@admin.register(Nakes)
class NakesAdmin(admin.ModelAdmin):
    list_display = ['nama', 'profesi', 'unit_kerja', 'no_str', 'masa_berlaku_str', 'no_sip', 'masa_berlaku_sip', 'status_kredensial']
    list_filter = ['profesi', 'status_kredensial', 'kewenangan_klinis']
    search_fields = ['nama', 'no_str', 'no_sip']


@admin.register(DokumenNakes)
class DokumenNakesAdmin(admin.ModelAdmin):
    list_display = ['nakes', 'jenis', 'nama_file', 'uploaded_at', 'uploaded_by']
    list_filter = ['jenis']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'aksi', 'model_name', 'object_repr']
    list_filter = ['aksi', 'model_name']
    readonly_fields = ['user', 'aksi', 'model_name', 'object_id', 'object_repr', 'detail', 'timestamp']


@admin.register(DokumenUmum)
class DokumenUmumAdmin(admin.ModelAdmin):
    list_display = ['judul', 'kategori', 'uploaded_at', 'uploaded_by']
    list_filter = ['kategori']
    search_fields = ['judul', 'deskripsi']


@admin.register(EvaluasiOPPE)
class EvaluasiOPPEAdmin(admin.ModelAdmin):
    list_display = ['nakes', 'tahun', 'tanggal_evaluasi', 'total_nilai', 'poin_penilaian', 'grade']
    list_filter = ['grade', 'tahun']
    search_fields = ['nakes__nama']
    readonly_fields = ['total_nilai', 'poin_penilaian', 'grade']


@admin.register(EvaluasiMutuKlinis)
class EvaluasiMutuKlinisAdmin(admin.ModelAdmin):
    list_display = ['nama_indikator', 'unit_kerja', 'periode_bulan', 'periode_tahun', 'standar_target', 'capaian']
    list_filter = ['periode_tahun', 'periode_bulan', 'unit_kerja']
    search_fields = ['nama_indikator', 'unit_kerja']


@admin.register(PelanggaranEtik)
class PelanggaranEtikAdmin(admin.ModelAdmin):
    list_display = ['nakes', 'tanggal_kejadian', 'kategori', 'status', 'pelapor']
    list_filter = ['kategori', 'status', 'tanggal_kejadian']
    search_fields = ['nakes__nama', 'deskripsi', 'pelapor']


@admin.register(SidangEtik)
class SidangEtikAdmin(admin.ModelAdmin):
    list_display = ['judul_sidang', 'nakes', 'tanggal_sidang', 'waktu_mulai', 'status', 'tempat']
    list_filter = ['status', 'tanggal_sidang']
    search_fields = ['judul_sidang', 'nakes__nama', 'hasil_investigasi', 'rekomendasi_pembinaan']


@admin.register(EvaluasiKinerjaEtik)
class EvaluasiKinerjaEtikAdmin(admin.ModelAdmin):
    list_display = ['nakes', 'periode_tahun', 'periode_semester', 'predikat', 'status_kepatuhan', 'evaluator']
    list_filter = ['periode_tahun', 'periode_semester', 'predikat', 'status_kepatuhan']
    search_fields = ['nakes__nama', 'catatan_evaluasi', 'evaluator']
