"""Test integrasi Sub. Kredensial — views, permissions, security."""
from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from nakes.models import Nakes, Profesi, EvaluasiOPPE
from kredensial.models import (
    CredentialRequirement, CredentialApplication, CredentialDocument,
    DocumentVerification, ClinicalPrivilege, RequestedPrivilege,
    CompetencyAssessment, PrivilegeRecommendation, CredentialReview,
    GrantedPrivilege, ClinicalAppointment, CredentialEvent,
    CredentialFollowUp,
)
from kredensial.permissions import ROLE_GROUPS, user_can, user_can_transition
from kredensial.services import appointment as appointment_service


def make_group(role):
    group, _ = Group.objects.get_or_create(name=ROLE_GROUPS[role])
    return group


class KredensialViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='sekretariat', password='x')
        make_group('sekretariat')
        self.user.groups.add(Group.objects.get(name=ROLE_GROUPS['sekretariat']))
        self.client.login(username='sekretariat', password='x')

        self.profesi, _ = Profesi.objects.get_or_create(nama='ATLM')
        self.nakes = Nakes.objects.create(
            nama='Siti Rahayu', profesi=self.profesi, unit_kerja='Lab',
            no_str='STR-VIEW-1', masa_berlaku_str='2027-01-01',
            no_sip='SIP-VIEW-1', masa_berlaku_sip='2027-01-01',
            created_by=self.user,
        )

    def test_dashboard_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse('kredensial:dashboard'))
        self.assertEqual(resp.status_code, 302)

    def test_dashboard_ok(self):
        resp = self.client.get(reverse('kredensial:dashboard'))
        self.assertEqual(resp.status_code, 200)

    def test_create_application(self):
        resp = self.client.post(reverse('kredensial:application_create'), {
            'nakes': self.nakes.pk,
            'jenis': 'awal',
            'tanggal_pengajuan': '2026-10-28',
            'lingkup_kewenangan_diminta': 'Tes',
        })
        self.assertEqual(resp.status_code, 302)
        app = CredentialApplication.objects.get(nakes=self.nakes)
        self.assertEqual(app.profesi_snapshot, self.profesi)
        self.assertEqual(app.unit_kerja_snapshot, 'Lab')
        self.assertTrue(app.nomor_pengajuan.startswith('KRED-'))

    def test_application_detail_ok(self):
        app = CredentialApplication.objects.create(
            nomor_pengajuan='KRED-VIEW-001', nakes=self.nakes,
            profesi_snapshot=self.profesi, unit_kerja_snapshot='Lab',
            jenis='awal', diajukan_oleh=self.user,
        )
        resp = self.client.get(reverse('kredensial:application_detail', args=[app.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_verifikator_cannot_create_application(self):
        verif = User.objects.create_user(username='verif', password='x')
        make_group('verifikator')
        verif.groups.add(Group.objects.get(name=ROLE_GROUPS['verifikator']))
        c = Client()
        c.login(username='verif', password='x')
        resp = c.get(reverse('kredensial:application_create'))
        self.assertEqual(resp.status_code, 403)

    def test_document_upload_versioning(self):
        app = CredentialApplication.objects.create(
            nomor_pengajuan='KRED-VIEW-002', nakes=self.nakes,
            profesi_snapshot=self.profesi, unit_kerja_snapshot='Lab',
            jenis='awal', diajukan_oleh=self.user,
        )
        req = CredentialRequirement.objects.create(
            profesi=self.profesi, kategori='str', nama_syarat='STR Asli', wajib=True,
        )
        f = SimpleUploadedFile('str.pdf', b'%PDF-1.4 test', content_type='application/pdf')
        resp = self.client.post(reverse('kredensial:document_upload', args=[app.pk]), {
            'requirement': req.pk, 'nama_file': 'str.pdf', 'file': f,
        })
        self.assertEqual(resp.status_code, 302)
        doc = CredentialDocument.objects.get(application=app)
        self.assertEqual(doc.versi, 1)
        self.assertTrue(doc.is_versi_aktif)

        # Upload ulang → versi 2, versi 1 nonaktif
        f2 = SimpleUploadedFile('str2.pdf', b'%PDF-1.4 test2', content_type='application/pdf')
        self.client.post(reverse('kredensial:document_upload', args=[app.pk]), {
            'requirement': req.pk, 'nama_file': 'str2.pdf', 'file': f2,
        })
        docs = CredentialDocument.objects.filter(application=app).order_by('versi')
        self.assertEqual(docs.count(), 2)
        self.assertFalse(docs[0].is_versi_aktif)
        self.assertTrue(docs[1].is_versi_aktif)

    def test_demo_user_cannot_download(self):
        demo = User.objects.create_user(username='demo', password='x')
        app = CredentialApplication.objects.create(
            nomor_pengajuan='KRED-VIEW-003', nakes=self.nakes,
            profesi_snapshot=self.profesi, unit_kerja_snapshot='Lab',
            jenis='awal', diajukan_oleh=demo,
        )
        req = CredentialRequirement.objects.create(
            profesi=self.profesi, kategori='str', nama_syarat='STR', wajib=True,
        )
        doc = CredentialDocument.objects.create(
            application=app, requirement=req, nama_file='x.pdf', versi=1,
        )
        c = Client()
        c.login(username='demo', password='x')
        resp = c.get(reverse('kredensial:document_download', args=[doc.pk]))
        self.assertEqual(resp.status_code, 403)

    def test_unauthorized_workflow_transition(self):
        plain = User.objects.create_user(username='plain', password='x')
        app = CredentialApplication.objects.create(
            nomor_pengajuan='KRED-VIEW-004', nakes=self.nakes,
            profesi_snapshot=self.profesi, unit_kerja_snapshot='Lab',
            jenis='awal', diajukan_oleh=plain,
        )
        c = Client()
        c.login(username='plain', password='x')
        resp = c.post(reverse('kredensial:application_transition', args=[app.pk, 'SUBMITTED']))
        # Redirect kembali dengan pesan error (bukan 500)
        self.assertEqual(resp.status_code, 302)
        app.refresh_from_db()
        self.assertEqual(app.workflow_state, 'DRAFT')

    def test_permission_helpers(self):
        sekretariat = User.objects.create_user(username='sek2', password='x')
        sekretariat.groups.add(Group.objects.get(name=ROLE_GROUPS['sekretariat']))
        self.assertTrue(user_can(sekretariat, 'create_application'))
        self.assertFalse(user_can(sekretariat, 'approve'))
        self.assertTrue(user_can_transition(sekretariat, 'DRAFT', 'SUBMITTED'))
        self.assertFalse(user_can_transition(sekretariat, 'PENDING_FINAL_DECISION', 'APPROVED'))


class KredensialAssessmentTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.asesor = User.objects.create_user(username='asesor', password='x')
        make_group('asesor')
        self.asesor.groups.add(Group.objects.get(name=ROLE_GROUPS['asesor']))
        self.client.login(username='asesor', password='x')

        self.subkomite = User.objects.create_user(username='subkomite', password='x')
        make_group('subkomite')
        self.subkomite.groups.add(Group.objects.get(name=ROLE_GROUPS['subkomite']))

        self.profesi, _ = Profesi.objects.get_or_create(nama='Radiografer')
        self.nakes = Nakes.objects.create(
            nama='Andi Wijaya', profesi=self.profesi, unit_kerja='Radiologi',
            no_str='STR-ASESMEN-1', masa_berlaku_str='2027-01-01',
            no_sip='SIP-ASESMEN-1', masa_berlaku_sip='2027-01-01',
            created_by=self.asesor,
        )
        self.app = CredentialApplication.objects.create(
            nomor_pengajuan='KRED-ASESMEN-001', nakes=self.nakes,
            profesi_snapshot=self.profesi, unit_kerja_snapshot='Radiologi',
            jenis='awal', diajukan_oleh=self.asesor, workflow_state='UNDER_ASSESSMENT',
        )
        self.privilege = ClinicalPrivilege.objects.create(
            kode='RAD-01', profesi=self.profesi, nama='Foto Toraks',
        )
        self.rp = RequestedPrivilege.objects.create(
            application=self.app, privilege=self.privilege,
        )

    def test_create_assessment(self):
        resp = self.client.post(reverse('kredensial:assessment_create', args=[self.app.pk]), {
            'metode': 'observasi', 'tanggal_asesmen': '2026-10-28',
            'ruang_lingkup': 'Foto toraks', 'status': 'berlangsung',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(CompetencyAssessment.objects.filter(application=self.app).count(), 1)

    def test_assessment_result_and_complete(self):
        a = CompetencyAssessment.objects.create(
            application=self.app, asesor=self.asesor, metode='observasi',
            tanggal_asesmen='2026-10-28', status='berlangsung',
        )
        resp = self.client.post(reverse('kredensial:assessment_result_add', args=[a.pk]), {
            'kompetensi': 'Foto toraks', 'hasil': 'kompeten',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(a.results.count(), 1)

        resp = self.client.post(reverse('kredensial:assessment_complete', args=[a.pk]))
        a.refresh_from_db()
        self.assertEqual(a.status, 'selesai')

    def test_asesor_cannot_recommend(self):
        resp = self.client.get(reverse('kredensial:recommendation_edit', args=[self.rp.pk]))
        self.assertEqual(resp.status_code, 403)

    def test_subkomite_can_recommend(self):
        c = Client()
        c.login(username='subkomite', password='x')
        resp = c.post(reverse('kredensial:recommendation_edit', args=[self.rp.pk]), {
            'keputusan': 'supervisi',
            'kebutuhan_supervisi': 'Dengan radiolog senior',
            'dasar_pertimbangan': 'Asesmen observasi kompeten',
        })
        self.assertEqual(resp.status_code, 302)
        rec = PrivilegeRecommendation.objects.get(requested_privilege=self.rp)
        self.assertEqual(rec.keputusan, 'supervisi')
        self.assertEqual(rec.direkomendasikan_oleh, self.subkomite)

    def test_recommendation_does_not_grant_privilege(self):
        PrivilegeRecommendation.objects.create(
            requested_privilege=self.rp, keputusan='direkomendasikan',
            direkomendasikan_oleh=self.subkomite,
        )
        self.assertFalse(GrantedPrivilege.objects.exists())

    def test_committee_review_endorse(self):
        c = Client()
        c.login(username='subkomite', password='x')
        resp = c.post(reverse('kredensial:review_create', args=[self.app.pk]), {
            'catatan': 'Disetujui komite', 'disetujui': 'on',
        })
        self.assertEqual(resp.status_code, 302)
        review = CredentialReview.objects.get(application=self.app)
        self.assertTrue(review.disetujui)

    def test_privilege_catalog_crud(self):
        admin = User.objects.create_user(username='adm', password='x', is_superuser=True)
        c = Client()
        c.login(username='adm', password='x')
        resp = c.get(reverse('kredensial:privilege_list'))
        self.assertEqual(resp.status_code, 200)
        resp = c.post(reverse('kredensial:privilege_create'), {
            'kode': 'RAD-02', 'profesi': self.profesi.pk, 'nama': 'USG Abdomen',
            'versi_kebijakan': '1.0',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(ClinicalPrivilege.objects.filter(kode='RAD-02').exists())


class KredensialAppointmentTest(TestCase):
    def setUp(self):
        self.pejabat = User.objects.create_user(username='pejabat', password='x')
        make_group('pejabat')
        self.pejabat.groups.add(Group.objects.get(name=ROLE_GROUPS['pejabat']))
        self.subkomite = User.objects.create_user(username='subk', password='x')
        make_group('subkomite')
        self.subkomite.groups.add(Group.objects.get(name=ROLE_GROUPS['subkomite']))

        self.profesi, _ = Profesi.objects.get_or_create(nama='Fisioterapis')
        self.nakes = Nakes.objects.create(
            nama='Dewi Lestari', profesi=self.profesi, unit_kerja='Fisioterapi',
            no_str='STR-SPK-1', masa_berlaku_str='2027-01-01',
            no_sip='SIP-SPK-1', masa_berlaku_sip='2027-01-01',
            created_by=self.pejabat,
        )
        self.app = CredentialApplication.objects.create(
            nomor_pengajuan='KRED-SPK-001', nakes=self.nakes,
            profesi_snapshot=self.profesi, unit_kerja_snapshot='Fisioterapi',
            jenis='awal', diajukan_oleh=self.pejabat,
            workflow_state='PENDING_FINAL_DECISION',
        )
        self.privilege = ClinicalPrivilege.objects.create(
            kode='FIS-01', profesi=self.profesi, nama='Terapi Latihan',
        )
        self.rp = RequestedPrivilege.objects.create(
            application=self.app, privilege=self.privilege,
        )
        self.rec = PrivilegeRecommendation.objects.create(
            requested_privilege=self.rp, keputusan='direkomendasikan',
            direkomendasikan_oleh=self.subkomite,
        )

    def _valid_data(self, nomor='SPK-001'):
        return {
            'nomor_spk': nomor,
            'tanggal_terbit': '2026-10-28',
            'tanggal_mulai_berlaku': '2026-11-01',
            'tanggal_akhir_berlaku': '2028-10-31',
            'keputusan': 'disetujui',
            'lokasi_penugasan': 'Instalasi Fisioterapi',
        }

    def test_unauthorized_approval_blocked(self):
        c = Client()
        c.login(username='subk', password='x')
        resp = c.get(reverse('kredensial:appointment_create', args=[self.app.pk]))
        self.assertEqual(resp.status_code, 403)

    def test_finalize_appointment(self):
        c = Client()
        c.login(username='pejabat', password='x')
        data = self._valid_data()
        data[f'grant_{self.rp.pk}'] = 'on'
        data[f'redaksi_{self.rp.pk}'] = 'Terapi latihan dasar'
        resp = c.post(reverse('kredensial:appointment_create', args=[self.app.pk]), data)
        self.assertEqual(resp.status_code, 302)
        appt = ClinicalAppointment.objects.get(application=self.app)
        self.assertTrue(appt.is_final)
        self.assertEqual(appt.pejabat_berwenang, self.pejabat)
        self.assertEqual(appt.granted_privileges.count(), 1)
        granted = appt.granted_privileges.first()
        self.assertEqual(granted.status, 'active')
        self.assertEqual(granted.redaksi_final, 'Terapi latihan dasar')

    def test_duplicate_spk_number_rejected(self):
        appointment_service.finalize_appointment(
            self.app, self._valid_data('SPK-DUP'),
            [{'requested_privilege_id': self.rp.pk, 'approved': True}],
            self.pejabat,
        )
        app2 = CredentialApplication.objects.create(
            nomor_pengajuan='KRED-SPK-002', nakes=self.nakes,
            profesi_snapshot=self.profesi, unit_kerja_snapshot='Fisioterapi',
            jenis='awal', diajukan_oleh=self.pejabat,
            workflow_state='PENDING_FINAL_DECISION',
        )
        rp2 = RequestedPrivilege.objects.create(application=app2, privilege=self.privilege)
        PrivilegeRecommendation.objects.create(
            requested_privilege=rp2, keputusan='direkomendasikan',
            direkomendasikan_oleh=self.subkomite,
        )
        with self.assertRaises(ValidationError):
            appointment_service.finalize_appointment(
                app2, self._valid_data('SPK-DUP'),
                [{'requested_privilege_id': rp2.pk, 'approved': True}],
                self.pejabat,
            )

    def test_invalid_date_range_rejected(self):
        data = self._valid_data('SPK-BADDATE')
        data['tanggal_akhir_berlaku'] = '2026-01-01'  # sebelum mulai
        with self.assertRaises(ValidationError):
            appointment_service.finalize_appointment(
                self.app, data,
                [{'requested_privilege_id': self.rp.pk, 'approved': True}],
                self.pejabat,
            )

    def test_duplicate_finalization_blocked(self):
        appointment_service.finalize_appointment(
            self.app, self._valid_data('SPK-IDEM'),
            [{'requested_privilege_id': self.rp.pk, 'approved': True}],
            self.pejabat,
        )
        with self.assertRaises(ValidationError):
            appointment_service.finalize_appointment(
                self.app, self._valid_data('SPK-IDEM-2'),
                [{'requested_privilege_id': self.rp.pk, 'approved': True}],
                self.pejabat,
            )
        self.assertEqual(ClinicalAppointment.objects.filter(application=self.app).count(), 1)

    def test_privilege_without_recommendation_rejected(self):
        priv2 = ClinicalPrivilege.objects.create(
            kode='FIS-02', profesi=self.profesi, nama='Terapi Manual',
        )
        rp2 = RequestedPrivilege.objects.create(application=self.app, privilege=priv2)
        with self.assertRaises(ValidationError):
            appointment_service.finalize_appointment(
                self.app, self._valid_data('SPK-NOREC'),
                [{'requested_privilege_id': rp2.pk, 'approved': True}],
                self.pejabat,
            )

    def test_granted_status_change_logged(self):
        appt = appointment_service.finalize_appointment(
            self.app, self._valid_data('SPK-SUSPEND'),
            [{'requested_privilege_id': self.rp.pk, 'approved': True}],
            self.pejabat,
        )
        granted = appt.granted_privileges.first()
        events_before = CredentialEvent.objects.filter(
            application=self.app, aksi='perubahan_kewenangan',
        ).count()
        appointment_service.change_granted_status(
            granted, 'suspended', self.pejabat, 'Temuan OPPE grade K',
        )
        granted.refresh_from_db()
        self.assertEqual(granted.status, 'suspended')
        events_after = CredentialEvent.objects.filter(
            application=self.app, aksi='perubahan_kewenangan',
        ).count()
        self.assertEqual(events_after, events_before + 1)

    def test_appointment_detail_and_print(self):
        appt = appointment_service.finalize_appointment(
            self.app, self._valid_data('SPK-PRINT'),
            [{'requested_privilege_id': self.rp.pk, 'approved': True}],
            self.pejabat,
        )
        c = Client()
        c.login(username='pejabat', password='x')
        resp = c.get(reverse('kredensial:appointment_detail', args=[self.app.pk]))
        self.assertEqual(resp.status_code, 200)
        resp = c.get(reverse('kredensial:appointment_print', args=[self.app.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_demo_cannot_access_appointment(self):
        demo = User.objects.create_user(username='demo', password='x')
        appt = appointment_service.finalize_appointment(
            self.app, self._valid_data('SPK-DEMO'),
            [{'requested_privilege_id': self.rp.pk, 'approved': True}],
            self.pejabat,
        )
        c = Client()
        c.login(username='demo', password='x')
        resp = c.get(reverse('kredensial:appointment_download', args=[appt.pk, 'spk']))
        self.assertEqual(resp.status_code, 403)


class KredensialMonitoringTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='monitor', password='x')
        make_group('auditor')
        self.user.groups.add(Group.objects.get(name=ROLE_GROUPS['auditor']))
        self.pejabat = User.objects.create_user(username='pejabat2', password='x')
        make_group('pejabat')
        self.pejabat.groups.add(Group.objects.get(name=ROLE_GROUPS['pejabat']))
        self.client.login(username='monitor', password='x')

        self.profesi, _ = Profesi.objects.get_or_create(nama='Apoteker')
        self.nakes = Nakes.objects.create(
            nama='Rina Kusuma', profesi=self.profesi, unit_kerja='Farmasi',
            no_str='STR-MON-1', masa_berlaku_str='2027-01-01',
            no_sip='SIP-MON-1', masa_berlaku_sip='2027-01-01',
            created_by=self.user,
        )
        self.app = CredentialApplication.objects.create(
            nomor_pengajuan='KRED-MON-001', nakes=self.nakes,
            profesi_snapshot=self.profesi, unit_kerja_snapshot='Farmasi',
            jenis='awal', diajukan_oleh=self.user, workflow_state='CLOSED',
            status='Selesai',
        )
        self.privilege = ClinicalPrivilege.objects.create(
            kode='FAR-01', profesi=self.profesi, nama='Dispensing Obat',
        )
        self.rp = RequestedPrivilege.objects.create(
            application=self.app, privilege=self.privilege,
        )
        PrivilegeRecommendation.objects.create(
            requested_privilege=self.rp, keputusan='direkomendasikan',
            direkomendasikan_oleh=self.user,
        )

    def _finalize(self, nomor='SPK-MON-001', end='2027-12-31', target=None):
        return appointment_service.finalize_appointment(
            self.app,
            {
                'nomor_spk': nomor, 'tanggal_terbit': '2026-01-01',
                'tanggal_mulai_berlaku': '2026-01-01',
                'tanggal_akhir_berlaku': end, 'keputusan': 'disetujui',
                'target_rekredensial': target,
            },
            [{'requested_privilege_id': self.rp.pk, 'approved': True}],
            self.pejabat,
        )

    def test_monitoring_dashboard(self):
        self._finalize()
        resp = self.client.get(reverse('kredensial:monitoring'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'SPK-MON-001')

    def test_expiration_detection(self):
        self._finalize(nomor='SPK-EXP', end='2026-06-30')
        resp = self.client.get(reverse('kredensial:monitoring'))
        self.assertContains(resp, 'SPK-EXP')
        appt = ClinicalAppointment.objects.get(nomor_spk='SPK-EXP')
        self.assertTrue(appt.is_expired)

    def test_credential_history(self):
        self._finalize()
        resp = self.client.get(reverse('kredensial:history', args=[self.nakes.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Rina Kusuma')
        self.assertContains(resp, 'Dispensing Obat')

    def test_followup_create_and_overdue(self):
        resp = self.client.post(reverse('kredensial:followup_create', args=[self.app.pk]), {
            'temuan': 'Keterlambatan input resep',
            'rekomendasi_tindakan': 'Pelatihan ulang',
            'penanggung_jawab': 'Apoteker Senior',
            'tanggal_target': '2026-01-15',
            'status': 'belum',
        })
        self.assertEqual(resp.status_code, 302)
        f = CredentialFollowUp.objects.get(application=self.app)
        self.assertTrue(f.is_overdue)

    def test_recredential_creates_new_cycle(self):
        self._finalize(nomor='SPK-REKRED')
        sek = User.objects.create_user(username='sek3', password='x')
        make_group('sekretariat')
        sek.groups.add(Group.objects.get(name=ROLE_GROUPS['sekretariat']))
        c = Client()
        c.login(username='sek3', password='x')
        resp = c.post(reverse('kredensial:recredential_create', args=[self.app.pk]), {
            'nakes': self.nakes.pk,
            'jenis': 'berkala',
            'tanggal_pengajuan': '2026-10-28',
            'previous_cycle': self.app.pk,
        })
        self.assertEqual(resp.status_code, 302)
        new_app = CredentialApplication.objects.get(previous_cycle=self.app)
        self.assertEqual(new_app.jenis, 'berkala')
        self.assertNotEqual(new_app.pk, self.app.pk)
        # Siklus lama tetap utuh
        self.app.refresh_from_db()
        self.assertEqual(self.app.workflow_state, 'CLOSED')
        self.assertTrue(ClinicalAppointment.objects.filter(application=self.app).exists())

    def test_oppe_link_in_followup(self):
        oppe = EvaluasiOPPE.objects.create(
            nakes=self.nakes, tahun=2026, tanggal_evaluasi='2026-06-01',
            created_by=self.user,
        )
        resp = self.client.post(reverse('kredensial:followup_create', args=[self.app.pk]), {
            'temuan': 'OPPE grade K', 'oppe_terkait': oppe.pk,
            'status': 'proses',
        })
        self.assertEqual(resp.status_code, 302)
        f = CredentialFollowUp.objects.get(application=self.app)
        self.assertEqual(f.oppe_terkait, oppe)

    def test_history_preserves_superseded_decisions(self):
        appt1 = self._finalize(nomor='SPK-OLD', end='2026-12-31')
        # Ubah status granted → superseded (keputusan lama tetap tercatat)
        granted = appt1.granted_privileges.first()
        appointment_service.change_granted_status(
            granted, 'superseded', self.user, 'Digantikan SPK baru',
        )
        resp = self.client.get(reverse('kredensial:history', args=[self.nakes.pk]))
        self.assertContains(resp, 'SPK-OLD')
        self.assertContains(resp, 'Digantikan')
