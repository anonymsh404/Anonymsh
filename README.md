# ANONYMSH — Wireless Android Mirroring Tool

Mirror layar Android ke PC secara nirkabel menggunakan ADB over WiFi, dengan tampilan terminal & overlay video bergaya hacker (REC indicator, FPS counter, HUD hijau).

![status](https://img.shields.io/badge/status-active-brightgreen) ![python](https://img.shields.io/badge/python-3.8%2B-blue)

## ✨ Fitur

- Mirroring layar Android secara real-time lewat ADB Wireless (tanpa kabel USB)
- Tampilan terminal hijau ala hacker dengan logging berwarna
- HUD overlay langsung di video: REC indicator, jam, FPS, resolusi device
- Auto-resize menjaga aspect ratio asli device
- Deteksi status device (unauthorized / offline) dengan pesan error yang jelas

## 📋 Requirements

- Python 3.8+
- [ADB (Android Platform Tools)](https://developer.android.com/tools/releases/platform-tools) terpasang & ada di PATH
- Android device dengan **Wireless debugging** aktif (Developer Options)
- Koneksi WiFi yang sama antara PC dan device

## 🚀 Instalasi

```bash
git clone https://github.com/<username>/anonymsh.git
cd anonymsh
pip install -r requirements.txt
```

Kalau muncul error `externally-managed-environment` (Debian/Kali/Ubuntu terbaru):

```bash
pip install -r requirements.txt --break-system-packages
```

## 🔧 Persiapan Wireless ADB

1. Di HP: **Settings → Developer Options → Wireless debugging** → aktifkan
2. Pairing pertama kali:
   ```bash
   adb pair <IP>:<PAIRING_PORT>
   ```
3. Connect:
   ```bash
   adb connect <IP>:<PORT>
   ```
4. Verifikasi:
   ```bash
   adb devices
   ```
   Pastikan statusnya `device`, bukan `unauthorized` atau `offline`.

> **Catatan untuk device Xiaomi/Redmi/POCO (MIUI/HyperOS):** aktifkan juga toggle **"USB debugging (Security settings)"** di Developer Options, terpisah dari toggle "USB debugging" biasa. Tanpa ini, perintah seperti `screencap` bisa gagal diam-diam.

## ▶️ Menjalankan

```bash
python3 anonymsh.py
```

Tekan `q` di jendela video untuk keluar.

## 🐛 Troubleshooting

| Gejala | Kemungkinan Penyebab | Solusi |
|---|---|---|
| `ModuleNotFoundError: No module named 'cv2'` | opencv-python belum terinstall | `pip install opencv-python --break-system-packages` |
| `QStandardPaths: error creating runtime directory` | `XDG_RUNTIME_DIR` tidak valid | `export XDG_RUNTIME_DIR=/tmp/runtime-$(id -u) && mkdir -p $XDG_RUNTIME_DIR && chmod 700 $XDG_RUNTIME_DIR` |
| Timeout terus-menerus saat capture | WiFi lambat / device sleep | Pastikan layar HP nyala, gunakan WiFi 5GHz, aktifkan "Stay awake" di Developer Options |
| `screencap` menghasilkan file 0 bytes | Restriksi OEM (MIUI/HyperOS dll) | Aktifkan "USB debugging (Security settings)" di Developer Options |
| Device `unauthorized` | Popup izin di HP belum di-tap | Cek layar HP, tap "Allow" pada dialog USB/Wireless debugging |
| Device `offline` | Koneksi WiFi terputus | `adb disconnect` lalu `adb connect <IP>:<PORT>` ulang |

## ⚠️ Disclaimer

Tool ini hanya untuk mirroring device milik sendiri yang sudah kamu setujui (Developer Options + Wireless debugging harus diaktifkan manual oleh pemilik device). Gunakan secara bertanggung jawab.

## 📄 Lisensi

MIT License — bebas digunakan, dimodifikasi, dan didistribusikan ulang.
