"""Views Sub. Kredensial — dashboard, pengajuan, verifikasi dokumen."""
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Count
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.utils import timezone
from django.conf import settings

from nakes.models import Nakes, Profesi, EvaluasiOPPE
from .models import (
    CredentialApplication,
    CredentialDocument,
    DocumentVerification,
    CredentialRequirement,
    CredentialEvent,
    ClinicalAppointment,
    GrantedPrivilege,
    CredentialFollowUp,
    ClinicalPrivilege,
    CompetencyAssessment,
    PrivilegeRecommendation,
)
from .forms import (
    CredentialApplicationForm,
    CredentialDocumentForm,
    DocumentVerificationForm,
    CredentialRequirementForm,
)
from .services import workflow
from .permissions import user_can, kredensial_role_required


# ==========================================
# DASHBOARD
# ==========================================
@login_required
def dashboard(request):
    today = timezone.now().date()
    apps_qs = CredentialApplication.objects.select_related('nakes', 'profesi_snapshot')

    kpi = {
        'total_aktif': apps_qs.filter(status='Aktif').count(),
        'menunggu_verifikasi': apps_qs.filter(
            workflow_state__in=['SUBMITTED', 'UNDER_VERIFICATION', 'RESUBMITTED'],
        ).count(),
        'menunggu_asesmen': apps_qs.filter(workflow_state='UNDER_ASSESSMENT').count(),
        'menunggu_keputusan': apps_qs.filter(workflow_state='PENDING_FINAL_DECISION').count(),
        'spk_mendekati_kedaluwarsa': ClinicalAppointment.objects.filter(
            is_final=True,
            tanggal_akhir_berlaku__gte=today,
            tanggal_akhir_berlaku__lte=today + timezone.timedelta(days=90),
        ).count(),
    }

    context = {
        **kpi,
        'applications': apps_qs.filter(status='Aktif').order_by('-tanggal_pengajuan')[:15],
        'recent_events': CredentialEvent.objects.select_related('application', 'aktor').order_by('-timestamp')[:10],
        'recent_decisions': ClinicalAppointment.objects.filter(is_final=True).select_related(
            'application__nakes',
        ).order_by('-tanggal_keputusan')[:5],
        'upcoming_recredential': ClinicalAppointment.objects.filter(
            is_final=True, target_rekredensial__gte=today,
        ).select_related('application__nakes').order_by('target_rekredensial')[:10],
        'overdue_followups': CredentialFollowUp.objects.filter(
            tanggal_target__lt=today,
        ).exclude(status__in=['selesai', 'dibatalkan']).select_related('application__nakes')[:10],
    }
    return render(request, 'kredensial/dashboard.html', context)


# ==========================================
# PENGAJUAN — LIST & CRUD
# ==========================================
@login_required
def application_list(request):
    qs = CredentialApplication.objects.select_related(
        'nakes', 'profesi_snapshot', 'diajukan_oleh', 'verifikator',
    ).order_by('-tanggal_pengajuan', '-created_at')

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(nomor_pengajuan__icontains=q) | Q(nakes__nama__icontains=q),
        )
    jenis = request.GET.get('jenis', '')
    if jenis:
        qs = qs.filter(jenis=jenis)
    state = request.GET.get('state', '')
    if state:
        qs = qs.filter(workflow_state=state)
    profesi = request.GET.get('profesi', '')
    if profesi:
        qs = qs.filter(profesi_snapshot_id=profesi)

    context = {
        'applications': qs,
        'q': q,
        'jenis_filter': jenis,
        'state_filter': state,
        'profesi_filter': profesi,
        'jenis_choices': CredentialApplication.JENIS_CHOICES,
        'state_choices': CredentialApplication.STATE_CHOICES,
        'profesi_list': Profesi.objects.all(),
    }
    return render(request, 'kredensial/application_list.html', context)


@login_required
@kredensial_role_required('create_application')
def application_create(request):
    if request.method == 'POST':
        form = CredentialApplicationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                app = form.save(commit=False)
                app.diajukan_oleh = request.user
                # Snapshot dari Nakes
                app.profesi_snapshot = app.nakes.profesi
                app.unit_kerja_snapshot = app.nakes.unit_kerja
                app.nomor_pengajuan = _generate_nomor(app)
                app.save()
                CredentialEvent.objects.create(
                    application=app, dari_state='', ke_state='DRAFT',
                    aksi='create', aktor=request.user,
                    catatan='Pengajuan dibuat.',
                )
            messages.success(request, f'Pengajuan {app.nomor_pengajuan} berhasil dibuat.')
            return redirect('kredensial:application_detail', pk=app.pk)
    else:
        form = CredentialApplicationForm()
    return render(request, 'kredensial/application_form.html', {'form': form, 'mode': 'create'})


@login_required
def application_detail(request, pk):
    app = get_object_or_404(
        CredentialApplication.objects.select_related(
            'nakes', 'profesi_snapshot', 'verifikator', 'diajukan_oleh',
        ), pk=pk,
    )
    documents = app.documents.select_related('requirement').prefetch_related('verifications')
    requirements = CredentialRequirement.objects.filter(
        profesi=app.profesi_snapshot, aktif=True,
    )
    assessments = app.assessments.prefetch_related('results').select_related('asesor')
    requested = app.requested_privileges.select_related('privilege')
    rec_map = {
        r.requested_privilege_id: r
        for r in PrivilegeRecommendation.objects.filter(
            requested_privilege__application=app,
        ).select_related('direkomendasikan_oleh')
    }
    requested_with_rec = [
        {'privilege': rp.privilege, 'recommendation': rec_map.get(rp.pk)}
        for rp in requested
    ]
    appointment = getattr(app, 'appointment', None)
    granted = appointment.granted_privileges.select_related('privilege') if appointment else []
    events = app.events.select_related('aktor').order_by('-timestamp')
    oppe_list = EvaluasiOPPE.objects.filter(nakes=app.nakes).order_by('-tahun')[:5]
    follow_ups = app.follow_ups.select_related('oppe_terkait')

    transitions = workflow.available_transitions(app, request.user)

    # Stepper: tahap yang sudah dilewati
    STEPPER = [
        ('Pengajuan', ['DRAFT', 'SUBMITTED', 'UNDER_VERIFICATION', 'REVISION_REQUIRED', 'RESUBMITTED',
                       'VERIFIED', 'UNDER_ASSESSMENT', 'ASSESSMENT_COMPLETED', 'RECOMMENDATION_REVIEW',
                       'RECOMMENDED', 'PENDING_FINAL_DECISION', 'RETURNED_FOR_REVISION', 'APPROVED',
                       'DOCUMENT_ISSUED', 'CLOSED']),
        ('Verifikasi', ['UNDER_VERIFICATION', 'REVISION_REQUIRED', 'RESUBMITTED', 'VERIFIED',
                        'UNDER_ASSESSMENT', 'ASSESSMENT_COMPLETED', 'RECOMMENDATION_REVIEW',
                        'RECOMMENDED', 'PENDING_FINAL_DECISION', 'RETURNED_FOR_REVISION', 'APPROVED',
                        'DOCUMENT_ISSUED', 'CLOSED']),
        ('Asesmen', ['UNDER_ASSESSMENT', 'ASSESSMENT_COMPLETED', 'RECOMMENDATION_REVIEW',
                     'RECOMMENDED', 'PENDING_FINAL_DECISION', 'RETURNED_FOR_REVISION', 'APPROVED',
                     'DOCUMENT_ISSUED', 'CLOSED']),
        ('Rekomendasi', ['RECOMMENDATION_REVIEW', 'RECOMMENDED', 'PENDING_FINAL_DECISION',
                         'RETURNED_FOR_REVISION', 'APPROVED', 'DOCUMENT_ISSUED', 'CLOSED']),
        ('Penetapan', ['PENDING_FINAL_DECISION', 'APPROVED', 'DOCUMENT_ISSUED', 'CLOSED']),
        ('Monitoring', ['DOCUMENT_ISSUED', 'CLOSED']),
    ]
    stepper = []
    for i, (label, states) in enumerate(STEPPER, start=1):
        stepper.append({'num': i, 'label': label, 'active': app.workflow_state in states})

    context = {
        'app': app,
        'documents': documents,
        'requirements': requirements,
        'assessments': assessments,
        'requested_privileges': requested_with_rec,
        'appointment': appointment,
        'granted_privileges': granted,
        'events': events,
        'oppe_list': oppe_list,
        'follow_ups': follow_ups,
        'available_transitions': transitions,
        'stepper': stepper,
        'can_create': user_can(request.user, 'create_application'),
        'can_verify': user_can(request.user, 'verify_document'),
        'can_assess': user_can(request.user, 'assess'),
        'can_recommend': user_can(request.user, 'recommend'),
        'can_approve': user_can(request.user, 'approve'),
    }
    return render(request, 'kredensial/application_detail.html', context)


@login_required
@kredensial_role_required('create_application')
def application_update(request, pk):
    app = get_object_or_404(CredentialApplication, pk=pk)
    if app.workflow_state not in ('DRAFT', 'REVISION_REQUIRED'):
        messages.error(request, 'Pengajuan hanya bisa diubah pada status Draft atau Perlu Perbaikan.')
        return redirect('kredensial:application_detail', pk=pk)
    if request.method == 'POST':
        form = CredentialApplicationForm(request.POST, instance=app)
        if form.is_valid():
            app = form.save(commit=False)
            app.profesi_snapshot = app.nakes.profesi
            app.unit_kerja_snapshot = app.nakes.unit_kerja
            app.save()
            messages.success(request, 'Pengajuan berhasil diperbarui.')
            return redirect('kredensial:application_detail', pk=app.pk)
    else:
        form = CredentialApplicationForm(instance=app)
    return render(request, 'kredensial/application_form.html', {'form': form, 'mode': 'update', 'app': app})


def _generate_nomor(app):
    today = timezone.now()
    prefix = f"KRED-{today:%Y%m}-"
    count = CredentialApplication.objects.filter(nomor_pengajuan__startswith=prefix).count() + 1
    nomor = f"{prefix}{count:04d}"
    while CredentialApplication.objects.filter(nomor_pengajuan=nomor).exists():
        count += 1
        nomor = f"{prefix}{count:04d}"
    return nomor


# ==========================================
# TRANSISI WORKFLOW
# ==========================================
@login_required
def application_transition(request, pk, to_state):
    app = get_object_or_404(CredentialApplication, pk=pk)
    if request.method != 'POST':
        return redirect('kredensial:application_detail', pk=pk)
    catatan = request.POST.get('catatan', '')
    try:
        event = workflow.transition(app, to_state, request.user, catatan=catatan)
        if event:
            messages.success(request, f'Status diperbarui ke {app.get_workflow_state_display()}.')
        else:
            messages.info(request, 'Status sudah berada di tahap tersebut.')
    except Exception as e:
        messages.error(request, str(e))
    return redirect('kredensial:application_detail', pk=pk)


# ==========================================
# DOKUMEN — UPLOAD & DOWNLOAD
# ==========================================
@login_required
@kredensial_role_required('create_application')
def document_upload(request, pk):
    app = get_object_or_404(CredentialApplication, pk=pk)
    if request.method == 'POST':
        form = CredentialDocumentForm(request.POST, request.FILES, application=app)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.application = app
            doc.uploaded_by = request.user
            # Versioning: versi baru = versi aktif lama + 1, nonaktifkan lama
            last = app.documents.filter(requirement=doc.requirement).order_by('-versi').first()
            doc.versi = (last.versi + 1) if last else 1
            with transaction.atomic():
                app.documents.filter(requirement=doc.requirement).update(is_versi_aktif=False)
                doc.is_versi_aktif = True
                doc.save()
            messages.success(request, f'Dokumen "{doc.requirement.nama_syarat}" v{doc.versi} berhasil diunggah.')
            return redirect('kredensial:application_detail', pk=app.pk)
    else:
        form = CredentialDocumentForm(application=app)
    return render(request, 'kredensial/document_upload.html', {'form': form, 'app': app})


@login_required
def document_download(request, pk):
    doc = get_object_or_404(CredentialDocument, pk=pk)
    if not _can_access_document(request.user, doc):
        return HttpResponseForbidden('Anda tidak memiliki akses ke dokumen ini.')
    if not doc.file:
        raise Http404('Berkas tidak ditemukan.')
    return FileResponse(doc.file.open('rb'), as_attachment=True, filename=os.path.basename(doc.file.name))


def _can_access_document(user, doc):
    if user.is_superuser:
        return True
    if user.username == 'demo':
        return False
    return user_can(user, 'verify_document') or user_can(user, 'create_application') or user_can(user, 'monitor')


# ==========================================
# VERIFIKASI DOKUMEN
# ==========================================
@login_required
@kredensial_role_required('verify_document')
def document_verify(request, pk):
    doc = get_object_or_404(
        CredentialDocument.objects.select_related('application', 'requirement'), pk=pk,
    )
    if request.method == 'POST':
        form = DocumentVerificationForm(request.POST)
        if form.is_valid():
            ver = form.save(commit=False)
            ver.document = doc
            ver.diverifikasi_oleh = request.user
            ver.save()
            messages.success(request, f'Hasil verifikasi "{doc.requirement.nama_syarat}" dicatat.')
            return redirect('kredensial:application_detail', pk=doc.application_id)
    else:
        form = DocumentVerificationForm()
    history = doc.verifications.select_related('diverifikasi_oleh').order_by('-tanggal_verifikasi')
    return render(request, 'kredensial/verification.html', {
        'form': form, 'doc': doc, 'history': history,
    })


@login_required
@kredensial_role_required('manage_master')
def requirement_list(request):
    qs = CredentialRequirement.objects.select_related('profesi').order_by('profesi__nama', 'kategori')
    profesi = request.GET.get('profesi', '')
    if profesi:
        qs = qs.filter(profesi_id=profesi)
    return render(request, 'kredensial/requirement_list.html', {
        'requirements': qs,
        'profesi_list': Profesi.objects.all(),
        'profesi_filter': profesi,
    })


@login_required
@kredensial_role_required('manage_master')
def requirement_create(request):
    if request.method == 'POST':
        form = CredentialRequirementForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Syarat kredensial berhasil ditambahkan.')
            return redirect('kredensial:requirement_list')
    else:
        form = CredentialRequirementForm()
    return render(request, 'kredensial/requirement_form.html', {'form': form, 'mode': 'create'})


@login_required
@kredensial_role_required('manage_master')
def requirement_update(request, pk):
    req = get_object_or_404(CredentialRequirement, pk=pk)
    if request.method == 'POST':
        form = CredentialRequirementForm(request.POST, instance=req)
        if form.is_valid():
            form.save()
            messages.success(request, 'Syarat kredensial berhasil diperbarui.')
            return redirect('kredensial:requirement_list')
    else:
        form = CredentialRequirementForm(instance=req)
    return render(request, 'kredensial/requirement_form.html', {'form': form, 'mode': 'update'})
