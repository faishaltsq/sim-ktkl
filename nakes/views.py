from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from openpyxl import Workbook

from .models import Nakes, DokumenNakes, AuditLog
from .forms import NakesForm, DokumenForm, NakesSearchForm


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
