"""Reset password semua akun di database yang sedang aktif.

Endpoint ini dibuat untuk memperbaiki password di database production
(PostgreSQL di Vercel) yang tidak bisa diakses dari mesin lokal.

Aturan keamanan:
- Hanya superuser yang sudah login yang bisa membukanya. Superuser
  memang sudah punya wewenang set_password lewat Django admin, jadi
  endpoint ini tidak menambah hak akses baru, cuma mempersingkat
  langkah untuk rotate semua akun sekaligus.
- Akun demo tidak diubah, tetap demo123, supaya tombol "Masuk Sebagai
  Demo" di halaman login tetap berfungsi.
"""
import os

from django.contrib.auth import get_user_model
from django.http import HttpResponse, HttpResponseForbidden

# Username yang TIDAK boleh diubah: akun demo harus tetap demo123
# supaya tombol "Masuk Sebagai Demo" di halaman login tetap berfungsi.
PROTECTED_USERNAMES = {'demo'}

# Password baru untuk semua akun selain yang dilindungi.
NEW_PASSWORD = os.environ.get('RESET_PASSWORD_VALUE', 'qweasd123')

# Password khusus untuk akun yang dilindungi.
DEMO_PASSWORD = 'demo123'


def reset_all_passwords(request):
    if not (request.user.is_authenticated and request.user.is_superuser):
        return HttpResponseForbidden('Hanya superuser yang bisa mengakses endpoint ini.')

    User = get_user_model()
    lines = []
    for user in User.objects.all().order_by('pk'):
        if user.username in PROTECTED_USERNAMES:
            password = DEMO_PASSWORD
            note = 'dilindungi, tetap demo123'
        else:
            password = NEW_PASSWORD
            note = 'diubah'
        user.set_password(password)
        user.save()
        lines.append(f'{user.username}: {note}')

    body = (
        'Reset password selesai.\n\n'
        + '\n'.join(lines)
        + '\n\nSemua akun kecuali demo sekarang memakai: '
        + NEW_PASSWORD
    )
    return HttpResponse(body, content_type='text/plain; charset=utf-8')
