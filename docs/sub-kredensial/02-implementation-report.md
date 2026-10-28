# Implementasi Modul Sub. Kredensial — Laporan Akhir

## 1. Ringkasan Implementasi

Modul `kredensial` telah diimplementasikan penuh sebagai Django app terpisah
yang terintegrasi dengan app `nakes` existing. Branch: `feature/sub-kredensial`.

Cakupan yang selesai:
- Pengajuan & verifikasi dokumen (dengan versioning & riwayat verifikasi)
- Asesmen kompetensi (multi-metode, multi-asesor)
- Rekomendasi RKK per kewenangan (subkomite)
- Penetapan SPK/RKK (pejabat berwenang, snapshot kewenangan)
- Monitoring, rekam jejak, follow-up, dan rekredensial
- Role-based access control server-side
- Audit trail immutable (`CredentialEvent`)
- 32 automated tests, semua lulus

## 2. Model Database yang Dibuat

| Model | Fungsi |
|---|---|
| `CredentialRequirement` | Master syarat dokumen per profesi (versioned) |
| `CredentialApplication` | Master pengajuan + siklus kredensial |
| `CredentialDocument` | Dokumen unggahan + versioning |
| `DocumentVerification` | Hasil verifikasi (append-only history) |
| `CompetencyAssessment` | Sesi asesmen (6 metode) |
| `AssessmentResult` | Hasil per kompetensi |
| `ClinicalPrivilege` | Katalog kewenangan per profesi |
| `RequestedPrivilege` | Kewenangan yang diminta |
| `PrivilegeRecommendation` | Rekomendasi subkomite + kondisi |
| `CredentialReview` | Endorsement komite |
| `ClinicalAppointment` | SPK — keputusan final |
| `GrantedPrivilege` | Snapshot kewenangan efektif |
| `CredentialFollowUp` | Temuan monitoring + tindak lanjut |
| `CredentialEvent` | Riwayat workflow immutable |

## 3. Migrations

- `kredensial/migrations/0001_initial.py` — semua model + index + constraint

## 4. Routes dan Template

Routes (`kredensial/urls.py`, prefix `/kredensial/`):

| Route | Nama |
|---|---|
| `/` | `dashboard` |
| `/pengajuan/` | `application_list` |
| `/pengajuan/tambah/` | `application_create` |
| `/pengajuan/<pk>/` | `application_detail` |
| `/pengajuan/<pk>/edit/` | `application_update` |
| `/pengajuan/<pk>/transisi/<state>/` | `application_transition` |
| `/pengajuan/<pk>/dokumen/upload/` | `document_upload` |
| `/dokumen/<pk>/download/` | `document_download` |
| `/dokumen/<pk>/verifikasi/` | `document_verify` |
| `/pengajuan/<pk>/asesmen/tambah/` | `assessment_create` |
| `/asesmen/<pk>/hasil/tambah/` | `assessment_result_add` |
| `/asesmen/<pk>/selesai/` | `assessment_complete` |
| `/pengajuan/<pk>/kewenangan/tambah/` | `requested_privilege_add` |
| `/rekomendasi/<pk>/` | `recommendation_edit` |
| `/pengajuan/<pk>/review/` | `review_create` |
| `/pengajuan/<pk>/spk/tetapkan/` | `appointment_create` |
| `/pengajuan/<pk>/spk/` | `appointment_detail` |
| `/spk/<pk>/dokumen/` | `appointment_document_upload` |
| `/spk/<pk>/unduh/<type>/` | `appointment_download` |
| `/spk/<pk>/cetak/` | `appointment_print` |
| `/monitoring/` | `monitoring` |
| `/riwayat/<nakes_pk>/` | `history` |
| `/pengajuan/<pk>/tindak-lanjut/tambah/` | `followup_create` |
| `/tindak-lanjut/<pk>/edit/` | `followup_update` |
| `/pengajuan/<pk>/rekredensial/` | `recredential_create` |
| `/master/syarat/` | `requirement_list` |
| `/master/kewenangan/` | `privilege_list` |

Template (`templates/kredensial/`): dashboard, application_list, application_form,
application_detail (stepper), document_upload, verification, requirement_list,
requirement_form, assessment_form, assessment_result_form,
requested_privilege_form, recommendation_form, review_form, privilege_list,
privilege_form, appointment_form, appointment_detail, appointment_document,
appointment_print, monitoring, history, followup_form — 22 template.

## 5. File Existing yang Dimodifikasi

| File | Perubahan |
|---|---|
| `config/settings.py` | Tambah `'kredensial'` ke INSTALLED_APPS |
| `config/urls.py` | Include `kredensial.urls` di `/kredensial/` |
| `templates/includes/sidebar_nav.html` | Section "Sub. Kredensial" (4 menu) |

## 6. Transisi Workflow yang Diimplementasikan

```
DRAFT → SUBMITTED → UNDER_VERIFICATION
                      ↓ (bukti: semua dokumen wajib valid)
                REVISION_REQUIRED → RESUBMITTED → UNDER_VERIFICATION
                      ↓
                  VERIFIED → UNDER_ASSESSMENT → ASSESSMENT_COMPLETED
                      ↓ (bukti: minimal 1 asesmen selesai)
              RECOMMENDATION_REVIEW → RECOMMENDED
                      ↓ (bukti: semua requested privilege punya rekomendasi)
              PENDING_FINAL_DECISION
                      ↓ (bukti: endorsement komite)
              ┌───────────┼───────────┐
              ↓           ↓           ↓
        RETURNED_FOR_  REJECTED    APPROVED
          REVISION                  ↓ (bukti: appointment valid)
                            DOCUMENT_ISSUED → CLOSED
```

Setiap transisi: cek state machine, cek role, cek bukti, `@transaction.atomic`,
idempoten, dan menulis `CredentialEvent`.

## 7. Role Permissions

9 role via Django Group: Administrator, Sekretariat, Verifikator, Asesor,
Subkomite, Ketua Komite, Pejabat Berwenang, Auditor, Demo.

- `kredensial/permissions.py` — `ROLE_GROUPS`, `ROLE_ACTIONS`, `TRANSITION_ROLES`
- Decorator `@kredensial_role_required('approve')` pada setiap view mutable
- Demo user: middleware existing blok POST; download dokumen ditolak 403
- Superuser selalu lolos

## 8. Integrasi OPPE

- `EvaluasiOPPE` dibaca read-only (tidak dihitung ulang)
- Ditampilkan di application detail dan credential history
- `CredentialFollowUp.oppe_terkait` — asosiasi eksplisit OPPE ke siklus
- Tidak ada pencabutan/pemberian kewenangan otomatis berdasarkan grade OPPE

## 9. Hasil Automated Test

```
Ran 32 tests in ~60s — OK
```

Kelompok test:
- Workflow: transisi legal/ilegal, idempotensi, bukti wajib, event append-only
- View: CRUD, RBAC (403 untuk role salah), demo isolation
- Assessment: multi-metode, completion, isolasi asesor↔rekomendasi
- Recommendation: rekomendasi tidak memberi kewenangan, endorsement komite
- Approval: otorisasi, duplikat nomor SPK, rentang tanggal invalid,
  duplikasi finalisasi, privilege tanpa rekomendasi, audit perubahan status
- Monitoring: deteksi kedaluwarsa, riwayat, follow-up overdue,
  rekredensial siklus baru, keputusan lama tetap terjaga
- Existing suite `nakes`: 27 test lulus (tidak ada regresi)

## 10. Keterbatasan yang Diketahui

1. **PDF generation** — belum ada generator PDF server-side. MVP memakai
   template print-friendly (`appointment_print.html`) + unggah dokumen
   bertandatangan. Perlu library tambahan (mis. WeasyPrint) jika PDF
   otomatis diinginkan.
2. **Tanda tangan elektronik** — tidak diimplementasikan (sesuai blueprint).
   Sistem hanya menyimpan metadata dan dokumen hasil unggahan.
3. **Katalog kewenangan bersifat acuan awal** — 47 entri untuk 17 profesi
   sudah diseed, namun administrator RS WAJIB meninjau dan menyesuaikan
   dengan SOP serta regulasi internal sebelum digunakan operasional.

## 11. Persyaratan Kebijakan RS yang Belum Diresolusi

1. Interval rekredensial berkala per profesi (default: flag manual)
2. Kewenangan penandatangan SPK per tingkat jabatan
3. Apakah endorsement Ketua Komite wajib sebelum keputusan final
4. Masa berlaku default SPK per profesi
5. Daftar kewenangan klinis aktual per profesi (katalog masih kosong —
   harus diisi administrator dari regulasi tervalidasi)

## 12. Tindak Lanjut yang Sudah Dilakukan

1. **Group role dibuat otomatis** — `seed_kredensial_master` membuat 8 group
   role secara idempoten; juga dipanggil dari `seed_data`.
2. **Katalog kewenangan diseed** — 47 entri untuk 17 profesi
   (`seed_kredensial_master`), dengan peringatan agar ditinjau administrator.
3. **Master syarat dokumen diseed** — 131 entri dengan referensi regulasi
   (UU 17/2023, Permenkes 13/2025, Permenkes 6/2026) dan pembeda profesi
   wajib SIP vs teknis.
4. **Akun demo per role dibuat** — `seed_kredensial_accounts` membuat 7 akun
   (kred_sekretariat, kred_verifikator, kred_asesor, kred_subkomite,
   kred_ketua, kred_pejabat, kred_auditor) dengan group assignment.
   Password default `Kredensial@123` (ubah via `--password` atau env
   `KREDENSIAL_DEMO_PASSWORD`).
5. **Sinkronisasi ringkasan Nakes diimplementasikan** —
   `kredensial/services/summary_sync.py` menurunkan `status_kredensial` dan
   `kewenangan_klinis` dari keputusan final. Dipanggil otomatis setelah
   finalisasi SPK dan perubahan status kewenangan, serta manual via
   `manage.py sync_nakes_kredensial` (ada `--dry-run`).
6. **Deployment chain diperbarui** — `build.sh` dan `railway.toml`
   preDeploy menjalankan `seed_kredensial_master`,
   `seed_kredensial_accounts`, dan `sync_nakes_kredensial`.

## 13. Rekomendasi Tindak Lanjut Berikutnya

1. **Tinjau katalog kewenangan** — administrator RS harus memvalidasi 47
   entri terhadap SOP dan regulasi internal sebelum operasional.
2. **Tetapkan kebijakan** — interval rekredensial, masa berlaku SPK,
   hierotoris penandatangan.
3. **Ganti password akun demo** setelah pengujian selesai.
4. **PDF otomatis** — evaluasi WeasyPrint/ReportLab untuk SPK draft.
5. **Backfill summary** — jalankan `manage.py sync_nakes_kredensial`
   setelah ada data kredensial produksi.
