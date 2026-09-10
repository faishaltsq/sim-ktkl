import os
from django import forms
from django.utils.safestring import mark_safe
from .models import (
    Nakes, DokumenNakes, DokumenUmum, Profesi,
    EvaluasiOPPE, EvaluasiMutuKlinis,
    PelanggaranEtik, SidangEtik, EvaluasiKinerjaEtik
)

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


_skor_widget = {'class': 'form-control form-control-sm skor-input', 'type': 'number', 'min': '0', 'max': '100', 'step': '0.01'}


class EvaluasiOPPEForm(forms.ModelForm):
    class Meta:
        model = EvaluasiOPPE
        fields = [
            'nakes', 'tahun', 'tanggal_evaluasi',
            'skor_perilaku_1', 'skor_perilaku_2', 'skor_perilaku_3', 'skor_perilaku_4',
            'skor_perilaku_5', 'skor_perilaku_6', 'skor_perilaku_7',
            'skor_profesional_1', 'skor_profesional_2', 'skor_profesional_3', 'skor_profesional_4',
            'skor_kinerja_1', 'skor_kinerja_2', 'skor_kinerja_3', 'skor_kinerja_4',
            'skor_kinerja_5', 'skor_kinerja_6', 'skor_kinerja_7', 'skor_kinerja_8', 'skor_kinerja_9',
            'penilai_nama', 'penilai_nip', 'mengetahui_nama', 'mengetahui_nip', 'pegawai_nip',
        ]
        widgets = {
            'nakes': forms.Select(attrs={'class': 'form-select', 'id': 'id_nakes'}),
            'tahun': forms.NumberInput(attrs={'class': 'form-control', 'min': '2000', 'max': '2100'}),
            'tanggal_evaluasi': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'skor_perilaku_1': forms.NumberInput(attrs=_skor_widget),
            'skor_perilaku_2': forms.NumberInput(attrs=_skor_widget),
            'skor_perilaku_3': forms.NumberInput(attrs=_skor_widget),
            'skor_perilaku_4': forms.NumberInput(attrs=_skor_widget),
            'skor_perilaku_5': forms.NumberInput(attrs=_skor_widget),
            'skor_perilaku_6': forms.NumberInput(attrs=_skor_widget),
            'skor_perilaku_7': forms.NumberInput(attrs=_skor_widget),
            'skor_profesional_1': forms.NumberInput(attrs=_skor_widget),
            'skor_profesional_2': forms.NumberInput(attrs=_skor_widget),
            'skor_profesional_3': forms.NumberInput(attrs=_skor_widget),
            'skor_profesional_4': forms.NumberInput(attrs=_skor_widget),
            'skor_kinerja_1': forms.NumberInput(attrs=_skor_widget),
            'skor_kinerja_2': forms.NumberInput(attrs=_skor_widget),
            'skor_kinerja_3': forms.NumberInput(attrs=_skor_widget),
            'skor_kinerja_4': forms.NumberInput(attrs=_skor_widget),
            'skor_kinerja_5': forms.NumberInput(attrs=_skor_widget),
            'skor_kinerja_6': forms.NumberInput(attrs=_skor_widget),
            'skor_kinerja_7': forms.NumberInput(attrs=_skor_widget),
            'skor_kinerja_8': forms.NumberInput(attrs=_skor_widget),
            'skor_kinerja_9': forms.NumberInput(attrs=_skor_widget),
            'penilai_nama': forms.TextInput(attrs={'class': 'form-control'}),
            'penilai_nip': forms.TextInput(attrs={'class': 'form-control'}),
            'mengetahui_nama': forms.TextInput(attrs={'class': 'form-control'}),
            'mengetahui_nip': forms.TextInput(attrs={'class': 'form-control'}),
            'pegawai_nip': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def get_sections(self):
        sections = []
        counter = 1
        for sec_key, sec_title, labels in EvaluasiOPPE.INDIKATOR_LABELS:
            items = []
            for idx, label in enumerate(labels, start=1):
                items.append((counter, label, self[f'skor_{sec_key}_{idx}']))
                counter += 1
            sections.append((sec_title, items))
        return sections


class EvaluasiMutuKlinisForm(forms.ModelForm):
    class Meta:
        model = EvaluasiMutuKlinis
        fields = [
            'unit_kerja', 'periode_bulan', 'periode_tahun',
            'nama_indikator', 'standar_target', 'capaian',
            'analisis', 'rencana_tindak_lanjut', 'penanggung_jawab',
        ]
        widgets = {
            'unit_kerja': forms.TextInput(attrs={'class': 'form-control'}),
            'periode_bulan': forms.Select(attrs={'class': 'form-select'}),
            'periode_tahun': forms.NumberInput(attrs={'class': 'form-control', 'min': '2000', 'max': '2100'}),
            'nama_indikator': forms.TextInput(attrs={'class': 'form-control'}),
            'standar_target': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100', 'step': '0.01'}),
            'capaian': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100', 'step': '0.01'}),
            'analisis': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'rencana_tindak_lanjut': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'penanggung_jawab': forms.TextInput(attrs={'class': 'form-control'}),
        }


class PelanggaranEtikForm(forms.ModelForm):
    class Meta:
        model = PelanggaranEtik
        fields = [
            'nakes', 'tanggal_kejadian', 'tanggal_lapor',
            'kategori', 'deskripsi', 'pelapor', 'status',
        ]
        widgets = {
            'nakes': forms.Select(attrs={'class': 'form-select'}),
            'tanggal_kejadian': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'tanggal_lapor': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'kategori': forms.Select(attrs={'class': 'form-select'}),
            'deskripsi': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Tuliskan kronologi pelanggaran etik...'}),
            'pelapor': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nama pelapor / sumber informasi'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class SidangEtikForm(forms.ModelForm):
    class Meta:
        model = SidangEtik
        fields = [
            'nakes', 'pelanggaran', 'judul_sidang',
            'tanggal_sidang', 'waktu_mulai', 'waktu_selesai',
            'tempat', 'perangkat_sidang', 'status',
            'hasil_investigasi', 'rekomendasi_pembinaan', 'tindak_lanjut',
        ]
        widgets = {
            'nakes': forms.Select(attrs={'class': 'form-select'}),
            'pelanggaran': forms.Select(attrs={'class': 'form-select'}),
            'judul_sidang': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Agenda / Judul Sidang Etik'}),
            'tanggal_sidang': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'waktu_mulai': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'waktu_selesai': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'tempat': forms.TextInput(attrs={'class': 'form-control'}),
            'perangkat_sidang': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Ketua: ..., Sekretaris: ..., Anggota: ...'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'hasil_investigasi': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Temuan fakta, telaah bukti & saksi...'}),
            'rekomendasi_pembinaan': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Teguran, pembinaan, penangguhan kewenangan...'}),
            'tindak_lanjut': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Status eksekusi pembinaan...'}),
        }


class EvaluasiKinerjaEtikForm(forms.ModelForm):
    class Meta:
        model = EvaluasiKinerjaEtik
        fields = [
            'nakes', 'periode_tahun', 'periode_semester',
            'predikat', 'status_kepatuhan',
            'catatan_evaluasi', 'rekomendasi_kelanjutan', 'evaluator',
        ]
        widgets = {
            'nakes': forms.Select(attrs={'class': 'form-select'}),
            'periode_tahun': forms.NumberInput(attrs={'class': 'form-control', 'min': '2000', 'max': '2100'}),
            'periode_semester': forms.Select(attrs={'class': 'form-select'}),
            'predikat': forms.Select(attrs={'class': 'form-select'}),
            'status_kepatuhan': forms.Select(attrs={'class': 'form-select'}),
            'catatan_evaluasi': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Ulasan kepatuhan etika & perilaku klinis...'}),
            'rekomendasi_kelanjutan': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Kelayakan perpanjangan SPK / RKK...'}),
            'evaluator': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nama evaluator / penilai'}),
        }
