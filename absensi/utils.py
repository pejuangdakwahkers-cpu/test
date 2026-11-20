"""
Fungsi utilitas untuk Sistem Absensi RFID.
- Konversi zona waktu
- Format tanggal Indonesia
- Ekspor Excel (openpyxl)
- Helper pengaturan
"""

import datetime
from zoneinfo import ZoneInfo

from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from .models import Pengaturan


# ============================================================
# Helper zona waktu & penanggalan
# ============================================================

NAMA_HARI = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
NAMA_BULAN = [
    '', 'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
    'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
]


def get_zona_waktu():
    """Ambil objek ZoneInfo dari pengaturan."""
    pengaturan = Pengaturan.get_solo()
    return ZoneInfo(pengaturan.zona_waktu)


def sekarang_wib():
    """Waktu sekarang dalam zona waktu sekolah (default WIB)."""
    tz = get_zona_waktu()
    return datetime.datetime.now(tz)


def hari_ini_wib():
    """Tanggal hari ini dalam zona waktu sekolah."""
    return sekarang_wib().date()


def utc_ke_lokal(dt_utc):
    """Konversi datetime UTC ke zona waktu lokal sekolah."""
    tz = get_zona_waktu()
    return dt_utc.astimezone(tz)


def format_tanggal_indonesia(d):
    """Format tanggal ke bahasa Indonesia, misal: Senin, 16 November 2026."""
    if isinstance(d, datetime.datetime):
        d = d.date()
    hari = NAMA_HARI[d.weekday()]
    bulan = NAMA_BULAN[d.month]
    return f"{hari}, {d.day} {bulan} {d.year}"


# ============================================================
# Ekspor Excel
# ============================================================

def buat_excel_rekap(data_rekap, data_detail, tanggal_mulai, tanggal_selesai):
    """
    Buat file Excel (.xlsx) rekap kehadiran.

    Args:
        data_rekap: list of dict — ringkasan per siswa
            [{'nama': str, 'kelas': str, 'hadir': int, 'terlambat': int,
              'alpa': int, 'total_hari': int, 'persentase': float}]
        data_detail: list of dict — detail per hari per siswa
            [{'nama': str, 'kelas': str, 'tanggal': date, 'status': str,
              'jam_tap': time|None}]
        tanggal_mulai: date
        tanggal_selesai: date

    Returns:
        HttpResponse dengan file .xlsx siap download.
    """
    wb = Workbook()

    # ---- Sheet 1: Ringkasan Per Siswa ----
    ws_ringkasan = wb.active
    ws_ringkasan.title = "Ringkasan Per Siswa"

    # Style header
    header_font = Font(bold=True, size=11)
    header_alignment = Alignment(horizontal='center', vertical='center')
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin'),
    )

    # Judul
    ws_ringkasan.merge_cells('A1:G1')
    ws_ringkasan['A1'] = (
        f"Rekap Kehadiran: {tanggal_mulai.strftime('%d/%m/%Y')} - "
        f"{tanggal_selesai.strftime('%d/%m/%Y')}"
    )
    ws_ringkasan['A1'].font = Font(bold=True, size=14)
    ws_ringkasan['A1'].alignment = Alignment(horizontal='center')

    # Header kolom
    headers_ringkasan = [
        'No', 'Nama', 'Kelas', 'Hadir', 'Terlambat', 'Alpa', 'Persentase (%)'
    ]
    for col, header in enumerate(headers_ringkasan, 1):
        cell = ws_ringkasan.cell(row=3, column=col, value=header)
        cell.font = header_font
        cell.alignment = header_alignment
        cell.border = thin_border

    # Data ringkasan
    for i, row_data in enumerate(data_rekap, 1):
        row_num = i + 3
        ws_ringkasan.cell(row=row_num, column=1, value=i).border = thin_border
        ws_ringkasan.cell(row=row_num, column=2, value=row_data['nama']).border = thin_border
        ws_ringkasan.cell(row=row_num, column=3, value=row_data['kelas']).border = thin_border
        ws_ringkasan.cell(row=row_num, column=4, value=row_data['hadir']).border = thin_border
        ws_ringkasan.cell(row=row_num, column=5, value=row_data['terlambat']).border = thin_border
        ws_ringkasan.cell(row=row_num, column=6, value=row_data['alpa']).border = thin_border
        cell_persen = ws_ringkasan.cell(
            row=row_num, column=7, value=row_data['persentase']
        )
        cell_persen.border = thin_border
        cell_persen.number_format = '0.0'

    # Lebar kolom otomatis
    lebar_ringkasan = [5, 30, 15, 10, 12, 10, 15]
    for col, width in enumerate(lebar_ringkasan, 1):
        ws_ringkasan.column_dimensions[get_column_letter(col)].width = width

    # ---- Sheet 2: Detail Per Hari ----
    ws_detail = wb.create_sheet(title="Detail Per Hari")

    # Judul
    ws_detail.merge_cells('A1:E1')
    ws_detail['A1'] = (
        f"Detail Kehadiran: {tanggal_mulai.strftime('%d/%m/%Y')} - "
        f"{tanggal_selesai.strftime('%d/%m/%Y')}"
    )
    ws_detail['A1'].font = Font(bold=True, size=14)
    ws_detail['A1'].alignment = Alignment(horizontal='center')

    # Header kolom
    headers_detail = ['No', 'Nama', 'Kelas', 'Tanggal', 'Status', 'Jam Tap']
    for col, header in enumerate(headers_detail, 1):
        cell = ws_detail.cell(row=3, column=col, value=header)
        cell.font = header_font
        cell.alignment = header_alignment
        cell.border = thin_border

    # Data detail
    for i, row_data in enumerate(data_detail, 1):
        row_num = i + 3
        ws_detail.cell(row=row_num, column=1, value=i).border = thin_border
        ws_detail.cell(row=row_num, column=2, value=row_data['nama']).border = thin_border
        ws_detail.cell(row=row_num, column=3, value=row_data['kelas']).border = thin_border
        tgl_cell = ws_detail.cell(
            row=row_num, column=4,
            value=row_data['tanggal'].strftime('%d/%m/%Y')
                if row_data['tanggal'] else ''
        )
        tgl_cell.border = thin_border
        ws_detail.cell(row=row_num, column=5, value=row_data['status']).border = thin_border
        jam_str = (
            row_data['jam_tap'].strftime('%H:%M')
            if row_data.get('jam_tap') else '-'
        )
        ws_detail.cell(row=row_num, column=6, value=jam_str).border = thin_border

    # Lebar kolom otomatis
    lebar_detail = [5, 30, 15, 15, 12, 10]
    for col, width in enumerate(lebar_detail, 1):
        ws_detail.column_dimensions[get_column_letter(col)].width = width

    # Buat response HTTP
    nama_file = (
        f"rekap_kehadiran_{tanggal_mulai.strftime('%Y%m%d')}_"
        f"{tanggal_selesai.strftime('%Y%m%d')}.xlsx"
    )
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{nama_file}"'

    wb.save(response)
    return response
