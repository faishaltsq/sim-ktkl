# AGENTS.md

Project ini punya aturan desain sendiri di `DESIGN.md`. Untuk pekerjaan UI,
copy, mobile layout, atau code comments, baca dulu file aturannya.

## antislop

Untuk pekerjaan UI, copy, people, mobile layout, atau code comments, baca
`DESIGN.md` untuk arah desain, lalu `antislop.md` sebagai filternya.
antislop terpasang sebagai plugin, bukan sebagai folder di project ini.

Sebelum mulai, ikuti bagian "Two Usage Modes" di core antislop dengan urutan
ketat: instruksi sesi eksplisit lebih dulu, lalu preferensi global, lalu
tanya. Instruksi sesi selalu menang.

- Mode saat ini: **AFTER** (dipilih 2026-10-28, audit `anti-slop/audit-001-2026-10-28.md`)

Laporan audit ditulis di `anti-slop/audit-NNN-YYYY-MM-DD.md` dengan nomor
yang terus naik.

## Tech Stack

Django 5.x, Python 3.12, SQLite (dev) / PostgreSQL (prod), Bootstrap 5,
crispy-bootstrap5, WhiteNoise, Gunicorn. Deployment: Render / Railway /
Vercel.

## Perintah

```bash
python manage.py migrate
python manage.py seed_data      # membuat user admin/pengurus/demo + data awal
python manage.py runserver
python manage.py test nakes.tests accounts
```

## Catatan Project

- `staticfiles/` adalah output `collectstatic`, bukan sumber. Jangan diedit.
- `db.sqlite3` dibundel untuk deployment serverless (Vercel). Ada `db.sqlite3.old`
  sebagai cadangan.
- Akun `demo` bersifat read-only; penegakannya ada di `nakes/middleware.py`.
  Login demo lewat `POST /accounts/demo-login/` — kredensial tidak pernah
  dikirim ke browser.
