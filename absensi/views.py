"""
Views untuk Sistem Absensi RFID Sekolah.

View yang tersedia:
1. LoginView — halaman login guru/admin
2. LogoutView — logout dan redirect ke login
3. DashboardView — ringkasan kehadiran hari ini
4. BelumTapView — daftar siswa yang belum tap hari ini
5. RekapBulananView — tabel rekap kehadiran per siswa (filter tanggal & kelas)
6. EksporExcelView — download .xlsx dari rekap kehadiran
7. scan_api — POST /api/scan endpoint untuk perangkat ESP32
"""

import json
import datetime
from zoneinfo import ZoneInfo

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.views import View
from django.http import JsonResponse, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from .models import (
    Kelas, Orang, Kartu, Perangkat,
    LogTap, KehadiranHarian, Pengaturan
)
from .forms import LoginForm, RekapFilterForm
from .utils import (
    sekarang_wib, hari_ini_wib, utc_ke_lokal,
    format_tanggal_indonesia, buat_excel_rekap
)


# ============================================================
# Rate limiter sederhana berbasis memori (per perangkat)
# ============================================================
_rate_limit_cache = {}  # {device_id: [datetime_utc, ...]}
RATE_LIMIT_MAX = 30       # maks 30 request
RATE_LIMIT_WINDOW = 60    # per 60 detik


def cek_rate_limit(device_id):
    """
    Cek apakah perangkat melebihi batas rate limit.
    Returns True jika masih diizinkan, False jika melebihi batas.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff = now - datetime.timedelta(seconds=RATE_LIMIT_WINDOW)

    if device_id not in _rate_limit_cache:
        _rate_limit_cache[device_id] = []

    # Bersihkan timestamp lama
    _rate_limit_cache[device_id] = [
        ts for ts in _rate_limit_cache[device_id] if ts > cutoff
    ]

    if len(_rate_limit_cache[device_id]) >= RATE_LIMIT_MAX:
        return False

    _rate_limit_cache[device_id].append(now)
    return True


# ============================================================
# API Endpoint: POST /api/scan (KONTRAK TETAP)
# ============================================================

@csrf_exempt
def scan_api(request):
    """
    Endpoint untuk menerima data scan kartu RFID dari perangkat ESP32.

    Headers: Content-Type: application/json, X-API-Key: <kunci perangkat>
    Body: {"uid": "04A1B2C3D4E580", "card_code": "SIS0001", "device": "gate-1", "ts": 1763280000}

    Responses:
    - 200: {"ok": true, "name": "Budi", "duplicate": false} — berhasil atau tap ganda
    - 401: {"ok": false, "error": "unauthorized"} — API key salah
    - 404: {"ok": false, "error": "kartu tidak terdaftar"} — kartu tidak ada
    """
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    # --- Autentikasi via API Key ---
    api_key = request.headers.get('X-API-Key', '')
    if not api_key:
        return JsonResponse(
            {'ok': False, 'error': 'unauthorized'},
            status=401
        )

    try:
        perangkat = Perangkat.objects.get(api_key=api_key, aktif=True)
    except Perangkat.DoesNotExist:
        return JsonResponse(
            {'ok': False, 'error': 'unauthorized'},
            status=401
        )

    # --- Rate limiting per perangkat ---
    if not cek_rate_limit(perangkat.device_id):
        return JsonResponse(
            {'ok': False, 'error': 'rate limit exceeded'},
            status=429
        )

    # --- Parse body JSON ---
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse(
            {'ok': False, 'error': 'invalid json'},
            status=400
        )

    uid = data.get('uid', '')
    card_code = data.get('card_code', '')
    ts = data.get('ts')

    # --- Cari kartu: cocokkan card_code dulu, kalau tidak ketemu coba uid ---
    kartu = None
    if card_code:
        kartu = Kartu.objects.filter(kode_kartu=card_code).select_related('orang').first()
    if not kartu and uid:
        kartu = Kartu.objects.filter(uid=uid).select_related('orang').first()

    if not kartu:
        return JsonResponse(
            {'ok': False, 'error': 'kartu tidak terdaftar'},
            status=404
        )

    orang = kartu.orang

    # Pastikan orang aktif
    if not orang.aktif:
        return JsonResponse(
            {'ok': False, 'error': 'kartu tidak terdaftar'},
            status=404
        )

    # --- Tentukan waktu tap (UTC) ---
    if ts:
        try:
            waktu_tap_utc = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
        except (ValueError, OSError, OverflowError):
            waktu_tap_utc = timezone.now()
    else:
        waktu_tap_utc = timezone.now()

    # --- Ambil pengaturan ---
    pengaturan = Pengaturan.get_solo()
    jendela = pengaturan.jendela_tap_ganda_detik

    # --- Cek tap ganda (orang sama dalam jendela_tap_ganda_detik) ---
    batas_tap_ganda = waktu_tap_utc - datetime.timedelta(seconds=jendela)
    tap_terakhir = LogTap.objects.filter(
        orang=orang,
        waktu__gte=batas_tap_ganda
    ).order_by('-waktu').first()

    if tap_terakhir:
        # Tap ganda terdeteksi → kembalikan 200 + duplicate:true, JANGAN simpan baru
        return JsonResponse({
            'ok': True,
            'name': orang.nama,
            'duplicate': True,
        })

    # --- Simpan LogTap baru ---
    LogTap.objects.create(
        orang=orang,
        waktu=waktu_tap_utc,
        perangkat=perangkat,
        data_mentah=data,
    )

    # --- Proses KehadiranHarian ---
    # Konversi waktu tap ke zona waktu lokal (default Asia/Jakarta / WIB)
    waktu_lokal = utc_ke_lokal(waktu_tap_utc)
    tanggal_lokal = waktu_lokal.date()
    jam_lokal = waktu_lokal.time()

    # Tap pertama hari itu (kalender WIB) → buat KehadiranHarian
    kehadiran_existing = KehadiranHarian.objects.filter(
        orang=orang,
        tanggal=tanggal_lokal,
    ).first()

    if not kehadiran_existing:
        # Tentukan status: hadir jika sebelum/sama dengan jam_masuk, terlambat jika sesudah
        if jam_lokal <= pengaturan.jam_masuk:
            status_kehadiran = 'hadir'
        else:
            status_kehadiran = 'terlambat'

        KehadiranHarian.objects.create(
            orang=orang,
            tanggal=tanggal_lokal,
            jam_tap_pertama=jam_lokal,
            status=status_kehadiran,
        )
    # Tap selanjutnya hari yang sama → LogTap tetap dicatat, KehadiranHarian JANGAN diubah

    return JsonResponse({
        'ok': True,
        'name': orang.nama,
        'duplicate': False,
    })


# ============================================================
# View: Login
# ============================================================

class LoginView(View):
    """
    Halaman login untuk guru dan admin.
    GET: form login
    POST: autentikasi kredensial, redirect ke dashboard
    """
    template_name = 'absensi/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        form = LoginForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                next_url = request.GET.get('next') or request.POST.get('next') or 'dashboard'
                return redirect(next_url)
            else:
                form.add_error(None, 'Username atau password salah.')
        return render(request, self.template_name, {'form': form})


# ============================================================
# View: Logout
# ============================================================

class LogoutView(View):
    """Logout sesi pengguna dan redirect ke halaman login."""

    def get(self, request):
        logout(request)
        return redirect('login')

    def post(self, request):
        logout(request)
        return redirect('login')


# ============================================================
# View: Dashboard
# ============================================================

class DashboardView(LoginRequiredMixin, View):
    """
    Dashboard ringkasan kehadiran hari ini.
    Menampilkan:
    - Ringkasan seluruh sekolah (Total, Hadir, Terlambat, Belum Tap)
    - Ringkasan khusus kelas saya (jika user adalah wali kelas)
    - Tabel 10 aktivitas tap terakhir hari ini
    """
    template_name = 'absensi/dashboard.html'

    def get(self, request):
        tanggal = hari_ini_wib()
        pengaturan = Pengaturan.get_solo()
        user = request.user

        # Cek apakah user adalah wali kelas
        kelas_wali = getattr(user, 'kelas_wali', None)
        is_wali_kelas = bool(kelas_wali)

        # Hitung statistik per kelas
        daftar_kelas = Kelas.objects.all().order_by('nama')
        ringkasan_per_kelas = []

        kelas_total = 0
        kelas_hadir = 0
        kelas_terlambat = 0
        kelas_belum_tap = 0

        for kls in daftar_kelas:
            siswa_kls = Orang.objects.filter(kelas=kls, aktif=True)
            k_total = siswa_kls.count()

            kehadiran_kls = KehadiranHarian.objects.filter(
                orang__kelas=kls,
                orang__aktif=True,
                tanggal=tanggal,
            )
            k_hadir = kehadiran_kls.filter(status='hadir').count()
            k_terlambat = kehadiran_kls.filter(status='terlambat').count()
            k_belum_tap = k_total - k_hadir - k_terlambat

            ringkasan_per_kelas.append({
                'kelas': kls,
                'total': k_total,
                'hadir': k_hadir,
                'terlambat': k_terlambat,
                'belum_tap': k_belum_tap,
            })

            # Data khusus wali kelas
            if kelas_wali and kls.pk == kelas_wali.pk:
                kelas_total = k_total
                kelas_hadir = k_hadir
                kelas_terlambat = k_terlambat
                kelas_belum_tap = k_belum_tap

        # Total seluruh sekolah
        total_siswa = Orang.objects.filter(aktif=True).count()
        kehadiran_hari_ini = KehadiranHarian.objects.filter(
            orang__aktif=True,
            tanggal=tanggal,
        )
        hadir = kehadiran_hari_ini.filter(status='hadir').count()
        terlambat = kehadiran_hari_ini.filter(status='terlambat').count()
        belum_tap = total_siswa - hadir - terlambat

        # 10 Aktivitas tap terakhir hari ini (ditentukan berdasarkan kalender WIB)
        # Hitung rentang UTC untuk hari ini di WIB
        tz = ZoneInfo(pengaturan.zona_waktu)
        awal_hari_lokal = datetime.datetime.combine(tanggal, datetime.time.min, tzinfo=tz)
        awal_hari_utc = awal_hari_lokal.astimezone(datetime.timezone.utc)

        log_terakhir = list(
            LogTap.objects.filter(waktu__gte=awal_hari_utc)
            .select_related('orang', 'orang__kelas')
            .order_by('-waktu')[:10]
        )

        # Tempelkan atribut status dan waktu lokal pada tiap objek log
        kehadiran_map = {
            kh.orang_id: kh.status
            for kh in KehadiranHarian.objects.filter(
                tanggal=tanggal,
                orang_id__in=[log.orang_id for log in log_terakhir]
            )
        }

        for log in log_terakhir:
            log.waktu_lokal = utc_ke_lokal(log.waktu)
            # Ambil status dari KehadiranHarian siswa hari ini
            st = kehadiran_map.get(log.orang_id)
            if not st:
                # Fallback: bandingkan jam tap dengan jam masuk
                st = 'hadir' if log.waktu_lokal.time() <= pengaturan.jam_masuk else 'terlambat'
            log.status = st

        context = {
            'today': tanggal,
            'today_formatted': format_tanggal_indonesia(tanggal),
            'total_siswa': total_siswa,
            'hadir': hadir,
            'terlambat': terlambat,
            'belum_tap': belum_tap,
            # Alias nama variabel
            'jumlah_hadir': hadir,
            'jumlah_terlambat': terlambat,
            'jumlah_belum_tap': belum_tap,
            # Data wali kelas
            'is_wali_kelas': is_wali_kelas,
            'kelas_wali': kelas_wali.nama if kelas_wali else '',
            'kelas_wali_obj': kelas_wali,
            'kelas_total': kelas_total,
            'kelas_hadir': kelas_hadir,
            'kelas_terlambat': kelas_terlambat,
            'kelas_belum_tap': kelas_belum_tap,
            # Data pendukung
            'aktivitas_terakhir': log_terakhir,
            'ringkasan_per_kelas': ringkasan_per_kelas,
            'daftar_kelas': daftar_kelas,
            'kelas_list': daftar_kelas,
        }
        return render(request, self.template_name, context)


# ============================================================
# View: Belum Tap
# ============================================================

class BelumTapView(LoginRequiredMixin, View):
    """
    Daftar siswa aktif yang belum tap hari ini.
    Filter dropdown berdasarkan kelas.
    Wali kelas secara otomatis default ke kelas yang diampunya.
    """
    template_name = 'absensi/belum_tap.html'

    def get(self, request):
        tanggal = hari_ini_wib()
        user = request.user
        kelas_wali = getattr(user, 'kelas_wali', None)

        kelas_param = request.GET.get('kelas')
        selected_kelas = None

        if kelas_param is not None:
            # User eksplisit memilih filter (bisa kosong = semua kelas)
            if kelas_param.isdigit():
                selected_kelas = int(kelas_param)
        elif kelas_wali:
            # Default ke kelas wali jika tidak ada query parameter
            selected_kelas = kelas_wali.pk

        siswa_aktif = Orang.objects.filter(aktif=True)
        if selected_kelas:
            siswa_aktif = siswa_aktif.filter(kelas_id=selected_kelas)

        # ID siswa yang sudah tercatat kehadiran hari ini
        sudah_tap_ids = KehadiranHarian.objects.filter(
            tanggal=tanggal,
            orang__aktif=True,
        ).values_list('orang_id', flat=True)

        siswa_belum_tap = siswa_aktif.exclude(
            id__in=sudah_tap_ids
        ).select_related('kelas').order_by('kelas__nama', 'nama')

        total_belum_tap = siswa_belum_tap.count()
        daftar_kelas = Kelas.objects.all().order_by('nama')

        context = {
            'siswa_belum_tap': siswa_belum_tap,
            'total_belum_tap': total_belum_tap,
            'kelas_list': daftar_kelas,
            'daftar_kelas': daftar_kelas,
            'selected_kelas': selected_kelas,
            'kelas_terpilih': selected_kelas,
            'kelas_wali': kelas_wali,
            'tanggal_hari_ini': tanggal,
        }
        return render(request, self.template_name, context)


# ============================================================
# View: Rekap Bulanan
# ============================================================

class RekapBulananView(LoginRequiredMixin, View):
    """
    Tabel rekap kehadiran per siswa dalam rentang tanggal tertentu.
    Filter: Kelas, Tanggal Mulai/Dari, Tanggal Selesai/Sampai.
    """
    template_name = 'absensi/rekap.html'

    def get(self, request):
        tanggal = hari_ini_wib()
        user = request.user
        kelas_wali = getattr(user, 'kelas_wali', None)

        # Terima baik tanggal_dari maupun tanggal_mulai
        tgl_dari_str = request.GET.get('tanggal_dari') or request.GET.get('tanggal_mulai')
        tgl_sampai_str = request.GET.get('tanggal_sampai') or request.GET.get('tanggal_selesai')
        kelas_param = request.GET.get('kelas')

        # Default tanggal: awal bulan berjalan s/d hari ini
        if tgl_dari_str:
            try:
                tanggal_mulai = datetime.date.fromisoformat(tgl_dari_str)
            except ValueError:
                tanggal_mulai = tanggal.replace(day=1)
        else:
            tanggal_mulai = tanggal.replace(day=1)

        if tgl_sampai_str:
            try:
                tanggal_selesai = datetime.date.fromisoformat(tgl_sampai_str)
            except ValueError:
                tanggal_selesai = tanggal
        else:
            tanggal_selesai = tanggal

        # Filter kelas
        selected_kelas = None
        if kelas_param is not None:
            if kelas_param.isdigit():
                selected_kelas = int(kelas_param)
        elif kelas_wali:
            selected_kelas = kelas_wali.pk

        siswa_qs = Orang.objects.filter(aktif=True).select_related('kelas')
        if selected_kelas:
            siswa_qs = siswa_qs.filter(kelas_id=selected_kelas)

        total_hari = (tanggal_selesai - tanggal_mulai).days + 1

        rekap_data = []
        for siswa in siswa_qs.order_by('kelas__nama', 'nama'):
            kehadiran = KehadiranHarian.objects.filter(
                orang=siswa,
                tanggal__gte=tanggal_mulai,
                tanggal__lte=tanggal_selesai,
            )
            jml_hadir = kehadiran.filter(status='hadir').count()
            jml_terlambat = kehadiran.filter(status='terlambat').count()
            jml_alpa = kehadiran.filter(status='alpa').count()

            total_tercatat = jml_hadir + jml_terlambat + jml_alpa
            if total_tercatat > 0:
                persen = ((jml_hadir + jml_terlambat) / total_tercatat) * 100
            else:
                persen = 0.0

            rekap_data.append({
                'orang': siswa,
                'nama': siswa.nama,
                'kelas': siswa.kelas.nama,
                'hadir': jml_hadir,
                'terlambat': jml_terlambat,
                'alpa': jml_alpa,
                'total_hari': total_tercatat,
                'persentase': round(persen, 1),
            })

        # Paginasi (opsional, jika data sangat banyak)
        page_number = request.GET.get('page')
        paginator = Paginator(rekap_data, 50)
        page_obj = paginator.get_page(page_number)

        daftar_kelas = Kelas.objects.all().order_by('nama')

        context = {
            'rekap_data': rekap_data,
            'data_rekap': rekap_data,
            'page_obj': page_obj,
            'kelas_list': daftar_kelas,
            'daftar_kelas': daftar_kelas,
            'selected_kelas': selected_kelas,
            'kelas_terpilih': selected_kelas,
            'tanggal_dari': tanggal_mulai.isoformat(),
            'tanggal_sampai': tanggal_selesai.isoformat(),
            'tanggal_mulai': tanggal_mulai,
            'tanggal_selesai': tanggal_selesai,
            'total_hari': total_hari,
        }
        return render(request, self.template_name, context)


# ============================================================
# View: Ekspor Excel
# ============================================================

class EksporExcelView(LoginRequiredMixin, View):
    """
    Download file Excel (.xlsx) rekap kehadiran.
    Membuat dua worksheet:
    1. Ringkasan Per Siswa
    2. Detail Kehadiran Per Hari
    """

    def get(self, request):
        tanggal = hari_ini_wib()
        user = request.user
        kelas_wali = getattr(user, 'kelas_wali', None)

        tgl_dari_str = request.GET.get('tanggal_dari') or request.GET.get('tanggal_mulai')
        tgl_sampai_str = request.GET.get('tanggal_sampai') or request.GET.get('tanggal_selesai')
        kelas_param = request.GET.get('kelas')

        if tgl_dari_str:
            try:
                tanggal_mulai = datetime.date.fromisoformat(tgl_dari_str)
            except ValueError:
                tanggal_mulai = tanggal.replace(day=1)
        else:
            tanggal_mulai = tanggal.replace(day=1)

        if tgl_sampai_str:
            try:
                tanggal_selesai = datetime.date.fromisoformat(tgl_sampai_str)
            except ValueError:
                tanggal_selesai = tanggal
        else:
            tanggal_selesai = tanggal

        selected_kelas = None
        if kelas_param is not None:
            if kelas_param.isdigit():
                selected_kelas = int(kelas_param)
        elif kelas_wali:
            selected_kelas = kelas_wali.pk

        siswa_qs = Orang.objects.filter(aktif=True).select_related('kelas')
        if selected_kelas:
            siswa_qs = siswa_qs.filter(kelas_id=selected_kelas)

        data_rekap = []
        data_detail = []

        for siswa in siswa_qs.order_by('kelas__nama', 'nama'):
            kehadiran = KehadiranHarian.objects.filter(
                orang=siswa,
                tanggal__gte=tanggal_mulai,
                tanggal__lte=tanggal_selesai,
            ).order_by('tanggal')

            jml_hadir = 0
            jml_terlambat = 0
            jml_alpa = 0

            for kh in kehadiran:
                if kh.status == 'hadir':
                    jml_hadir += 1
                elif kh.status == 'terlambat':
                    jml_terlambat += 1
                elif kh.status == 'alpa':
                    jml_alpa += 1

                data_detail.append({
                    'nama': siswa.nama,
                    'kelas': siswa.kelas.nama,
                    'tanggal': kh.tanggal,
                    'status': kh.get_status_display(),
                    'jam_tap': kh.jam_tap_pertama,
                })

            total_tercatat = jml_hadir + jml_terlambat + jml_alpa
            if total_tercatat > 0:
                persen = ((jml_hadir + jml_terlambat) / total_tercatat) * 100
            else:
                persen = 0.0

            data_rekap.append({
                'nama': siswa.nama,
                'kelas': siswa.kelas.nama,
                'hadir': jml_hadir,
                'terlambat': jml_terlambat,
                'alpa': jml_alpa,
                'total_hari': total_tercatat,
                'persentase': round(persen, 1),
            })

        return buat_excel_rekap(
            data_rekap, data_detail, tanggal_mulai, tanggal_selesai
        )
