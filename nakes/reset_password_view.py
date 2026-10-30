"""Reset password akun produksi sekali-pakai.

Endpoint ini dibuat untuk memperbaiki password di database production
(PostgreSQL di Vercel) yang tidak bisa diakses dari mesin lokal.

Aturan keamanan:
- Hanya superuser yang sudah login yang bisa membukanya.
- Butuh token rahasia dari environment RESET_PASSWORD_TOKEN. Kalau env
  tidak diisi, endpoint menolak semua permintaan.
- Akun demo tidak diubah, tetap demo123, supaya tombol "Masuk Sebagai
  Demo" di halaman login tetap berfungsi.
"""
import os

from django.contrib.auth import get_user_model
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST

# Username yang TIDAK boleh diubah: akun demo harus tetap demo123
# supaya tombol "Masuk Sebagai Demo" di halaman login tetap berfungsi.
PROTECTED_USERNAMES = {'demo'}

# Password baru untuk semua akun selain yang dilindungi.
NEW_PASSWORD = os.environ.get('RESET_PASSWORD_VALUE', 'qweasd123')

# Password khusus untuk akun yang dilindungi.
DEMO_PASSWORD = 'demo123'


@require_POST
def reset_all_passwords(request):
    if not (request.user.is_authenticated and request.user.is_superuser):
        return HttpResponseForbidden('Hanya superuser yang bisa mengakses endpoint ini.')

    expected_token = os.environ.get('RESET_PASSWORD_TOKEN', '')
    if not expected_token:
        return HttpResponseForbidden(
            'RESET_PASSWORD_TOKEN belum di-set di environment. '
            'Endpoint ini sengaja dimatikan.'
        )

    supplied = request.POST.get('token') or request.GET.get('token') or ''
    if supplied != expected_token:
        return HttpResponseForbidden('Token tidak cocok.')

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
        + '\n\nHapus RESET_PASSWORD_TOKEN dari environment Vercel sekarang.'
    )
    return HttpResponse(body, content_type='text/plain; charset=utf-8')
