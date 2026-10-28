import secrets

from django.contrib.auth import get_user_model, login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.urls import path
from django.views.decorators.http import require_POST

app_name = 'accounts'

DEMO_USERNAME = 'demo'


def demo_login(request):
    """Masuk sebagai akun demo tanpa mengirim kredensial ke browser.

    Password demo tidak pernah muncul di HTML. Kalau akun demo belum ada,
    akun itu dibuat di sini dengan password acak yang tidak dicetak ke mana pun.
    """
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username=DEMO_USERNAME,
        defaults={'first_name': 'Akun', 'last_name': 'Demo'},
    )
    if created:
        user.set_password(secrets.token_urlsafe(32))
        user.save()
    login(request, user)
    return redirect(request.POST.get('next') or 'nakes:dashboard')


urlpatterns = [
    path('login/', LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('demo-login/', require_POST(demo_login), name='demo_login'),
]
