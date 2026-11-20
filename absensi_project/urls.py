"""
URL utama proyek Absensi RFID.
Menghubungkan URL admin dan URL aplikasi absensi.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('absensi.urls')),
]
