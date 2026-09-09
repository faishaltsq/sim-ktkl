import os
from django import forms
from django.utils.safestring import mark_safe
from .models import Nakes, DokumenNakes, DokumenUmum, Profesi

ALLOWED_DOC_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx', '.xls', '.xlsx'}
MAX_UPLOAD_SIZE = 15 * 1024 * 1024  # 15 MB


class DatalistTextInput(forms.TextInput):
    def __init__(self, datalist_id='profesi_list', attrs=None):
        self.datalist_id = datalist_id
        super().__init__(attrs=attrs)

    def render(self, name, value, attrs=None, renderer=None):
        attrs = attrs or {}
        attrs['list'] = self.datalist_id
        attrs.setdefault('autocomplete', 'off')
        input_html = super().render(name, value, attrs, renderer)
        options = ''.join(
            f'<option value="{p.nama}">' for p in Profesi.objects.all()
        )
        datalist_html = f'<datalist id="{self.datalist_id}">{options}</datalist>'
        return mark_safe(input_html + datalist_html)


class NakesForm(forms.ModelForm):
    profesi = forms.CharField(
        max_length=100,
        widget=DatalistTextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ketik atau pilih profesi...',
        }),
    )

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.profesi_id:
            self.initial['profesi'] = self.instance.profesi.nama

    def clean_profesi(self):
        nama = self.cleaned_data['profesi'].strip()
        if not nama:
            raise forms.ValidationError('Profesi wajib diisi.')
        profesi_obj, _ = Profesi.objects.get_or_create(nama=nama)
        return profesi_obj


class DokumenForm(forms.ModelForm):
    nama_file = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Nama dokumen (opsional)',
            'class': 'form-control form-control-sm',
        }),
    )

    class Meta:
        model = DokumenNakes
        fields = ['jenis', 'nama_file', 'file']
        widgets = {
            'jenis': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'file': forms.FileInput(attrs={'class': 'form-control form-control-sm', 'accept': '.pdf,.jpg,.jpeg,.png,.doc,.docx,.xls,.xlsx'}),
        }

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in ALLOWED_DOC_EXTENSIONS:
                raise forms.ValidationError(f'Format file "{ext}" tidak didukung. Gunakan PDF, JPG, PNG, DOC, atau XLS.')
            if file.size > MAX_UPLOAD_SIZE:
                raise forms.ValidationError('Ukuran file maksimal 15 MB.')
        return file

    def clean(self):
        cleaned_data = super().clean()
        nama_file = cleaned_data.get('nama_file')
        file = cleaned_data.get('file')
        if not nama_file and file:
            cleaned_data['nama_file'] = os.path.splitext(file.name)[0]
        return cleaned_data


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
            'file': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png,.doc,.docx,.xls,.xlsx'}),
        }

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in ALLOWED_DOC_EXTENSIONS:
                raise forms.ValidationError(f'Format file "{ext}" tidak didukung. Gunakan PDF, JPG, PNG, DOC, atau XLS.')
            if file.size > MAX_UPLOAD_SIZE:
                raise forms.ValidationError('Ukuran file maksimal 15 MB.')
        return file
