"""
URL routing untuk aplikasi Absensi RFID.
"""

from django.urls import path
from . import views

urlpatterns = [
    # --- Halaman web (rendered HTML) ---
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('belum-tap/', views.BelumTapView.as_view(), name='belum_tap'),
    path('rekap/', views.RekapBulananView.as_view(), name='rekap'),
    path('rekap/ekspor/', views.EksporExcelView.as_view(), name='export_excel'),
    path('rekap/ekspor-excel/', views.EksporExcelView.as_view(), name='ekspor_excel'),

    # --- API endpoint untuk perangkat ESP32 ---
    path('api/scan', views.scan_api, name='scan_api'),
]
