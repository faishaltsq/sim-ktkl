from django.http import JsonResponse
from django.contrib import messages
from django.shortcuts import redirect

DEMO_USERNAME = 'demo'

# URL patterns yang termasuk operasi tulis (POST-only mutable)
# Semua views mutable punya suffix: tambah, hapus, edit, upload, import, export ke POST
# Kita blok semua POST request dari user demo — GET tetap boleh
READONLY_EXEMPT_PATHS = [
    '/accounts/logout/',   # logout tetap boleh
]

# Path yang bahkan GET-nya diblok untuk demo (admin write pages)
ADMIN_WRITE_BLOCK_PREFIXES = [
    '/admin/login/',       # boleh akses
]


class ReadOnlyDemoMiddleware:
    """
    Blok semua POST/PUT/PATCH/DELETE request dari user 'demo'.
    GET tetap diperbolehkan (read-only).
    Admin: blok semua write action.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and request.user.username == DEMO_USERNAME
            and request.method in ('POST', 'PUT', 'PATCH', 'DELETE')
            and request.path not in READONLY_EXEMPT_PATHS
        ):
            # AJAX / fetch request → JSON response
            if (
                request.headers.get('X-Requested-With') == 'XMLHttpRequest'
                or 'application/json' in request.headers.get('Accept', '')
            ):
                return JsonResponse(
                    {'error': 'Akun demo bersifat read-only. Operasi ini tidak diizinkan.'},
                    status=403,
                )

            # Form submit biasa → set session flag lalu redirect back
            request.session['readonly_triggered'] = True
            referer = request.META.get('HTTP_REFERER', '/')
            return redirect(referer)

        return self.get_response(request)
