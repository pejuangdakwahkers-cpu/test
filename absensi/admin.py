"""
Registrasi model di Django Admin untuk Sistem Absensi RFID.
Admin bisa mengelola semua data: Kelas, Orang, Kartu, Perangkat, dll.
"""

from django.contrib import admin
from .models import (
    Kelas, Orang, Kartu, Perangkat,
    LogTap, KehadiranHarian, Pengaturan
)


@admin.register(Kelas)
class KelasAdmin(admin.ModelAdmin):
    list_display = ('nama', 'wali_kelas')
    search_fields = ('nama',)
    list_filter = ('wali_kelas',)


class KartuInline(admin.TabularInline):
    """Inline kartu di halaman detail Orang."""
    model = Kartu
    extra = 1


@admin.register(Orang)
class OrangAdmin(admin.ModelAdmin):
    list_display = ('nama', 'kelas', 'aktif')
    list_filter = ('kelas', 'aktif')
    search_fields = ('nama',)
    inlines = [KartuInline]


@admin.register(Kartu)
class KartuAdmin(admin.ModelAdmin):
    list_display = ('kode_kartu', 'uid', 'orang')
    search_fields = ('kode_kartu', 'uid', 'orang__nama')
    list_filter = ('orang__kelas',)


@admin.register(Perangkat)
class PerangkatAdmin(admin.ModelAdmin):
    list_display = ('device_id', 'nama_lokasi', 'aktif')
    list_filter = ('aktif',)
    search_fields = ('device_id', 'nama_lokasi')


@admin.register(LogTap)
class LogTapAdmin(admin.ModelAdmin):
    list_display = ('orang', 'waktu', 'perangkat')
    list_filter = ('perangkat', 'waktu')
    search_fields = ('orang__nama',)
    date_hierarchy = 'waktu'
    readonly_fields = ('orang', 'waktu', 'perangkat', 'data_mentah')


@admin.register(KehadiranHarian)
class KehadiranHarianAdmin(admin.ModelAdmin):
    list_display = ('orang', 'tanggal', 'jam_tap_pertama', 'status')
    list_filter = ('status', 'tanggal', 'orang__kelas')
    search_fields = ('orang__nama',)
    date_hierarchy = 'tanggal'


@admin.register(Pengaturan)
class PengaturanAdmin(admin.ModelAdmin):
    list_display = ('jam_masuk', 'zona_waktu', 'jendela_tap_ganda_detik')

    def has_add_permission(self, request):
        """Cegah penambahan jika sudah ada satu instance."""
        if Pengaturan.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        """Cegah penghapusan pengaturan."""
        return False
