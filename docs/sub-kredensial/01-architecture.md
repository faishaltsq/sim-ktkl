# Arsitektur Modul Sub. Kredensial SIM-KTKL

## 1. Ringkasan

Modul `kredensial` mengelola siklus kredensial tenaga kesehatan non-dokter
(ATLM, Radiografer, Fisioterapis, Apoteker, Nutrisionis, Elektromedis,
Perekam Medis, dll.) di RS PKU Muhammadiyah Gombong, dari pengajuan,
verifikasi dokumen, asesmen kompetensi, rekomendasi RKK, penetapan SPK/RKK,
hingga monitoring dan rekredensial.

Modul ini berdiri sendiri sebagai Django app (`kredensial/`) yang terintegrasi
dengan model existing di app `nakes`:
- `Nakes` — referensi personel (tidak diduplikasi)
- `Profesi` — referensi profesi
- `DokumenNakes` — dokumen personel existing
- `EvaluasiOPPE` — evaluasi praktik berkelanjutan (read-only dari modul ini)
- `AuditLog` — audit trail existing

## 2. Temuan Repository (Discovery)

| Item | Temuan |
|---|---|
| Auth | Django `auth.User` default, tanpa custom user model |
| App structure | Flat: `nakes/`, `accounts/`, `config/` |
| Templates | `templates/<app>/` di project root, extend `base.html` |
| Design system | CSS variables di `base.html` (`--primary: #0284C7`, PKU green `#0D7A53`, Inter + Plus Jakarta Sans, Bootstrap 5.3.3, Bootstrap Icons 1.11.3) |
| Sidebar | `templates/includes/sidebar_nav.html`, struktur `nav-section` + `nav-link` dengan `nav-icon`/`nav-text` |
| Demo user | Middleware `ReadOnlyDemoMiddleware` blok semua POST dari user `demo` |
| DB | SQLite lokal, PostgreSQL produksi via `DATABASE_URL` |
| Migrations | `nakes/migrations/0006_*` terakhir |
| Tests | `nakes/tests.py` — `TestCase` + `Client`, login via `create_user` |
| Storage | Supabase Storage (`nakes/storage.py`) untuk file permanen |

## 3. Skema Database (Model)

```
kredensial/
├── CredentialRequirement      # Master syarat dokumen per profesi (versioned)
├── CredentialApplication      # Master pengajuan + siklus kredensial
├── CredentialDocument         # Dokumen yang diunggah + versi
├── DocumentVerification       # Hasil verifikasi per dokumen (immutable history)
├── CompetencyAssessment       # Sesi asesmen (wawancara, observasi, dll)
├── AssessmentResult           # Hasil per kompetensi/privilege
├── ClinicalPrivilege          # Master katalog kewenangan klinis per profesi
├── RequestedPrivilege         # Privilege yang diminta pemohon
├── PrivilegeRecommendation    # Rekomendasi per privilege + kondisi
├── CredentialReview           # Endorsement komite (jika diperlukan)
├── ClinicalAppointment        # SPK — keputusan final pejabat berwenang
├── GrantedPrivilege           # Snapshot privilege efektif (dari keputusan)
├── CredentialFollowUp         # Temuan monitoring + tindak lanjut
└── CredentialEvent            # Immutable workflow history
```

### Relationship Principles
- 1 Nakes → banyak CredentialApplication (siklus berurutan)
- 1 Application → banyak CredentialDocument → banyak DocumentVerification
- 1 Application → banyak CompetencyAssessment → banyak AssessmentResult
- 1 Application → banyak RequestedPrivilege → 1 PrivilegeRecommendation
- 1 ClinicalAppointment → banyak GrantedPrivilege (snapshot)
- Application.previous_cycle → CredentialApplication (self-FK, rekredensial)
- Setiap transisi state → CredentialEvent (append-only)

### Deletion Behavior
- `PROTECT` untuk keputusan historis (ClinicalAppointment, GrantedPrivilege)
- `CASCADE` untuk dokumen/asesmen yang milik aplikasi
- `SET_NULL` untuk referensi user (created_by, verified_by)

## 4. Workflow State Machine

```
DRAFT → SUBMITTED → UNDER_VERIFICATION
                        ↓
                  REVISION_REQUIRED → RESUBMITTED → UNDER_VERIFICATION
                        ↓
                    VERIFIED → UNDER_ASSESSMENT → ASSESSMENT_COMPLETED
                        ↓
              RECOMMENDATION_REVIEW → RECOMMENDED → PENDING_FINAL_DECISION
                        ↓
              ┌───────┼───────┐
              ↓       ↓       ↓
          RETURNED  REJECTED  APPROVED
          _FOR_REVISION              ↓
                              DOCUMENT_ISSUED → CLOSED
```

GrantedPrivilege status terpisah:
`PENDING → ACTIVE → (SUSPENDED | EXPIRED | REVOKED | SUPERSEDED)`

Transisi divalidasi di `services/workflow.py`:
- Server-side authorization (role check per transisi)
- Bukti wajib per transisi (dokumen lengkap, asesmen selesai, dll)
- `@transaction.atomic` + idempotency guard
- Setiap transisi → CredentialEvent (actor, timestamp, from, to, notes)

## 5. Role Permission Matrix

| Role | Create App | Verify Docs | Assess | Recommend | Approve | Monitor | Master |
|---|---|---|---|---|---|---|---|
| Administrator | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Sekretariat | ✓ | — | — | — | — | ✓ | — |
| Verifikator | — | ✓ | — | — | — | ✓ | — |
| Asesor | — | — | ✓ | — | — | ✓ | — |
| Subkomite Kredensial | — | — | — | ✓ | — | ✓ | — |
| Ketua Komite | — | — | — | ✓ (endorse) | — | ✓ | — |
| Pejabat Berwenang | — | — | — | — | ✓ | ✓ | — |
| Auditor | — | — | — | — | — | ✓ (read) | — |
| Demo | — | — | — | — | — | ✓ (read) | — |

Implementasi: `kredensial/permissions.py` dengan helper
`user_can_transition(user, from_state, to_state)` dan decorator
`@kredensial_role_required('verifikator', ...)`.

## 6. UI/UX

- Mengikuti design system existing (`base.html` CSS variables)
- Sidebar group baru: **Sub. Kredensial** di `sidebar_nav.html`
- Dashboard KPI: total pengajuan aktif, menunggu verifikasi/asesmen/keputusan, SPK mendekati kedaluwarsa
- Application detail: horizontal stepper (Pengajuan → Verifikasi → Asesmen → Rekomendasi → Penetapan → Monitoring)
- Templates di `templates/kredensial/`

## 7. Security

- Semua view `@login_required` + role check server-side
- File download: cek permission sebelum serve (tidak ada akses anonim)
- Demo user: middleware existing blok POST; GET juga dibatasi ke data sintetis
- Finalisasi keputusan: `@transaction.atomic`, cek authority, cegah duplicate SPK number
- Audit: setiap aksi penting → `CredentialEvent` + `AuditLog` existing

## 8. Catatan Regulasi

- Policy version dicatat per siklus (`CredentialApplication.policy_version`)
- Requirement configurable per profesi — tidak hardcode aturan usang
- STR/SIP existing di Nakes TIDAK dijadikan sumber kebenaran tunggal
- Rekredensial berkala: interval configurable (default flag untuk approval manusia)

## 9. Keputusan Desain

1. **App terpisah** (`kredensial/`) bukan menambah ke `nakes/` — isolation domain
2. **Models split** — `models.py` utama + import dari file domain jika terlalu besar
3. **Function-based views** — konsisten dengan `nakes/views.py`
4. **Crispy forms** — `CRISPY_TEMPLATE_PACK = 'bootstrap5'` sudah dikonfigurasi
5. **Tidak ada PDF generation dependency baru** — MVP pakai upload signed doc + print-friendly HTML template
6. **OPPE read-only** — tidak duplikasi/re-kalkulasi skor
