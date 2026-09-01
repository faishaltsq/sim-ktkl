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
    path('dokumen/<int:pk>/hapus/', views.dokumen_delete, name='dokumen_delete'),
    path('audit/', views.audit_log, name='audit_log'),
    path('export/', views.export_excel, name='export'),
]
