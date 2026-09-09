from django.contrib import admin
from .models import Nakes, DokumenNakes, AuditLog, DokumenUmum, Profesi


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
