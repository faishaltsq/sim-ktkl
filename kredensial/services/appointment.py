"""Service penetapan SPK/RKK — keputusan final transaksional + snapshot privilege.

Aturan integritas:
- Hanya pejabat berwenang (permissions.user_can 'approve') yang boleh finalisasi
- Nomor SPK unik dalam cakupan penerbitan
- Rentang tanggal divalidasi (mulai <= akhir)
- Granted privilege berasal dari rekomendasi yang dapat ditinjau
- Finalisasi @transaction.atomic + idempotensi (cek is_final)
- Tidak ada edit keputusan final tanpa proses amendment/replacement
"""
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from ..models import (
    CredentialApplication,
    ClinicalAppointment,
    GrantedPrivilege,
    PrivilegeRecommendation,
    CredentialEvent,
)
from ..permissions import user_can


def validate_appointment_data(nomor_spk, tanggal_mulai, tanggal_akhir, tanggal_terbit=None):
    """Validasi data SPK sebelum finalisasi."""
    errors = {}
    if not nomor_spk or not nomor_spk.strip():
        errors['nomor_spk'] = 'Nomor SPK wajib diisi.'
    else:
        qs = ClinicalAppointment.objects.filter(nomor_spk=nomor_spk.strip())
        if qs.exists():
            errors['nomor_spk'] = f'Nomor SPK "{nomor_spk}" sudah digunakan.'

    if tanggal_mulai and tanggal_akhir and tanggal_akhir < tanggal_mulai:
        errors['tanggal_akhir_berlaku'] = 'Tanggal akhir berlaku tidak boleh sebelum tanggal mulai berlaku.'

    if errors:
        raise ValidationError(errors)


def build_granted_from_recommendations(application, selections):
    """Bangun daftar GrantedPrivilege dari rekomendasi + pilihan pejabat.

    `selections`: list dict {'requested_privilege_id': int, 'approved': bool,
    'redaksi_final': str, 'pembatasan': str, 'kebutuhan_supervisi': str}
    Hanya privilege dengan rekomendasi yang dapat ditinjau yang boleh dipilih.
    """
    rec_map = {
        r.requested_privilege_id: r
        for r in PrivilegeRecommendation.objects.filter(
            requested_privilege__application=application,
        )
    }
    granted = []
    for sel in selections:
        rp_id = sel.get('requested_privilege_id')
        if rp_id not in rec_map:
            raise ValidationError(
                f'Kewenangan diminta id={rp_id} tidak memiliki rekomendasi yang dapat ditinjau.'
            )
        if not sel.get('approved'):
            continue
        rec = rec_map[rp_id]
        granted.append({
            'privilege': rec.requested_privilege.privilege,
            'redaksi_final': sel.get('redaksi_final') or rec.requested_privilege.privilege.nama,
            'pembatasan': sel.get('pembatasan', rec.pembatasan),
            'kebutuhan_supervisi': sel.get('kebutuhan_supervisi', rec.kebutuhan_supervisi),
        })
    return granted


def finalize_appointment(application, appointment_data, granted_selections, actor):
    """Finalisasi keputusan SPK secara transaksional.

    - Cek kewenangan pejabat
    - Cek idempotensi (sudah final → tolak)
    - Validasi nomor & tanggal
    - Simpan appointment + granted privilege snapshot
    - Catat event
    Returns ClinicalAppointment.
    """
    if not user_can(actor, 'approve'):
        raise ValidationError('Hanya pejabat berwenang yang dapat memfinalisasi keputusan SPK.')

    existing = getattr(application, 'appointment', None)
    if existing is not None and existing.is_final:
        raise ValidationError('Keputusan untuk pengajuan ini sudah difinalisasi.')

    validate_appointment_data(
        appointment_data.get('nomor_spk'),
        appointment_data.get('tanggal_mulai_berlaku'),
        appointment_data.get('tanggal_akhir_berlaku'),
    )

    granted = build_granted_from_recommendations(application, granted_selections)

    with transaction.atomic():
        if existing is None:
            appointment = ClinicalAppointment(application=application)
        else:
            appointment = existing

        for field in ('nomor_spk', 'tanggal_terbit', 'tanggal_mulai_berlaku',
                      'tanggal_akhir_berlaku', 'keputusan', 'lokasi_penugasan',
                      'tanggal_review', 'target_rekredensial', 'catatan',
                      'nama_pejabat_eksternal'):
            if field in appointment_data:
                setattr(appointment, field, appointment_data[field])

        appointment.pejabat_berwenang = actor
        appointment.tanggal_keputusan = timezone.now()
        appointment.is_final = True
        appointment.finalized_at = timezone.now()
        appointment.save()

        # Snapshot granted privileges (hapus snapshot lama bila appointment direvisi)
        appointment.granted_privileges.all().delete()
        for g in granted:
            GrantedPrivilege.objects.create(
                appointment=appointment,
                privilege=g['privilege'],
                redaksi_final=g['redaksi_final'],
                pembatasan=g['pembatasan'],
                kebutuhan_supervisi=g['kebutuhan_supervisi'],
                tanggal_mulai=appointment.tanggal_mulai_berlaku,
                tanggal_akhir=appointment.tanggal_akhir_berlaku,
                status='active',
            )

        CredentialEvent.objects.create(
            application=application,
            dari_state=application.workflow_state,
            ke_state=application.workflow_state,
            aksi='finalisasi_spk',
            aktor=actor,
            catatan=f"SPK {appointment.nomor_spk} difinalisasi ({appointment.get_keputusan_display()}).",
        )

    return appointment


def attach_signed_document(appointment, spk_file=None, rkk_file=None):
    """Lampirkan dokumen SPK/RKK resmi yang telah ditandatangani."""
    if appointment.is_final:
        raise ValidationError(
            'Dokumen pada SPK final hanya boleh ditambahkan melalui proses amendment.'
        )
    if spk_file is not None:
        appointment.dokumen_spk = spk_file
    if rkk_file is not None:
        appointment.lampiran_rkk = rkk_file
    appointment.save(update_fields=[
        f for f, v in (('dokumen_spk', spk_file), ('lampiran_rkk', rkk_file)) if v is not None
    ])
    return appointment


def change_granted_status(granted_privilege, new_status, actor, catatan=''):
    """Ubah status efektif kewenangan (suspensi, pencabutan, kedaluwarsa).

    Selalu tercatat sebagai event — tidak ada perubahan senyap.
    """
    allowed = {'active', 'suspended', 'expired', 'revoked', 'superseded'}
    if new_status not in allowed:
        raise ValidationError(f'Status tidak valid: {new_status}')

    old = granted_privilege.status
    granted_privilege.status = new_status
    granted_privilege.catatan_perubahan = catatan
    granted_privilege.save(update_fields=['status', 'catatan_perubahan'])

    CredentialEvent.objects.create(
        application=granted_privilege.appointment.application,
        dari_state=old,
        ke_state=new_status,
        aksi='perubahan_kewenangan',
        aktor=actor,
        catatan=catatan or f'{granted_privilege.privilege.nama}: {old} → {new_status}',
    )
    return granted_privilege
