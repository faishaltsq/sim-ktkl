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

    # Asesmen kompetensi
    path('pengajuan/<int:pk>/asesmen/tambah/', views.assessment_create, name='assessment_create'),
    path('asesmen/<int:pk>/hasil/tambah/', views.assessment_result_add, name='assessment_result_add'),
    path('asesmen/<int:pk>/selesai/', views.assessment_complete, name='assessment_complete'),

    # Kewenangan diminta
    path('pengajuan/<int:pk>/kewenangan/tambah/', views.requested_privilege_add, name='requested_privilege_add'),

    # Rekomendasi RKK
    path('rekomendasi/<int:pk>/', views.recommendation_edit, name='recommendation_edit'),
    path('pengajuan/<int:pk>/review/', views.review_create, name='review_create'),

    # Master katalog kewenangan
    path('master/kewenangan/', views.privilege_list, name='privilege_list'),
    path('master/kewenangan/tambah/', views.privilege_create, name='privilege_create'),
    path('master/kewenangan/<int:pk>/edit/', views.privilege_update, name='privilege_update'),

    # Penetapan SPK/RKK
    path('pengajuan/<int:pk>/spk/tetapkan/', views.appointment_create, name='appointment_create'),
    path('pengajuan/<int:pk>/spk/', views.appointment_detail, name='appointment_detail'),
    path('spk/<int:pk>/dokumen/', views.appointment_document_upload, name='appointment_document_upload'),
    path('spk/<int:pk>/unduh/<str:doc_type>/', views.appointment_download, name='appointment_download'),
    path('spk/<int:pk>/cetak/', views.appointment_print, name='appointment_print'),
]
