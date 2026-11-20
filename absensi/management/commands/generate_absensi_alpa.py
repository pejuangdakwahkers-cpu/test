"""
Management command: generate_absensi_alpa

Tandai alpa untuk semua siswa aktif yang belum tap pada hari tertentu.
Jalankan setiap malam via cron untuk memastikan data kehadiran lengkap.

Penggunaan:
    python manage.py generate_absensi_alpa
    python manage.py generate_absensi_alpa --tanggal 2024-01-15
"""

import datetime
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand

from absensi.models import Orang, KehadiranHarian, Pengaturan


class Command(BaseCommand):
    help = (
        'Tandai alpa untuk siswa aktif yang tidak tap hari ini '
        '(atau tanggal yang ditentukan). Jalankan via cron setiap malam.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--tanggal',
            type=str,
            default=None,
            help='Tanggal yang akan diproses (format: YYYY-MM-DD). Default: hari ini WIB.',
        )

    def handle(self, *args, **options):
        pengaturan = Pengaturan.get_solo()
        tz = ZoneInfo(pengaturan.zona_waktu)

        # Tentukan tanggal yang akan diproses
        if options['tanggal']:
            tanggal = datetime.date.fromisoformat(options['tanggal'])
        else:
            tanggal = datetime.datetime.now(tz).date()

        self.stdout.write(
            f"Memproses alpa untuk tanggal: {tanggal.isoformat()}"
        )

        # Ambil semua siswa aktif
        siswa_aktif = Orang.objects.filter(aktif=True)

        # Ambil ID siswa yang sudah punya KehadiranHarian hari ini
        sudah_tercatat_ids = KehadiranHarian.objects.filter(
            tanggal=tanggal,
        ).values_list('orang_id', flat=True)

        # Siswa yang belum tercatat = alpa
        siswa_alpa = siswa_aktif.exclude(id__in=sudah_tercatat_ids)

        jumlah_dibuat = 0
        for siswa in siswa_alpa:
            KehadiranHarian.objects.create(
                orang=siswa,
                tanggal=tanggal,
                jam_tap_pertama=None,
                status='alpa',
            )
            jumlah_dibuat += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Selesai. {jumlah_dibuat} siswa ditandai alpa "
                f"untuk tanggal {tanggal.isoformat()}."
            )
        )
