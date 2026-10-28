"""Form Sub. Kredensial — pengajuan, dokumen, verifikasi."""
from django import forms
from .models import (
    CredentialApplication,
    CredentialDocument,
    DocumentVerification,
    CredentialRequirement,
    CompetencyAssessment,
    AssessmentResult,
    ClinicalPrivilege,
    RequestedPrivilege,
    PrivilegeRecommendation,
    CredentialReview,
    ClinicalAppointment,
    CredentialFollowUp,
)
from nakes.models import EvaluasiOPPE


class CredentialApplicationForm(forms.ModelForm):
    class Meta:
        model = CredentialApplication
        fields = [
            'nakes', 'jenis', 'tanggal_pengajuan', 'verifikator',
            'lingkup_kewenangan_diminta', 'catatan', 'previous_cycle',
        ]
        widgets = {
            'tanggal_pengajuan': forms.DateInput(attrs={'type': 'date'}),
            'lingkup_kewenangan_diminta': forms.Textarea(attrs={'rows': 3}),
            'catatan': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Snapshot profesi & unit diambil dari Nakes saat save (di view)
        self.fields['previous_cycle'].queryset = CredentialApplication.objects.filter(
            status__in=['Aktif', 'Selesai'],
        ).exclude(pk=self.instance.pk)
        self.fields['previous_cycle'].required = False


class CredentialDocumentForm(forms.ModelForm):
    class Meta:
        model = CredentialDocument
        fields = [
            'requirement', 'nama_file', 'file',
            'tanggal_berlaku', 'tanggal_kedaluwarsa',
            'nomor_dokumen', 'catatan_pengunggah',
        ]
        widgets = {
            'tanggal_berlaku': forms.DateInput(attrs={'type': 'date'}),
            'tanggal_kedaluwarsa': forms.DateInput(attrs={'type': 'date'}),
            'catatan_pengunggah': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, application=None, **kwargs):
        super().__init__(*args, **kwargs)
        if application is not None:
            self.fields['requirement'].queryset = CredentialRequirement.objects.filter(
                profesi=application.profesi_snapshot, aktif=True,
            )


class DocumentVerificationForm(forms.ModelForm):
    class Meta:
        model = DocumentVerification
        fields = ['hasil', 'catatan', 'koreksi_diperlukan']
        widgets = {
            'catatan': forms.Textarea(attrs={'rows': 2}),
            'koreksi_diperlukan': forms.Textarea(attrs={'rows': 2}),
        }


class CredentialRequirementForm(forms.ModelForm):
    class Meta:
        model = CredentialRequirement
        fields = [
            'profesi', 'kategori', 'nama_syarat', 'deskripsi', 'wajib',
            'berlaku_untuk', 'masa_berlaku_hari', 'referensi_regulasi',
            'versi_kebijakan', 'aktif',
        ]
        widgets = {
            'deskripsi': forms.Textarea(attrs={'rows': 3}),
        }


# ==========================================
# ASESMEN KOMPETENSI
# ==========================================
class CompetencyAssessmentForm(forms.ModelForm):
    class Meta:
        model = CompetencyAssessment
        fields = [
            'asesor', 'nama_asesor_eksternal', 'metode', 'tanggal_asesmen',
            'ruang_lingkup', 'kriteria', 'temuan', 'bukti_pendukung',
            'rekomendasi_asesor', 'status', 'catatan_reviewer',
            'pernyataan_benturan_kepentingan',
        ]
        widgets = {
            'tanggal_asesmen': forms.DateInput(attrs={'type': 'date'}),
            'ruang_lingkup': forms.Textarea(attrs={'rows': 2}),
            'kriteria': forms.Textarea(attrs={'rows': 2}),
            'temuan': forms.Textarea(attrs={'rows': 3}),
            'bukti_pendukung': forms.Textarea(attrs={'rows': 2}),
            'rekomendasi_asesor': forms.Textarea(attrs={'rows': 2}),
            'catatan_reviewer': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['asesor'].required = False
        self.fields['nama_asesor_eksternal'].required = False


class AssessmentResultForm(forms.ModelForm):
    class Meta:
        model = AssessmentResult
        fields = ['kompetensi', 'hasil', 'skor', 'catatan']


# ==========================================
# MASTER KEWENANGAN KLINIS
# ==========================================
class ClinicalPrivilegeForm(forms.ModelForm):
    class Meta:
        model = ClinicalPrivilege
        fields = [
            'kode', 'profesi', 'nama', 'deskripsi', 'ruang_lingkup',
            'kompetensi_wajib', 'bukti_wajib', 'pembatasan',
            'aturan_supervisi', 'aktif', 'versi_kebijakan',
        ]
        widgets = {
            'deskripsi': forms.Textarea(attrs={'rows': 2}),
            'ruang_lingkup': forms.Textarea(attrs={'rows': 2}),
            'kompetensi_wajib': forms.Textarea(attrs={'rows': 2}),
            'bukti_wajib': forms.Textarea(attrs={'rows': 2}),
            'pembatasan': forms.Textarea(attrs={'rows': 2}),
            'aturan_supervisi': forms.Textarea(attrs={'rows': 2}),
        }


class RequestedPrivilegeForm(forms.ModelForm):
    class Meta:
        model = RequestedPrivilege
        fields = ['privilege', 'alasan', 'catatan']
        widgets = {
            'alasan': forms.Textarea(attrs={'rows': 2}),
            'catatan': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, application=None, **kwargs):
        super().__init__(*args, **kwargs)
        if application is not None:
            self.fields['privilege'].queryset = ClinicalPrivilege.objects.filter(
                profesi=application.profesi_snapshot, aktif=True,
            )


# ==========================================
# REKOMENDASI RKK
# ==========================================
class PrivilegeRecommendationForm(forms.ModelForm):
    class Meta:
        model = PrivilegeRecommendation
        fields = [
            'keputusan', 'pembatasan', 'kebutuhan_supervisi',
            'kualifikasi_supervisor', 'dasar_pertimbangan',
        ]
        widgets = {
            'pembatasan': forms.Textarea(attrs={'rows': 2}),
            'kebutuhan_supervisi': forms.Textarea(attrs={'rows': 2}),
            'dasar_pertimbangan': forms.Textarea(attrs={'rows': 3}),
        }


class CredentialReviewForm(forms.ModelForm):
    class Meta:
        model = CredentialReview
        fields = ['catatan', 'disetujui']
        widgets = {
            'catatan': forms.Textarea(attrs={'rows': 3}),
        }


# ==========================================
# PENETAPAN SPK / RKK
# ==========================================
class ClinicalAppointmentForm(forms.ModelForm):
    class Meta:
        model = ClinicalAppointment
        fields = [
            'nomor_spk', 'tanggal_terbit', 'tanggal_mulai_berlaku',
            'tanggal_akhir_berlaku', 'keputusan', 'lokasi_penugasan',
            'tanggal_review', 'target_rekredensial', 'catatan',
            'nama_pejabat_eksternal',
        ]
        widgets = {
            'tanggal_terbit': forms.DateInput(attrs={'type': 'date'}),
            'tanggal_mulai_berlaku': forms.DateInput(attrs={'type': 'date'}),
            'tanggal_akhir_berlaku': forms.DateInput(attrs={'type': 'date'}),
            'tanggal_review': forms.DateInput(attrs={'type': 'date'}),
            'target_rekredensial': forms.DateInput(attrs={'type': 'date'}),
            'catatan': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nama_pejabat_eksternal'].required = False


class AppointmentDocumentForm(forms.ModelForm):
    class Meta:
        model = ClinicalAppointment
        fields = ['dokumen_spk', 'lampiran_rkk']


# ==========================================
# MONITORING & FOLLOW-UP
# ==========================================
class CredentialFollowUpForm(forms.ModelForm):
    class Meta:
        model = CredentialFollowUp
        fields = [
            'oppe_terkait', 'temuan', 'rekomendasi_tindakan',
            'penanggung_jawab', 'tanggal_target', 'status',
            'bukti_penyelesaian', 'tanggal_selesai',
        ]
        widgets = {
            'temuan': forms.Textarea(attrs={'rows': 3}),
            'rekomendasi_tindakan': forms.Textarea(attrs={'rows': 2}),
            'bukti_penyelesaian': forms.Textarea(attrs={'rows': 2}),
            'tanggal_target': forms.DateInput(attrs={'type': 'date'}),
            'tanggal_selesai': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, application=None, **kwargs):
        super().__init__(*args, **kwargs)
        if application is not None:
            self.fields['oppe_terkait'].queryset = EvaluasiOPPE.objects.filter(
                nakes=application.nakes,
            )
