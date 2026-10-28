"""Sinkronisasi ringkasan kredensial ke field summary pada model Nakes.

Field `status_kredensial` dan `kewenangan_klinis` pada Nakes BUKAN sumber
kebenaran — sumber kebenaran adalah `CredentialApplication` +
`ClinicalAppointment` + `GrantedPrivilege`. Service ini hanya menurunkan
nilai ringkasan agar tampilan legacy tetap informatif.

Pemetaan:
- status_kredensial:
    'Belum Pengajuan' — tidak ada aplikasi
    'Dalam Proses'    — ada aplikasi aktif yang belum CLOSED
    'Selesai'         — ada aplikasi CLOSED (kredensial selesai)
- kewenangan_klinis:
    'Aktif'      — ada GrantedPrivilege status 'active'
    'Evaluasi'   — ada GrantedPrivilege 'suspended' atau follow-up overdue
    'Proses'     — ada aplikasi aktif tapi belum ada granted privilege
    'Tidak Aktif'— tidak ada granted privilege aktif dan tidak ada aplikasi aktif

Service ini dipanggil:
- otomatis setelah finalisasi SPK (appointment service)
- otomatis setelah perubahan status granted privilege
- manual via management command `sync_nakes_kredensial`
"""
from django.db import transaction
from django.utils import timezone

from nakes.models import Nakes
from ..models import (
    CredentialApplication,
    ClinicalAppointment,
    GrantedPrivilege,
    CredentialFollowUp,
)


def compute_summary(nakes):
    """Hitung ringkasan kredensial untuk satu Nakes. Return dict."""
    applications = CredentialApplication.objects.filter(nakes=nakes)
    active_apps = applications.filter(status='Aktif')
    closed_apps = applications.filter(workflow_state='CLOSED')

    granted_active = GrantedPrivilege.objects.filter(
        appointment__application__nakes=nakes,
        status='active',
    ).exists()
    granted_suspended = GrantedPrivilege.objects.filter(
        appointment__application__nakes=nakes,
        status='suspended',
    ).exists()

    overdue_followups = CredentialFollowUp.objects.filter(
        application__nakes=nakes,
        tanggal_target__lt=timezone.now().date(),
    ).exclude(status__in=['selesai', 'dibatalkan']).exists()

    # status_kredensial
    if not applications.exists():
        status_kredensial = 'Belum Pengajuan'
    elif closed_apps.exists() and not active_apps.exists():
        status_kredensial = 'Selesai'
    elif active_apps.exists():
        status_kredensial = 'Dalam Proses'
    else:
        status_kredensial = 'Dalam Proses'

    # kewenangan_klinis
    if granted_active and not granted_suspended and not overdue_followups:
        kewenangan_klinis = 'Aktif'
    elif granted_suspended or overdue_followups:
        kewenangan_klinis = 'Evaluasi'
    elif active_apps.exists():
        kewenangan_klinis = 'Proses'
    elif granted_active:
        kewenangan_klinis = 'Aktif'
    else:
        kewenangan_klinis = 'Tidak Aktif'

    return {
        'status_kredensial': status_kredensial,
        'kewenangan_klinis': kewenangan_klinis,
    }


@transaction.atomic
def sync_nakes(nakes):
    """Perbarui field ringkasan Nakes dari keputusan kredensial final.

    Return True jika ada perubahan.
    """
    summary = compute_summary(nakes)
    changed = False
    for field, value in summary.items():
        if getattr(nakes, field) != value:
            setattr(nakes, field, value)
            changed = True
    if changed:
        nakes.save(update_fields=['status_kredensial', 'kewenangan_klinis'])
    return changed


def sync_all():
    """Sinkronkan semua Nakes yang punya riwayat kredensial.

    Return (jumlah_diperbarui, jumlah_diperiksa).
    """
    nakes_ids = CredentialApplication.objects.values_list(
        'nakes_id', flat=True,
    ).distinct()
    updated = 0
    checked = 0
    for nakes in Nakes.objects.filter(pk__in=list(nakes_ids)):
        checked += 1
        if sync_nakes(nakes):
            updated += 1
    return updated, checked
