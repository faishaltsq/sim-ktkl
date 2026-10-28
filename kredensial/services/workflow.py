"""Service workflow Sub. Kredensial — transisi state transaksional + event history.

Setiap transisi:
- divalidasi terhadap state machine (ALLOWED_TRANSITIONS)
- dicek kewenangannya server-side (permissions.user_can_transition)
- dicek bukti wajibnya (dokumen lengkap, asesmen selesai, dll)
- dijalankan dalam @transaction.atomic
- idempoten: transisi yang sama berulang tidak menduplikasi efek
- selalu menulis CredentialEvent (append-only)
"""
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from ..models import CredentialApplication, CredentialEvent, CredentialDocument, DocumentVerification
from ..permissions import user_can_transition

# State machine — hanya pasangan ini yang legal
ALLOWED_TRANSITIONS = {
    'DRAFT': ['SUBMITTED'],
    'SUBMITTED': ['UNDER_VERIFICATION'],
    'UNDER_VERIFICATION': ['REVISION_REQUIRED', 'VERIFIED'],
    'REVISION_REQUIRED': ['RESUBMITTED'],
    'RESUBMITTED': ['UNDER_VERIFICATION'],
    'VERIFIED': ['UNDER_ASSESSMENT'],
    'UNDER_ASSESSMENT': ['ASSESSMENT_COMPLETED'],
    'ASSESSMENT_COMPLETED': ['RECOMMENDATION_REVIEW'],
    'RECOMMENDATION_REVIEW': ['RECOMMENDED'],
    'RECOMMENDED': ['PENDING_FINAL_DECISION'],
    'PENDING_FINAL_DECISION': ['RETURNED_FOR_REVISION', 'REJECTED', 'APPROVED'],
    'RETURNED_FOR_REVISION': ['RESUBMITTED'],
    'APPROVED': ['DOCUMENT_ISSUED'],
    'DOCUMENT_ISSUED': ['CLOSED'],
    'REJECTED': [],
    'CLOSED': [],
}


def is_transition_allowed(from_state, to_state):
    return to_state in ALLOWED_TRANSITIONS.get(from_state, [])


def _check_documents_verified(application):
    """Semua requirement wajib untuk profesi ini harus punya dokumen versi aktif
    dengan verifikasi terbaru berhasil 'valid' (atau 'tidak_berlaku')."""
    from ..models import CredentialRequirement

    requirements = CredentialRequirement.objects.filter(
        profesi=application.profesi_snapshot, wajib=True, aktif=True,
    )
    missing = []
    for req in requirements:
        doc = application.documents.filter(
            requirement=req, is_versi_aktif=True,
        ).first()
        if doc is None:
            missing.append(f"{req.nama_syarat} (belum diunggah)")
            continue
        latest = doc.verifications.order_by('-tanggal_verifikasi').first()
        if latest is None or latest.hasil not in ('valid', 'tidak_berlaku'):
            missing.append(f"{req.nama_syarat} (verifikasi belum valid)")
    return missing


def _check_assessments_completed(application):
    """Minimal satu asesmen selesai dengan hasil tercatat."""
    return application.assessments.filter(status='selesai').exists()


def _check_recommendations_exist(application):
    """Setiap requested privilege punya rekomendasi."""
    for rp in application.requested_privileges.all():
        if not hasattr(rp, 'recommendation'):
            return False
    return application.requested_privileges.exists()


def _check_committee_endorsed(application):
    review = getattr(application, 'committee_review', None)
    return bool(review and review.disetujui)


def _check_appointment_ready(application):
    """Keputusan final butuh appointment record yang valid."""
    appt = getattr(application, 'appointment', None)
    if appt is None:
        return False
    appt.full_clean()
    return True


# Bukti wajib per transisi (fungsi → application, return True/missing-list)
TRANSITION_EVIDENCE = {
    ('UNDER_VERIFICATION', 'VERIFIED'): _check_documents_verified,
    ('UNDER_ASSESSMENT', 'ASSESSMENT_COMPLETED'): _check_assessments_completed,
    ('RECOMMENDATION_REVIEW', 'RECOMMENDED'): _check_recommendations_exist,
    ('RECOMMENDED', 'PENDING_FINAL_DECISION'): _check_committee_endorsed,
    ('PENDING_FINAL_DECISION', 'APPROVED'): _check_appointment_ready,
}


def transition(application, to_state, actor, catatan='', aksi=None):
    """Jalankan transisi workflow secara transaksional.

    Returns CredentialEvent yang dibuat. Raise ValidationError jika ilegal.
    Idempoten: jika aplikasi sudah di to_state, tidak membuat event baru.
    """
    from_state = application.workflow_state

    # Idempotency — sudah di state tujuan
    if from_state == to_state:
        return None

    if not is_transition_allowed(from_state, to_state):
        raise ValidationError(
            f"Transisi tidak diizinkan: {from_state} → {to_state}."
        )

    if not user_can_transition(actor, from_state, to_state):
        raise ValidationError(
            f"Pengguna tidak memiliki kewenangan untuk transisi {from_state} → {to_state}."
        )

    evidence_fn = TRANSITION_EVIDENCE.get((from_state, to_state))
    if evidence_fn is not None:
        result = evidence_fn(application)
        if result is False or (isinstance(result, list) and result):
            detail = ', '.join(result) if isinstance(result, list) else 'bukti belum lengkap'
            raise ValidationError(f"Bukti transisi belum lengkap: {detail}.")

    with transaction.atomic():
        application.workflow_state = to_state
        now = timezone.now()

        # Timestamp per state
        ts_map = {
            'SUBMITTED': 'submitted_at',
            'VERIFIED': 'verified_at',
            'ASSESSMENT_COMPLETED': 'assessment_completed_at',
            'RECOMMENDED': 'recommended_at',
            'APPROVED': 'decision_at',
            'CLOSED': 'closed_at',
        }
        if to_state in ts_map:
            setattr(application, ts_map[to_state], now)

        # Status ringkas
        if to_state == 'REJECTED':
            application.status = 'Ditolak'
        elif to_state == 'CLOSED':
            application.status = 'Selesai'

        application.save()

        event = CredentialEvent.objects.create(
            application=application,
            dari_state=from_state,
            ke_state=to_state,
            aksi=aksi or to_state.lower(),
            aktor=actor,
            catatan=catatan,
            timestamp=now,
        )

    return event


def available_transitions(application, actor):
    """Daftar transisi yang legal dari state sekarang untuk aktor ini."""
    current = application.workflow_state
    return [
        to_state
        for to_state in ALLOWED_TRANSITIONS.get(current, [])
        if user_can_transition(actor, current, to_state)
    ]
