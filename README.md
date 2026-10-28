# SIM-KTKL — Sistem Informasi Manajemen Komite Tenaga Kesehatan Lainnya

Aplikasi web berbasis Django untuk mengelola data **Kredensial, Evaluasi, Etik & Disiplin, serta Sekretariat** Komite Tenaga Kesehatan Lainnya (KTKL) di rumah sakit.

## Fitur Utama

### 📋 Manajemen Tenaga Kesehatan (Nakes)
- CRUD data nakes: nama, profesi, unit kerja, STR/SIP & masa berlaku, status kredensial, kewenangan klinis
- Upload & download dokumen per nakes (STR, SIP, Sertifikat, dll.)
- Tracking sisa hari masa berlaku STR & SIP
- Import bulk data nakes via template Excel
- Export data ke Excel

### 📊 Evaluasi OPPE (Ongoing Professional Practice Evaluation)
- Penilaian 20 indikator: Perilaku (7), Pengembangan Profesional (4), Kinerja Klinik (9)
- Perhitungan otomatis total nilai, poin penilaian & grade (Baik / Cukup / Kurang)
- Cetak formulir OPPE

### 📈 Evaluasi Mutu Layanan Klinis
- Pencatatan indikator mutu per unit/instalasi per bulan
- Standar target vs capaian, analisis, RTL, PIC
- Tracking gap otomatis (tercapai / belum)

### ⚖️ Etik & Disiplin Profesi
- **Pelanggaran Etik** — pencatatan laporan pelanggaran (Ringan/Sedang/Berat), status tindak lanjut
- **Sidang Etik** — kalender sidang, perangkat sidang, hasil investigasi, rekomendasi pembinaan
- **Evaluasi Kinerja Etik** — penilaian per semester, predikat, status kepatuhan

### 🗂️ Sekretariat
- **Agenda Rapat** — kalender rapat (Pleno, Rutin, Koordinasi, Insidentil), daftar peserta
- **Regulasi & Kebijakan** — arsip SK Direktur, SPO, Pedoman, Peraturan; upload file PDF
- **Notulen Rapat** — pencatatan lengkap: pembahasan, keputusan, RTL & PIC; cetak notulen

### 📁 Dokumen Hub
- Dokumen umum komite: SOP, SK, Panduan, Formulir, Kebijakan
- Upload, edit, download, hapus

### 🛡️ Sub. Kredensial
- **Pengajuan Kredensial** — kredensial awal, rekredensial berkala, penambahan/perubahan kewenangan, rekredensial khusus
- **Verifikasi Dokumen** — syarat konfigurable per profesi, versioning dokumen, riwayat verifikasi (Valid / Perlu Perbaikan / Ditolak)
- **Asesmen Kompetensi** — wawancara, review portofolio, observasi praktik, uji keterampilan, review dokumen; multi-asesor dengan pernyataan bebas benturan kepentingan
- **Rekomendasi RKK** — rekomendasi per kewenangan klinis (direkomendasikan / dengan supervisi / dengan pembatasan / ditunda / tidak direkomendasikan) + endorsement komite
- **Penetapan SPK/RKK** — keputusan final pejabat berwenang, snapshot kewenangan efektif, unggah dokumen bertandatangan, cetak SPK
- **Monitoring & Rekredensial** — dashboard SPK aktif/mendekati kedaluwarsa/kedaluwarsa, supervisi aktif, tindak lanjut, rekam jejak lengkap, siklus rekredensial baru
- **Workflow state machine** — 16 status dengan transisi terotorisasi, transaksional, dan audit trail immutable
### 📝 Audit Log
- Pencatatan otomatis setiap aksi CREATE / UPDATE / DELETE

### 🔐 Autentikasi
- Login/logout berbasis Django auth
- Role-based access (admin site)

## Tech Stack

| Komponen | Teknologi |
|---|---|
| Backend | Django 5.x (Python 3.12) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Frontend | Bootstrap 5 via crispy-bootstrap5 |
| Static Files | WhiteNoise |
| Server | Gunicorn |
| Deployment | Render (render.yaml) / Railway / PythonAnywhere |

## Struktur Project

```
sim-ktkl/
├── config/             # Settings, URLs, WSGI/ASGI
├── accounts/           # App autentikasi (login/logout)
├── nakes/              # App utama (models, views, forms, admin)
│   ├── models.py       # Nakes, DokumenNakes, EvaluasiOPPE, EvaluasiMutuKlinis,
│   │                   # PelanggaranEtik, SidangEtik, EvaluasiKinerjaEtik,
│   │                   # AgendaRapat, Regulasi, NotulenRapat, DokumenUmum, AuditLog
│   ├── views.py        # Function-based views
│   ├── forms.py        # Django/Crispy forms
│   ├── urls.py         # URL routing (72 endpoints)
│   └── admin.py        # Admin site config
├── kredensial/         # App Sub. Kredensial (workflow SPK/RKK)
│   ├── models.py       # 14 model kredensial + event history
│   ├── kredensial_models.py  # Model domain (asesmen, privilege, SPK, monitoring)
│   ├── views.py        # Function-based views (26 endpoints)
│   ├── forms.py        # Django forms
│   ├── permissions.py  # Role-based access control (9 role)
│   ├── services/       # Workflow state machine + appointment service
│   └── tests.py        # 32 automated tests
├── templates/          # HTML templates (dashboard, CRUD, print, calendar)
├── static/             # Static assets (logo, favicon)
├── requirements.txt    # Dependencies
├── render.yaml         # Render deployment config
├── build.sh            # Build script (collectstatic, migrate, seed_data)
└── manage.py
```

## Instalasi Lokal

```bash
# Clone & masuk direktori
git clone <repo-url> sim-ktkl
cd sim-ktkl

# Virtual environment
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows

# Install dependencies
pip install -r requirements.txt

# Migrate & seed data
python manage.py migrate
python manage.py seed_data
python manage.py seed_kredensial_master
python manage.py seed_kredensial_accounts
python manage.py sync_nakes_kredensial

# Jalankan server
python manage.py runserver
```

Buka `http://localhost:8000`

### Command Kredensial

| Command | Fungsi |
|---|---|
| `seed_kredensial_master` | Seed syarat dokumen & katalog kewenangan per profesi (idempoten) |
| `seed_kredensial_accounts` | Buat 7 akun demo per role kredensial |
| `sync_nakes_kredensial` | Sinkronkan ringkasan `status_kredensial`/`kewenangan_klinis` Nakes (`--dry-run` untuk pratinjau) |

Akun demo kredensial: `kred_sekretariat`, `kred_verifikator`, `kred_asesor`,
`kred_subkomite`, `kred_ketua`, `kred_pejabat`, `kred_auditor`
(password default `Kredensial@123`).

## Environment Variables (Produksi)

| Variable | Deskripsi |
|---|---|
| `DATABASE_URL` | Connection string PostgreSQL |
| `DJANGO_SECRET_KEY` | Secret key (wajib diganti di produksi) |
| `DJANGO_DEBUG` | `False` untuk produksi |
| `DJANGO_ALLOWED_HOSTS` | Hostname yang diizinkan (comma-separated) |
| `CSRF_TRUSTED_ORIGINS` | Trusted origins untuk CSRF |

## Deploy ke Render

Project sudah dilengkapi `render.yaml` — tinggal connect repo ke Render dashboard, database PostgreSQL free tier otomatis terbuat.

## Dependencies

- Django ≥5.0
- psycopg2-binary ≥2.9
- django-crispy-forms ≥2.0
- crispy-bootstrap5 ≥2024.2
- openpyxl ≥3.1
- gunicorn ≥22.0
- whitenoise ≥6.5
- dj-database-url ≥2.0

## Lisensi

Proprietary — Komite Tenaga Kesehatan Lainnya Rumah Sakit.
