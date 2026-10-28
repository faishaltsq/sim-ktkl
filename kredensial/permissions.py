"""Role-based access control untuk modul Sub. Kredensial.

Role operasional dipetakan ke permission Django. Administrator dapat
memetakan role ke tata kelola rumah sakit melalui group Django.
"""
from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required

# Nama group Django per role operasional
ROLE_GROUPS = {
    'administrator': 'Kredensial Administrator',
    'sekretariat': 'Kredensial Sekretariat',
    'verifikator': 'Kredensial Verifikator',
    'asesor': 'Kredensial Asesor',
    'subkomite': 'Kredensial Subkomite',
    'ketua_komite': 'Kredensial Ketua Komite',
    'pejabat': 'Kredensial Pejabat Berwenang',
    'auditor': 'Kredensial Auditor',
}

# Role yang boleh melakukan setiap aksi (superuser selalu lolos)
ROLE_ACTIONS = {
    'create_application': ['administrator', 'sekretariat'],
    'verify_document': ['administrator', 'verifikator'],
    'assess': ['administrator', 'asesor'],
    'recommend': ['administrator', 'subkomite'],
    'endorse': ['administrator', 'subkomite', 'ketua_komite'],
    'approve': ['administrator', 'pejabat'],
    'issue_document': ['administrator', 'pejabat', 'sekretariat'],
    'manage_master': ['administrator'],
    'monitor': ['administrator', 'sekretariat', 'verifikator', 'asesor',
                'subkomite', 'ketua_komite', 'pejabat', 'auditor'],
}


def user_has_role(user, *roles):
    """True jika user superuser atau anggota salah satu group role."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    group_names = {ROLE_GROUPS[r] for r in roles if r in ROLE_GROUPS}
    return user.groups.filter(name__in=group_names).exists()


def user_can(user, action):
    """True jika user boleh melakukan aksi sesuai ROLE_ACTIONS."""
    roles = ROLE_ACTIONS.get(action, [])
    return user_has_role(user, *roles)


def kredensial_role_required(*actions):
    """Decorator view: wajib login DAN punya role untuk salah satu aksi."""

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if not any(user_can(request.user, a) for a in actions):
                raise PermissionDenied(
                    'Anda tidak memiliki kewenangan untuk aksi ini.'
                )
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


# Transisi workflow → role yang diizinkan
TRANSITION_ROLES = {
    ('DRAFT', 'SUBMITTED'): ['create_application'],
    ('SUBMITTED', 'UNDER_VERIFICATION'): ['verify_document'],
    ('UNDER_VERIFICATION', 'REVISION_REQUIRED'): ['verify_document'],
    ('REVISION_REQUIRED', 'RESUBMITTED'): ['create_application'],
    ('RESUBMITTED', 'UNDER_VERIFICATION'): ['verify_document'],
    ('UNDER_VERIFICATION', 'VERIFIED'): ['verify_document'],
    ('VERIFIED', 'UNDER_ASSESSMENT'): ['assess'],
    ('UNDER_ASSESSMENT', 'ASSESSMENT_COMPLETED'): ['assess'],
    ('ASSESSMENT_COMPLETED', 'RECOMMENDATION_REVIEW'): ['recommend'],
    ('RECOMMENDATION_REVIEW', 'RECOMMENDED'): ['recommend'],
    ('RECOMMENDED', 'PENDING_FINAL_DECISION'): ['endorse'],
    ('PENDING_FINAL_DECISION', 'RETURNED_FOR_REVISION'): ['approve'],
    ('PENDING_FINAL_DECISION', 'REJECTED'): ['approve'],
    ('PENDING_FINAL_DECISION', 'APPROVED'): ['approve'],
    ('APPROVED', 'DOCUMENT_ISSUED'): ['issue_document'],
    ('DOCUMENT_ISSUED', 'CLOSED'): ['manage_master'],
}


def user_can_transition(user, from_state, to_state):
    """True jika user boleh melakukan transisi state tertentu."""
    if user.is_superuser:
        return True
    actions = TRANSITION_ROLES.get((from_state, to_state))
    if not actions:
        return False
    return any(user_can(user, a) for a in actions)
