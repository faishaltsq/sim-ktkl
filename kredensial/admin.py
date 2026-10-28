from django.contrib import admin
from .models import (
    CredentialRequirement,
    CredentialApplication,
    CredentialDocument,
    DocumentVerification,
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


@admin.register(CredentialRequirement)
class CredentialRequirementAdmin(admin.ModelAdmin):
    list_display = ['nama_syarat', 'profesi', 'kategori', 'wajib', 'versi_kebijakan', 'aktif']
    list_filter = ['profesi', 'kategori', 'wajib', 'aktif']
    search_fields = ['nama_syarat', 'deskripsi']


@admin.register(CredentialApplication)
class CredentialApplicationAdmin(admin.ModelAdmin):
    list_display = ['nomor_pengajuan', 'nakes', 'jenis', 'workflow_state', 'status', 'tanggal_pengajuan']
    list_filter = ['jenis', 'workflow_state', 'status', 'profesi_snapshot']
    search_fields = ['nomor_pengajuan', 'nakes__nama']
    autocomplete_fields = ['nakes', 'profesi_snapshot']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(CredentialDocument)
class CredentialDocumentAdmin(admin.ModelAdmin):
    list_display = ['requirement', 'application', 'versi', 'is_versi_aktif', 'uploaded_at']
    list_filter = ['is_versi_aktif', 'requirement__profesi']
    search_fields = ['nama_file', 'application__nomor_pengajuan']


@admin.register(DocumentVerification)
class DocumentVerificationAdmin(admin.ModelAdmin):
    list_display = ['document', 'hasil', 'diverifikasi_oleh', 'tanggal_verifikasi']
    list_filter = ['hasil']
    search_fields = ['document__nama_file']


@admin.register(CompetencyAssessment)
class CompetencyAssessmentAdmin(admin.ModelAdmin):
    list_display = ['application', 'metode', 'asesor', 'tanggal_asesmen', 'status']
    list_filter = ['metode', 'status']
    search_fields = ['application__nomor_pengajuan']


@admin.register(AssessmentResult)
class AssessmentResultAdmin(admin.ModelAdmin):
    list_display = ['assessment', 'kompetensi', 'hasil', 'skor']
    list_filter = ['hasil']
    search_fields = ['kompetensi']


@admin.register(ClinicalPrivilege)
class ClinicalPrivilegeAdmin(admin.ModelAdmin):
    list_display = ['kode', 'nama', 'profesi', 'aktif', 'versi_kebijakan']
    list_filter = ['profesi', 'aktif']
    search_fields = ['kode', 'nama']


@admin.register(RequestedPrivilege)
class RequestedPrivilegeAdmin(admin.ModelAdmin):
    list_display = ['application', 'privilege']
    search_fields = ['application__nomor_pengajuan', 'privilege__nama']


@admin.register(PrivilegeRecommendation)
class PrivilegeRecommendationAdmin(admin.ModelAdmin):
    list_display = ['requested_privilege', 'keputusan', 'direkomendasikan_oleh', 'tanggal_rekomendasi']
    list_filter = ['keputusan']


@admin.register(CredentialReview)
class CredentialReviewAdmin(admin.ModelAdmin):
    list_display = ['application', 'reviewer', 'tanggal_review', 'disetujui']
    list_filter = ['disetujui']


@admin.register(ClinicalAppointment)
class ClinicalAppointmentAdmin(admin.ModelAdmin):
    list_display = ['nomor_spk', 'application', 'keputusan', 'tanggal_terbit',
                    'tanggal_akhir_berlaku', 'is_final']
    list_filter = ['keputusan', 'is_final']
    search_fields = ['nomor_spk', 'application__nakes__nama']
    readonly_fields = ['finalized_at']


@admin.register(GrantedPrivilege)
class GrantedPrivilegeAdmin(admin.ModelAdmin):
    list_display = ['privilege', 'appointment', 'status', 'tanggal_mulai', 'tanggal_akhir']
    list_filter = ['status']
    search_fields = ['privilege__nama', 'appointment__nomor_spk']


@admin.register(CredentialFollowUp)
class CredentialFollowUpAdmin(admin.ModelAdmin):
    list_display = ['application', 'temuan', 'penanggung_jawab', 'status', 'tanggal_target']
    list_filter = ['status']
    search_fields = ['temuan', 'application__nomor_pengajuan']


@admin.register(CredentialEvent)
class CredentialEventAdmin(admin.ModelAdmin):
    list_display = ['application', 'dari_state', 'ke_state', 'aksi', 'aktor', 'timestamp']
    list_filter = ['aksi', 'ke_state']
    search_fields = ['application__nomor_pengajuan', 'catatan']

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
