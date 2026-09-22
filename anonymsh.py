import subprocess
import cv2
import numpy as np
import sys
import os
import time
import shutil
import random
import threading
from datetime import datetime

# ============================================================
#  ANONYMSH - Wireless Android Mirroring Tool (Hacker Edition)
# ============================================================

# ---------- Warna terminal ----------
GREEN = "\033[1;32m"
BRIGHT_GREEN = "\033[1;92m"
RED = "\033[1;31m"
CYAN = "\033[1;36m"
YELLOW = "\033[1;33m"
DIM = "\033[2m"
RESET = "\033[0m"
BOLD = "\033[1m"


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def term_width():
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return 65


def type_effect(text, delay=0.002, color=GREEN):
    for ch in text:
        sys.stdout.write(f"{color}{ch}{RESET}")
        sys.stdout.flush()
        time.sleep(delay)
    print()


def banner():
    clear_screen()
    width = max(65, min(term_width(), 90))
    print(GREEN)
    print(r"""
      █████╗ ███╗   ██╗ ██████╗ ███╗   ██╗██╗   ██╗███╗   ███╗███████╗██╗  ██╗
     ██╔══██╗████╗  ██║██╔═══██╗████╗  ██║╚██╗ ██╔╝████╗ ████║██╔════╝██║  ██║
     ███████║██╔██╗ ██║██║   ██║██╔██╗ ██║ ╚████╔╝ ██╔████╔██║███████╗███████║
     ██╔══██║██║╚██╗██║██║   ██║██║╚██╗██║  ╚██╔╝  ██║╚██╔╝██║╚════██║██╔══██║
     ██║  ██║██║ ╚████║╚██████╔╝██║ ╚████║   ██║   ██║ ╚═╝ ██║███████║██║  ██║
     ╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═══╝   ╚═╝   ╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝
    """)
    print(RESET, end="")
    print(f"{DIM}{GREEN}{'═' * width}{RESET}")
    print(f"{BRIGHT_GREEN}{BOLD}   [ ANONYMSH ]{RESET}{GREEN} :: Wireless Android Screen Mirroring{RESET}")
    print(f"{DIM}{GREEN}   build: v2.0-hacker  |  mode: ADB-over-WiFi  |  status: STANDBY{RESET}")
    print(f"{DIM}{GREEN}{'═' * width}{RESET}\n")


def log(tag, msg, color=GREEN):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{DIM}[{ts}]{RESET} {color}[{tag}]{RESET} {msg}")


def check_wireless_adb():
    log("SCAN", "Memeriksa status koneksi ADB Nirkabel...", CYAN)
    try:
        result = subprocess.run(["adb", "devices"], stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True, timeout=10)
    except FileNotFoundError:
        log("FATAL", "Perintah 'adb' tidak ditemukan. Pastikan Android Platform-Tools sudah "
                      "terinstall dan ada di PATH.", RED)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        log("FATAL", "adb tidak merespon (timeout). Coba jalankan 'adb kill-server' lalu ulangi.", RED)
        sys.exit(1)

    print(f"{DIM}{result.stdout}{RESET}")

    lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
    device_serial = None
    device_status = None

    for line in lines[1:]:  # skip header "List of devices attached"
        parts = line.split()
        if len(parts) >= 2:
            serial, status = parts[0], parts[1]
            device_serial = serial
            device_status = status
            break  # ambil device pertama yang terdeteksi

    if device_serial is None:
        log("ERROR", "Tidak ada perangkat ADB yang terdeteksi sama sekali!", RED)
        log("HINT", "Pastikan sudah pairing & connect, contoh:", YELLOW)
        log("HINT", "    adb pair <IP>:<PORT>", YELLOW)
        log("HINT", "    adb connect <IP>:<PORT>", YELLOW)
        sys.exit(1)

    if device_status == "unauthorized":
        log("ERROR", f"Device {device_serial} berstatus UNAUTHORIZED.", RED)
        log("HINT", "Cek layar HP kamu, pasti ada popup 'Allow USB/Wireless debugging?' "
                     "yang belum di-tap Allow.", YELLOW)
        sys.exit(1)

    if device_status == "offline":
        log("ERROR", f"Device {device_serial} berstatus OFFLINE.", RED)
        log("HINT", "Koneksi WiFi putus. Coba 'adb disconnect' lalu 'adb connect <IP>:<PORT>' lagi.", YELLOW)
        sys.exit(1)

    if device_status != "device":
        log("ERROR", f"Device {device_serial} status tidak dikenal: {device_status}", RED)
        sys.exit(1)

    log("OK", f"Terhubung ke perangkat: {BRIGHT_GREEN}{device_serial}{RESET}{GREEN} (status: {device_status})", GREEN)
    print()
    return device_serial


def capture_screen(timeout=60.0):
    """
    Mengambil screenshot via adb exec-out screencap -p.
    Mengembalikan (frame, error_message).
    Catatan: di device beresolusi tinggi + WiFi lambat, satu capture
    bisa makan waktu puluhan detik. timeout default dinaikkan supaya
    tidak dianggap 'gagal' padahal cuma lambat.
    """
    try:
        process = subprocess.run(
            ["adb", "exec-out", "screencap", "-p"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return None, f"timeout {timeout:.0f}s (koneksi WiFi lemot / resolusi device tinggi)"
    except FileNotFoundError:
        return None, "adb tidak ditemukan"

    if process.returncode != 0:
        err = process.stderr.decode(errors="ignore").strip()
        return None, f"adb error: {err or 'unknown'}"

    if not process.stdout:
        return None, "stdout kosong (kemungkinan device sleep/layar mati)"

    raw = np.frombuffer(process.stdout, dtype="uint8")
    image = cv2.imdecode(raw, cv2.IMREAD_COLOR)

    if image is None:
        return None, "gagal decode PNG (data korup / terpotong saat transfer WiFi)"

    return image, None


class CaptureWorker:
    """
    Menjalankan capture_screen() di thread terpisah secara terus-menerus,
    supaya jendela video tetap hidup & responsif walau satu capture
    butuh waktu lama (device resolusi tinggi via WiFi lambat).
    """

    def __init__(self, capture_timeout=60.0):
        self.capture_timeout = capture_timeout
        self.lock = threading.Lock()
        self.latest_frame = None
        self.latest_error = None
        self.last_update_time = None
        self.is_capturing = False
        self.consecutive_failures = 0
        self._stop = False
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop = True

    def _run(self):
        while not self._stop:
            with self.lock:
                self.is_capturing = True
            frame, err = capture_screen(timeout=self.capture_timeout)
            with self.lock:
                self.is_capturing = False
                if frame is not None:
                    self.latest_frame = frame
                    self.latest_error = None
                    self.last_update_time = time.time()
                    self.consecutive_failures = 0
                else:
                    self.latest_error = err
                    self.consecutive_failures += 1

    def snapshot(self):
        """Ambil salinan state terbaru secara thread-safe."""
        with self.lock:
            return (
                self.latest_frame.copy() if self.latest_frame is not None else None,
                self.latest_error,
                self.last_update_time,
                self.is_capturing,
                self.consecutive_failures,
            )


def resize_keep_aspect(frame, target_height=960):
    h, w = frame.shape[:2]
    scale = target_height / h
    new_w = int(w * scale)
    return cv2.resize(frame, (new_w, target_height), interpolation=cv2.INTER_AREA)


SPINNER_FRAMES = ["|", "/", "-", "\\"]


def draw_hacker_hud(frame, resolution_text, is_capturing, last_update_time, consecutive_failures):
    """Overlay HUD hijau ala hacker di atas frame video."""
    h, w = frame.shape[:2]
    overlay = frame.copy()

    # Bar atas semi transparan
    cv2.rectangle(overlay, (0, 0), (w, 40), (0, 0, 0), -1)
    frame = cv2.addWeighted(overlay, 0.55, frame, 0.45, 0)

    green = (60, 255, 60)
    yellow = (60, 220, 255)
    red = (40, 40, 255)

    cv2.putText(frame, "ANONYMSH LIVE", (12, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, green, 1, cv2.LINE_AA)

    # Status capturing (spinner) di tengah
    if is_capturing:
        spin = SPINNER_FRAMES[int(time.time() * 4) % len(SPINNER_FRAMES)]
        status_text = f"{spin} MENGAMBIL FRAME BARU..."
        status_color = yellow
    elif consecutive_failures > 0:
        status_text = f"! GAGAL {consecutive_failures}x BERTURUT-TURUT"
        status_color = red
    else:
        status_text = "STANDBY"
        status_color = green

    (stw, _), _ = cv2.getTextSize(status_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    cv2.putText(frame, status_text, ((w - stw) // 2, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.5, status_color, 1, cv2.LINE_AA)

    # Info kanan: waktu sekarang + kapan terakhir update + resolusi
    ts = datetime.now().strftime("%H:%M:%S")
    if last_update_time is not None:
        age = time.time() - last_update_time
        age_text = f"update {age:.0f}s lalu"
    else:
        age_text = "belum ada frame"
    text_right = f"{ts}  |  {age_text}  |  {resolution_text}"
    (tw, th), _ = cv2.getTextSize(text_right, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    cv2.putText(frame, text_right, (w - tw - 12, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.5, green, 1, cv2.LINE_AA)

    # Garis scan hijau tipis di bawah bar
    cv2.line(frame, (0, 40), (w, 40), green, 1)

    # Border tipis di sekeliling frame (kuning kalau lagi capturing, hijau kalau standby)
    border_color = yellow if is_capturing else green
    cv2.rectangle(frame, (0, 0), (w - 1, h - 1), border_color, 1)

    return frame


def main():
    banner()
    check_wireless_adb()

    input(f"{YELLOW}Tekan [ENTER] untuk meluncurkan ANONYMSH Wireless Stream...{RESET}")
    log("BOOT", "Menjalankan stream nirkabel... tekan 'q' di jendela video untuk keluar.", CYAN)
    print()

    window_name = "ANONYMSH - Wireless Live Screen"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    consecutive_failures = 0
    max_failures_before_warning = 20
    last_frame_time = time.time()
    fps = 0.0
    last_resolution_text = "N/A"

    try:
        while True:
            frame, err = capture_screen(timeout=2.0)
            now = time.time()

            if frame is not None:
                consecutive_failures = 0

                dt = now - last_frame_time
                last_frame_time = now
                if dt > 0:
                    fps = (fps * 0.8) + ((1.0 / dt) * 0.2)  # smoothing

                orig_h, orig_w = frame.shape[:2]
                last_resolution_text = f"{orig_w}x{orig_h}"

                frame_resized = resize_keep_aspect(frame, target_height=960)
                frame_hud = draw_hacker_hud(frame_resized, fps, last_resolution_text)

                cv2.imshow(window_name, frame_hud)
            else:
                consecutive_failures += 1
                if consecutive_failures == 1 or consecutive_failures % max_failures_before_warning == 0:
                    log("WARN", f"Gagal ambil frame: {err} (gagal berturut-turut: {consecutive_failures})", YELLOW)
                time.sleep(0.15)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                log("EXIT", "Menutup ANONYMSH...", RED)
                break

    except KeyboardInterrupt:
        log("EXIT", "Dihentikan oleh user (Ctrl+C).", RED)
    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
