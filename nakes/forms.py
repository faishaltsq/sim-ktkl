from django import forms
from .models import Nakes, DokumenNakes, DokumenUmum


class NakesForm(forms.ModelForm):
    class Meta:
        model = Nakes
        fields = [
            'nama', 'profesi', 'unit_kerja',
            'no_str', 'masa_berlaku_str',
            'no_sip', 'masa_berlaku_sip',
            'status_kredensial', 'kewenangan_klinis',
            'catatan',
        ]
        widgets = {
            'masa_berlaku_str': forms.DateInput(attrs={'type': 'date'}),
            'masa_berlaku_sip': forms.DateInput(attrs={'type': 'date'}),
            'catatan': forms.Textarea(attrs={'rows': 3}),
        }


class DokumenForm(forms.ModelForm):
    class Meta:
        model = DokumenNakes
        fields = ['jenis', 'nama_file', 'file']


class NakesSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Cari nama atau profesi...',
            'class': 'form-control',
        }),
    )


class DokumenUmumForm(forms.ModelForm):
    class Meta:
        model = DokumenUmum
        fields = ['judul', 'kategori', 'deskripsi', 'file']
        widgets = {
            'judul': forms.TextInput(attrs={'class': 'form-control'}),
            'kategori': forms.Select(attrs={'class': 'form-select'}),
            'deskripsi': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
        }
