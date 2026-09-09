from django.urls import path
from . import views

app_name = 'nakes'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('nakes/', views.nakes_list, name='list'),
    path('nakes/tambah/', views.nakes_create, name='create'),
    path('nakes/<int:pk>/', views.nakes_detail, name='detail'),
    path('nakes/<int:pk>/edit/', views.nakes_update, name='update'),
    path('nakes/<int:pk>/hapus/', views.nakes_delete, name='delete'),
    path('nakes/<int:nakes_pk>/upload/', views.dokumen_upload, name='dokumen_upload'),
    path('dokumen/<int:pk>/download/', views.dokumen_download, name='dokumen_download'),
    path('dokumen/<int:pk>/hapus/', views.dokumen_delete, name='dokumen_delete'),
    path('audit/', views.audit_log, name='audit_log'),
    path('export/', views.export_excel, name='export'),
    path('template/', views.download_template, name='download_template'),
    path('import/', views.upload_bulk, name='upload_bulk'),
    path('dokumen/', views.dokumen_hub, name='dokumen_hub'),
    path('dokumen/umum/upload/', views.dokumen_umum_create, name='dokumen_umum_create'),
    path('dokumen/umum/<int:pk>/download/', views.dokumen_umum_download, name='dokumen_umum_download'),
    path('dokumen/umum/<int:pk>/edit/', views.dokumen_umum_edit, name='dokumen_umum_edit'),
    path('dokumen/umum/<int:pk>/hapus/', views.dokumen_umum_delete, name='dokumen_umum_delete'),

    path('oppe/', views.oppe_list, name='oppe_list'),
    path('oppe/tambah/', views.oppe_create, name='oppe_create'),
    path('oppe/<int:pk>/', views.oppe_detail, name='oppe_detail'),
    path('oppe/<int:pk>/edit/', views.oppe_update, name='oppe_update'),
    path('oppe/<int:pk>/hapus/', views.oppe_delete, name='oppe_delete'),

    path('mutu/', views.mutu_list, name='mutu_list'),
    path('mutu/tambah/', views.mutu_create, name='mutu_create'),
    path('mutu/<int:pk>/', views.mutu_detail, name='mutu_detail'),
    path('mutu/<int:pk>/edit/', views.mutu_update, name='mutu_update'),
    path('mutu/<int:pk>/hapus/', views.mutu_delete, name='mutu_delete'),
]
