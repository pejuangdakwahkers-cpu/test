---
title: Sistem Absensi RFID Sekolah
emoji: 🏫
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Sistem Absensi RFID Sekolah

Sistem absensi berbasis kartu RFID/NFC untuk sekolah dengan ESP32 + RC522.

## Akun Bawaan (Pengujian)

| Peran | Username | Password |
|---|---|---|
| **Admin** | `admin` | `admin123` |
| **Wali Kelas** | `guru_wali1` | `guru123` |
| **Guru Biasa** | `guru_biasa` | `guru123` |

## Endpoint API ESP32

- **URL:** `/api/scan`
- **Method:** `POST`
- **Header:** `X-API-Key: test-api-key-12345`
- **Body:** `{"uid": "04A1B2C3D4E580", "card_code": "SIS0001", "device": "gate-1"}`
