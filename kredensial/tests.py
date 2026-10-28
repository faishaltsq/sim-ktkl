"""Test integrasi Sub. Kredensial — views, permissions, security."""
from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from nakes.models import Nakes, Profesi
from kredensial.models import (
    CredentialRequirement, CredentialApplication, CredentialDocument,
    DocumentVerification,
)
from kredensial.permissions import ROLE_GROUPS, user_can, user_can_transition


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
