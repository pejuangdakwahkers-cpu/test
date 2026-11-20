"""
Model data untuk Sistem Absensi RFID Sekolah.

Tabel:
- Kelas: data kelas dengan wali kelas
- Orang: data siswa/orang yang diabsen
- Kartu: kartu RFID/NFC yang terhubung ke orang
- Perangkat: reader RFID (ESP32) yang terdaftar
- LogTap: catatan mentah setiap tap kartu
- KehadiranHarian: rekap kehadiran per orang per hari
- Pengaturan: konfigurasi singleton (jam masuk, zona waktu, dll)
"""

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
import datetime


class Kelas(models.Model):
    """Kelas/rombel di sekolah."""
    nama = models.CharField(
        max_length=100,
        help_text="Nama kelas, misal: X-IPA-1"
    )
    wali_kelas = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='kelas_wali',
        help_text="User guru yang menjadi wali kelas"
    )

    class Meta:
        verbose_name = 'Kelas'
        verbose_name_plural = 'Kelas'
        ordering = ['nama']

    def __str__(self):
        return self.nama


class Orang(models.Model):
    """
    Data siswa/orang yang diabsen.
    Dibuat otomatis saat siswa ditambahkan ke sistem.
    """
    nama = models.CharField(
        max_length=200,
        help_text="Nama lengkap siswa"
    )
    kelas = models.ForeignKey(
        Kelas,
        on_delete=models.CASCADE,
        related_name='anggota',
        help_text="Kelas tempat siswa ini terdaftar"
    )
    aktif = models.BooleanField(
        default=True,
        help_text="Status aktif siswa. Non-aktif tidak dihitung absensi."
    )

    class Meta:
        verbose_name = 'Orang'
        verbose_name_plural = 'Orang'
        ordering = ['kelas', 'nama']

    def __str__(self):
        return f"{self.nama} ({self.kelas.nama})"


class Kartu(models.Model):
    """
    Kartu RFID/NFC yang terhubung ke seorang siswa.
    Satu orang bisa punya beberapa kartu (misal: kartu hilang, diganti).
    """
    kode_kartu = models.CharField(
        max_length=50,
        unique=True,
        help_text="Kode kartu unik, misal: SIS0001"
    )
    uid = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        help_text="UID fisik kartu RFID (hex), misal: 04A1B2C3D4E580"
    )
    orang = models.ForeignKey(
        Orang,
        on_delete=models.CASCADE,
        related_name='kartu_set',
        help_text="Pemilik kartu ini"
    )

    class Meta:
        verbose_name = 'Kartu'
        verbose_name_plural = 'Kartu'

    def __str__(self):
        return f"{self.kode_kartu} → {self.orang.nama}"


class Perangkat(models.Model):
    """
    Reader RFID (ESP32 + RC522) yang terdaftar di sistem.
    Setiap perangkat punya API key unik untuk autentikasi.
    """
    device_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="ID unik perangkat, misal: gate-1"
    )
    api_key = models.CharField(
        max_length=255,
        help_text="Kunci API untuk autentikasi perangkat"
    )
    nama_lokasi = models.CharField(
        max_length=200,
        help_text="Lokasi perangkat, misal: Gerbang Utama"
    )
    model_perangkat = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="Model perangkat (opsional), misal: ESP32-WROOM"
    )
    aktif = models.BooleanField(
        default=True,
        help_text="Status aktif perangkat"
    )

    class Meta:
        verbose_name = 'Perangkat'
        verbose_name_plural = 'Perangkat'

    def __str__(self):
        return f"{self.device_id} ({self.nama_lokasi})"


class LogTap(models.Model):
    """
    Catatan mentah setiap tap kartu RFID.
    Semua tap dicatat di sini (kecuali tap ganda dalam jendela waktu).
    Waktu disimpan dalam UTC.
    """
    orang = models.ForeignKey(
        Orang,
        on_delete=models.CASCADE,
        related_name='log_tap',
        help_text="Orang yang melakukan tap"
    )
    waktu = models.DateTimeField(
        help_text="Waktu tap dalam UTC"
    )
    perangkat = models.ForeignKey(
        Perangkat,
        on_delete=models.CASCADE,
        related_name='log_tap',
        help_text="Perangkat yang membaca kartu"
    )
    data_mentah = models.JSONField(
        default=dict,
        blank=True,
        help_text="Data JSON mentah dari request perangkat"
    )

    class Meta:
        verbose_name = 'Log Tap'
        verbose_name_plural = 'Log Tap'
        ordering = ['-waktu']

    def __str__(self):
        return f"{self.orang.nama} @ {self.waktu}"


class KehadiranHarian(models.Model):
    """
    Rekap kehadiran per orang per hari.
    Dibuat saat tap pertama hari itu, atau oleh command generate_absensi_alpa.
    """
    STATUS_CHOICES = [
        ('hadir', 'Hadir'),
        ('terlambat', 'Terlambat'),
        ('alpa', 'Alpa'),
    ]

    orang = models.ForeignKey(
        Orang,
        on_delete=models.CASCADE,
        related_name='kehadiran',
        help_text="Orang yang kehadirannya dicatat"
    )
    tanggal = models.DateField(
        help_text="Tanggal kehadiran (kalender WIB)"
    )
    jam_tap_pertama = models.TimeField(
        null=True,
        blank=True,
        help_text="Jam tap pertama hari itu (waktu WIB)"
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        help_text="Status kehadiran: hadir, terlambat, atau alpa"
    )

    class Meta:
        verbose_name = 'Kehadiran Harian'
        verbose_name_plural = 'Kehadiran Harian'
        unique_together = ('orang', 'tanggal')
        ordering = ['-tanggal', 'orang']

    def __str__(self):
        return f"{self.orang.nama} | {self.tanggal} | {self.status}"


class Pengaturan(models.Model):
    """
    Konfigurasi singleton untuk sistem absensi.
    Hanya boleh ada satu baris di tabel ini.
    """
    jam_masuk = models.TimeField(
        default=datetime.time(6, 45),
        help_text="Batas jam masuk. Tap sebelum ini = hadir, sesudah = terlambat."
    )
    zona_waktu = models.CharField(
        max_length=50,
        default='Asia/Jakarta',
        help_text="Zona waktu untuk menentukan tanggal dan jam (IANA format)"
    )
    jendela_tap_ganda_detik = models.PositiveIntegerField(
        default=60,
        help_text="Jendela waktu (detik) untuk mendeteksi tap ganda"
    )

    class Meta:
        verbose_name = 'Pengaturan'
        verbose_name_plural = 'Pengaturan'

    def __str__(self):
        return f"Pengaturan (jam masuk: {self.jam_masuk})"

    def clean(self):
        """Pastikan hanya ada satu instance Pengaturan."""
        if not self.pk and Pengaturan.objects.exists():
            raise ValidationError(
                'Hanya boleh ada satu baris Pengaturan. Edit yang sudah ada.'
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        """
        Ambil instance Pengaturan. Buat default jika belum ada.
        """
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
