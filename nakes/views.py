from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from .models import Nakes, DokumenNakes, AuditLog, DokumenUmum
from .forms import NakesForm, DokumenForm, NakesSearchForm, DokumenUmumForm


def log_audit(user, aksi, obj, detail=''):
    AuditLog.objects.create(
        user=user,
        aksi=aksi,
        model_name=obj.__class__.__name__,
        object_id=obj.pk,
        object_repr=str(obj),
        detail=detail,
    )


@login_required
def dashboard(request):
    today = date.today()
    nakes_list = Nakes.objects.all()
    total = nakes_list.count()
    kredensial_selesai = nakes_list.filter(status_kredensial='Selesai').count()
    kewenangan_aktif = nakes_list.filter(kewenangan_klinis='Aktif').count()

    warnings = []
    for n in nakes_list:
        for label, field in [('STR', 'masa_berlaku_str'), ('SIP', 'masa_berlaku_sip')]:
            exp = getattr(n, field)
            sisa = (exp - today).days
            if sisa < 0:
                warnings.append({
                    'level': 'danger',
                    'nakes': n,
                    'doc': label,
                    'tanggal': exp,
                    'sisa': sisa,
                    'msg': f'{n.nama} ({n.profesi}) - {label} sudah kedaluwarsa sejak {exp}',
                })
            elif sisa <= 180:
                warnings.append({
                    'level': 'warning',
                    'nakes': n,
                    'doc': label,
                    'tanggal': exp,
                    'sisa': sisa,
                    'msg': f'{n.nama} ({n.profesi}) - {label} akan habis pada {exp} ({sisa} hari lagi)',
                })

    warnings.sort(key=lambda x: x['sisa'])

    context = {
        'total': total,
        'kredensial_selesai': kredensial_selesai,
        'kewenangan_aktif': kewenangan_aktif,
        'warnings': warnings,
    }
    return render(request, 'nakes/dashboard.html', context)


@login_required
def nakes_list(request):
    form = NakesSearchForm(request.GET)
    qs = Nakes.objects.all()
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(nama__icontains=q) | Q(profesi__icontains=q))
    context = {'nakes_list': qs, 'form': form, 'q': q}
    return render(request, 'nakes/nakes_list.html', context)


@login_required
def nakes_create(request):
    if request.method == 'POST':
        form = NakesForm(request.POST)
        if form.is_valid():
            nakes = form.save(commit=False)
            nakes.created_by = request.user
            nakes.save()
            log_audit(request.user, 'CREATE', nakes)
            messages.success(request, f'Data {nakes.nama} berhasil ditambahkan.')
            return redirect('nakes:detail', pk=nakes.pk)
    else:
        form = NakesForm()
    return render(request, 'nakes/nakes_form.html', {'form': form, 'title': 'Tambah Tenaga Kesehatan'})


@login_required
def nakes_detail(request, pk):
    nakes = get_object_or_404(Nakes, pk=pk)
    dokumen = nakes.dokumen.all()
    dokumen_form = DokumenForm()
    context = {
        'nakes': nakes,
        'dokumen': dokumen,
        'dokumen_form': dokumen_form,
    }
    return render(request, 'nakes/nakes_detail.html', context)


@login_required
def nakes_update(request, pk):
    nakes = get_object_or_404(Nakes, pk=pk)
    if request.method == 'POST':
        form = NakesForm(request.POST, instance=nakes)
        if form.is_valid():
            changed = form.changed_data
            nakes = form.save()
            log_audit(request.user, 'UPDATE', nakes, detail=f'Field diubah: {", ".join(changed)}')
            messages.success(request, f'Data {nakes.nama} berhasil diperbarui.')
            return redirect('nakes:detail', pk=nakes.pk)
    else:
        form = NakesForm(instance=nakes)
    return render(request, 'nakes/nakes_form.html', {'form': form, 'title': f'Edit - {nakes.nama}'})


@login_required
def nakes_delete(request, pk):
    nakes = get_object_or_404(Nakes, pk=pk)
    if request.method == 'POST':
        log_audit(request.user, 'DELETE', nakes)
        nama = nakes.nama
        nakes.delete()
        messages.success(request, f'Data {nama} berhasil dihapus.')
        return redirect('nakes:list')
    return render(request, 'nakes/nakes_confirm_delete.html', {'nakes': nakes})


@login_required
def dokumen_upload(request, nakes_pk):
    nakes = get_object_or_404(Nakes, pk=nakes_pk)
    if request.method == 'POST':
        form = DokumenForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.nakes = nakes
            doc.uploaded_by = request.user
            doc.save()
            log_audit(request.user, 'CREATE', doc, detail=f'Upload {doc.jenis} untuk {nakes.nama}')
            messages.success(request, f'Dokumen {doc.jenis} berhasil diupload.')
    return redirect('nakes:detail', pk=nakes_pk)


@login_required
def dokumen_delete(request, pk):
    doc = get_object_or_404(DokumenNakes, pk=pk)
    nakes_pk = doc.nakes.pk
    if request.method == 'POST':
        log_audit(request.user, 'DELETE', doc)
        doc.file.delete(save=False)
        doc.delete()
        messages.success(request, 'Dokumen berhasil dihapus.')
    return redirect('nakes:detail', pk=nakes_pk)


@login_required
def audit_log(request):
    logs = AuditLog.objects.select_related('user').all()[:200]
    return render(request, 'nakes/audit_log.html', {'logs': logs})


@login_required
def export_excel(request):
    wb = Workbook()
    ws = wb.active
    ws.title = 'Data Nakes'

    headers = [
        'Nama', 'Profesi', 'Unit Kerja',
        'No STR', 'Masa Berlaku STR',
        'No SIP', 'Masa Berlaku SIP',
        'Status Kredensial', 'Kewenangan Klinis',
    ]
    ws.append(headers)

    for n in Nakes.objects.all():
        ws.append([
            n.nama, n.profesi, n.unit_kerja,
            n.no_str, n.masa_berlaku_str.isoformat(),
            n.no_sip, n.masa_berlaku_sip.isoformat(),
            n.status_kredensial, n.kewenangan_klinis,
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="data_nakes.xlsx"'
    wb.save(response)
    return response


@login_required
def download_template(request):
    wb = Workbook()
    ws = wb.active
    ws.title = 'Template Import'

    headers = [
        'nama', 'profesi', 'unit_kerja',
        'no_str', 'masa_berlaku_str',
        'no_sip', 'masa_berlaku_sip',
        'status_kredensial', 'kewenangan_klinis', 'catatan',
    ]

    header_fill = PatternFill(start_color='0C7C84', end_color='0C7C84', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF')
    center = Alignment(horizontal='center', vertical='center')
    thin = Side(style='thin', color='CCCCCC')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center
        cell.border = border

    example_rows = [
        ['Budi Santoso', 'ATLM', 'Laboratorium', 'STR-001-2021', '2026-12-31',
         'SIP-001-2021', '2026-12-31', 'Selesai', 'Aktif', ''],
        ['Siti Rahayu', 'Radiografer', 'Radiologi', 'STR-002-2022', '2027-06-30',
         'SIP-002-2022', '2027-06-30', 'Dalam Proses', 'Proses', 'Sedang proses perpanjangan'],
    ]

    note_fill = PatternFill(start_color='F0FAFA', end_color='F0FAFA', fill_type='solid')
    for row_data in example_rows:
        row_idx = ws.max_row + 1
        for col, val in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col, value=val)
            cell.fill = note_fill
            cell.border = border

    col_widths = [25, 18, 20, 18, 18, 18, 18, 18, 16, 30]
    for col, width in enumerate(col_widths, 1):
        ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = width

    ws.row_dimensions[1].height = 22

    info_ws = wb.create_sheet('Panduan')
    info_ws['A1'] = 'PANDUAN IMPORT DATA NAKES'
    info_ws['A1'].font = Font(bold=True, size=13, color='0C7C84')
    panduan = [
        ('', ''),
        ('Kolom', 'Keterangan'),
        ('nama', 'Nama lengkap tenaga kesehatan'),
        ('profesi', 'Pilih: ATLM | Radiografer | Fisioterapis | Nutrisionis | Perekam Medis | Apoteker | Sanitarian | Lainnya'),
        ('unit_kerja', 'Nama unit/departemen kerja'),
        ('no_str', 'Nomor STR (harus unik)'),
        ('masa_berlaku_str', 'Format: YYYY-MM-DD (contoh: 2026-12-31)'),
        ('no_sip', 'Nomor SIP (harus unik)'),
        ('masa_berlaku_sip', 'Format: YYYY-MM-DD (contoh: 2026-12-31)'),
        ('status_kredensial', 'Pilih: Belum Pengajuan | Dalam Proses | Selesai'),
        ('kewenangan_klinis', 'Pilih: Aktif | Evaluasi | Proses | Tidak Aktif'),
        ('catatan', 'Opsional. Catatan tambahan'),
        ('', ''),
        ('PENTING', 'Baris pertama (header) JANGAN diubah'),
        ('PENTING', 'Data dimulai dari baris ke-2'),
        ('PENTING', 'no_str dan no_sip harus unik; baris duplikat akan dilewati'),
    ]
    for r, (col_a, col_b) in enumerate(panduan, 2):
        info_ws.cell(row=r, column=1, value=col_a)
        info_ws.cell(row=r, column=2, value=col_b)
        if col_a == 'Kolom':
            for c in [1, 2]:
                info_ws.cell(row=r, column=c).font = Font(bold=True)
        if col_a == 'PENTING':
            info_ws.cell(row=r, column=1).font = Font(bold=True, color='C0392B')

    info_ws.column_dimensions['A'].width = 22
    info_ws.column_dimensions['B'].width = 80

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="template_import_nakes.xlsx"'
    wb.save(response)
    return response


@login_required
def upload_bulk(request):
    if request.method == 'POST':
        excel_file = request.FILES.get('excel_file')
        if not excel_file:
            messages.error(request, 'File Excel wajib diupload.')
            return redirect('nakes:upload_bulk')

        try:
            wb = load_workbook(excel_file, data_only=True)
            ws = wb.active
        except Exception:
            messages.error(request, 'File tidak valid. Pastikan format .xlsx.')
            return redirect('nakes:upload_bulk')

        EXPECTED_HEADERS = [
            'nama', 'profesi', 'unit_kerja',
            'no_str', 'masa_berlaku_str',
            'no_sip', 'masa_berlaku_sip',
            'status_kredensial', 'kewenangan_klinis', 'catatan',
        ]

        headers = [str(c.value).strip().lower() if c.value else '' for c in ws[1]]
        if headers[:len(EXPECTED_HEADERS)] != EXPECTED_HEADERS:
            messages.error(request, 'Header kolom tidak sesuai template. Download template terlebih dahulu.')
            return redirect('nakes:upload_bulk')

        PROFESI_VALID = {'ATLM', 'Radiografer', 'Fisioterapis', 'Nutrisionis',
                         'Perekam Medis', 'Apoteker', 'Sanitarian', 'Lainnya'}
        STATUS_VALID = {'Belum Pengajuan', 'Dalam Proses', 'Selesai'}
        KEWENANGAN_VALID = {'Aktif', 'Evaluasi', 'Proses', 'Tidak Aktif'}

        sukses = 0
        errors = []

        for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if all(v is None or str(v).strip() == '' for v in row):
                continue

            def get(idx):
                val = row[idx] if len(row) > idx else None
                return str(val).strip() if val is not None else ''

            nama = get(0)
            profesi = get(1)
            unit_kerja = get(2)
            no_str = get(3)
            masa_berlaku_str_raw = row[4] if len(row) > 4 else None
            no_sip = get(5)
            masa_berlaku_sip_raw = row[6] if len(row) > 6 else None
            status_kredensial = get(7) or 'Belum Pengajuan'
            kewenangan_klinis = get(8) or 'Proses'
            catatan = get(9)

            row_errors = []

            if not nama:
                row_errors.append('nama kosong')
            if profesi not in PROFESI_VALID:
                row_errors.append(f'profesi tidak valid: "{profesi}"')
            if not no_str:
                row_errors.append('no_str kosong')
            if not no_sip:
                row_errors.append('no_sip kosong')
            if status_kredensial not in STATUS_VALID:
                row_errors.append(f'status_kredensial tidak valid: "{status_kredensial}"')
            if kewenangan_klinis not in KEWENANGAN_VALID:
                row_errors.append(f'kewenangan_klinis tidak valid: "{kewenangan_klinis}"')

            from datetime import date as date_type
            import datetime

            def parse_date(val, label):
                if val is None:
                    return None, f'{label} kosong'
                if isinstance(val, (date_type, datetime.datetime)):
                    return val.date() if isinstance(val, datetime.datetime) else val, None
                try:
                    return date_type.fromisoformat(str(val).strip()), None
                except ValueError:
                    return None, f'{label} format salah (gunakan YYYY-MM-DD)'

            masa_str, err_str = parse_date(masa_berlaku_str_raw, 'masa_berlaku_str')
            if err_str:
                row_errors.append(err_str)
            masa_sip, err_sip = parse_date(masa_berlaku_sip_raw, 'masa_berlaku_sip')
            if err_sip:
                row_errors.append(err_sip)

            if row_errors:
                errors.append(f'Baris {row_num}: {", ".join(row_errors)}')
                continue

            if Nakes.objects.filter(no_str=no_str).exists():
                errors.append(f'Baris {row_num}: no_str "{no_str}" sudah ada, dilewati')
                continue
            if Nakes.objects.filter(no_sip=no_sip).exists():
                errors.append(f'Baris {row_num}: no_sip "{no_sip}" sudah ada, dilewati')
                continue

            nakes = Nakes.objects.create(
                nama=nama,
                profesi=profesi,
                unit_kerja=unit_kerja,
                no_str=no_str,
                masa_berlaku_str=masa_str,
                no_sip=no_sip,
                masa_berlaku_sip=masa_sip,
                status_kredensial=status_kredensial,
                kewenangan_klinis=kewenangan_klinis,
                catatan=catatan,
                created_by=request.user,
            )
            log_audit(request.user, 'CREATE', nakes, detail='Import bulk Excel')
            sukses += 1

        if sukses:
            messages.success(request, f'{sukses} data berhasil diimport.')
        if errors:
            for e in errors:
                messages.warning(request, e)
        if not sukses and not errors:
            messages.info(request, 'Tidak ada data yang diproses. File mungkin kosong.')

        return redirect('nakes:upload_bulk')

    return render(request, 'nakes/upload_bulk.html')


@login_required
def dokumen_hub(request):
    tab = request.GET.get('tab', 'nakes')
    q = request.GET.get('q', '').strip()
    kategori = request.GET.get('kategori', '')

    dokumen_nakes = DokumenNakes.objects.select_related('nakes', 'uploaded_by').all()
    if q:
        dokumen_nakes = dokumen_nakes.filter(
            Q(nama_file__icontains=q) | Q(nakes__nama__icontains=q)
        )

    dokumen_umum = DokumenUmum.objects.select_related('uploaded_by').all()
    if q and tab == 'umum':
        dokumen_umum = dokumen_umum.filter(
            Q(judul__icontains=q) | Q(deskripsi__icontains=q)
        )
    if kategori and tab == 'umum':
        dokumen_umum = dokumen_umum.filter(kategori=kategori)

    context = {
        'tab': tab,
        'q': q,
        'kategori': kategori,
        'dokumen_nakes': dokumen_nakes,
        'dokumen_umum': dokumen_umum,
        'kategori_choices': DokumenUmum.KATEGORI_CHOICES,
    }
    return render(request, 'nakes/dokumen_hub.html', context)


@login_required
def dokumen_umum_create(request):
    if request.method == 'POST':
        form = DokumenUmumForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.uploaded_by = request.user
            doc.save()
            log_audit(request.user, 'CREATE', doc, detail=f'Upload dokumen umum: {doc.judul}')
            messages.success(request, f'Dokumen "{doc.judul}" berhasil diupload.')
            return redirect('nakes:dokumen_hub')
    else:
        form = DokumenUmumForm()
    return render(request, 'nakes/dokumen_umum_form.html', {'form': form, 'title': 'Upload Dokumen Umum'})


@login_required
def dokumen_umum_edit(request, pk):
    doc = get_object_or_404(DokumenUmum, pk=pk)
    if request.method == 'POST':
        form = DokumenUmumForm(request.POST, request.FILES, instance=doc)
        if form.is_valid():
            changed = form.changed_data
            doc = form.save()
            log_audit(request.user, 'UPDATE', doc, detail=f'Field diubah: {", ".join(changed)}')
            messages.success(request, f'Dokumen "{doc.judul}" berhasil diperbarui.')
            return redirect('nakes:dokumen_hub')
    else:
        form = DokumenUmumForm(instance=doc)
    return render(request, 'nakes/dokumen_umum_form.html', {'form': form, 'title': f'Edit - {doc.judul}'})


@login_required
def dokumen_umum_delete(request, pk):
    doc = get_object_or_404(DokumenUmum, pk=pk)
    if request.method == 'POST':
        log_audit(request.user, 'DELETE', doc)
        doc.file.delete(save=False)
        doc.delete()
        messages.success(request, 'Dokumen berhasil dihapus.')
    return redirect('nakes:dokumen_hub')
