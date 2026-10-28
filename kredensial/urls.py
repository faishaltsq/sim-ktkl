from django.urls import path
from . import views

app_name = 'kredensial'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Pengajuan
    path('pengajuan/', views.application_list, name='application_list'),
    path('pengajuan/tambah/', views.application_create, name='application_create'),
    path('pengajuan/<int:pk>/', views.application_detail, name='application_detail'),
    path('pengajuan/<int:pk>/edit/', views.application_update, name='application_update'),
    path('pengajuan/<int:pk>/transisi/<str:to_state>/', views.application_transition, name='application_transition'),

    # Dokumen
    path('pengajuan/<int:pk>/dokumen/upload/', views.document_upload, name='document_upload'),
    path('dokumen/<int:pk>/download/', views.document_download, name='document_download'),
    path('dokumen/<int:pk>/verifikasi/', views.document_verify, name='document_verify'),

    # Master syarat dokumen
    path('master/syarat/', views.requirement_list, name='requirement_list'),
    path('master/syarat/tambah/', views.requirement_create, name='requirement_create'),
    path('master/syarat/<int:pk>/edit/', views.requirement_update, name='requirement_update'),
]
