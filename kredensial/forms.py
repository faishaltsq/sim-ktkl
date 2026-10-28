"""Form Sub. Kredensial — pengajuan, dokumen, verifikasi."""
from django import forms
from .models import (
    CredentialApplication,
    CredentialDocument,
    DocumentVerification,
    CredentialRequirement,
)


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
