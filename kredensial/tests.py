"""Smoke test: model creation, workflow transitions, event history."""
from django.test import TestCase
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.utils import timezone

from nakes.models import Nakes, Profesi
from kredensial.models import (
    CredentialRequirement, CredentialApplication, CredentialDocument,
    DocumentVerification, CredentialEvent,
)
from kredensial.services import workflow


class KredensialSmokeTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='x', is_superuser=True)
        self.profesi, _ = Profesi.objects.get_or_create(nama='ATLM')
        self.nakes = Nakes.objects.create(
            nama='Budi Santoso', profesi=self.profesi, unit_kerja='Lab',
            no_str='STR-SMOKE-1', masa_berlaku_str='2027-01-01',
            no_sip='SIP-SMOKE-1', masa_berlaku_sip='2027-01-01',
            created_by=self.user,
        )
        self.req = CredentialRequirement.objects.create(
            profesi=self.profesi, kategori='str', nama_syarat='STR Asli', wajib=True,
        )
        self.app = CredentialApplication.objects.create(
            nomor_pengajuan='KRED-SMOKE-001', nakes=self.nakes,
            profesi_snapshot=self.profesi, unit_kerja_snapshot='Lab',
            jenis='awal', diajukan_oleh=self.user,
        )

    def test_model_creation(self):
        self.assertEqual(self.app.workflow_state, 'DRAFT')
        self.assertEqual(self.app.nakes.nama, 'Budi Santoso')
        self.assertEqual(str(self.req), 'STR Asli (ATLM)')

    def test_transition_draft_to_submitted(self):
        event = workflow.transition(self.app, 'SUBMITTED', self.user)
        self.assertIsNotNone(event)
        self.app.refresh_from_db()
        self.assertEqual(self.app.workflow_state, 'SUBMITTED')
        self.assertEqual(CredentialEvent.objects.count(), 1)

    def test_illegal_transition_blocked(self):
        with self.assertRaises(ValidationError):
            workflow.transition(self.app, 'APPROVED', self.user)

    def test_idempotent_transition(self):
        workflow.transition(self.app, 'SUBMITTED', self.user)
        event2 = workflow.transition(self.app, 'SUBMITTED', self.user)
        self.assertIsNone(event2)
        self.assertEqual(CredentialEvent.objects.count(), 1)

    def test_verification_requires_valid_document(self):
        workflow.transition(self.app, 'SUBMITTED', self.user)
        workflow.transition(self.app, 'UNDER_VERIFICATION', self.user)
        # Belum ada dokumen → gagal
        with self.assertRaises(ValidationError):
            workflow.transition(self.app, 'VERIFIED', self.user)
        # Upload + verifikasi valid → berhasil
        doc = CredentialDocument.objects.create(
            application=self.app, requirement=self.req, nama_file='str.pdf',
            versi=1, uploaded_by=self.user,
        )
        DocumentVerification.objects.create(
            document=doc, hasil='valid', diverifikasi_oleh=self.user,
        )
        event = workflow.transition(self.app, 'VERIFIED', self.user)
        self.assertIsNotNone(event)
        self.app.refresh_from_db()
        self.assertEqual(self.app.workflow_state, 'VERIFIED')

    def test_event_append_only(self):
        event = workflow.transition(self.app, 'SUBMITTED', self.user)
        with self.assertRaises(ValidationError):
            event.catatan = 'changed'
            event.save()
        with self.assertRaises(ValidationError):
            event.delete()

    def test_unauthorized_role_blocked(self):
        plain = User.objects.create_user(username='plain', password='x')
        with self.assertRaises(ValidationError):
            workflow.transition(self.app, 'SUBMITTED', plain)
