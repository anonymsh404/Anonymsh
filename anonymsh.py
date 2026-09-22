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


def get_device_screen_size():
    """Ambil resolusi asli layar device via 'adb shell wm size'."""
    try:
        result = subprocess.run(["adb", "shell", "wm", "size"],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 text=True, timeout=10)
    except Exception:
        return None

    text = result.stdout
    # Prioritaskan "Override size" kalau ada, fallback ke "Physical size"
    override = None
    physical = None
    for line in text.splitlines():
        if "Override size:" in line:
            override = line.split(":")[1].strip()
        elif "Physical size:" in line:
            physical = line.split(":")[1].strip()

    size_str = override or physical
    if not size_str or "x" not in size_str:
        return None

    try:
        w, h = size_str.lower().split("x")
        return int(w), int(h)
    except ValueError:
        return None


def compute_stream_size(native_w, native_h, max_dimension=720):
    """Hitung ukuran streaming yang di-downscale, tetap menjaga aspect ratio,
    dan dibulatkan ke angka genap (disyaratkan encoder H.264)."""
    if native_w >= native_h:
        scale = max_dimension / native_w
    else:
        scale = max_dimension / native_h
    scale = min(scale, 1.0)
    w = int(native_w * scale)
    h = int(native_h * scale)
    w -= w % 2
    h -= h % 2
    return max(w, 2), max(h, 2)


class StreamWorker:
    """
    Meniru cara kerja scrcpy: menjalankan 'adb shell screenrecord' yang
    encode video H.264 langsung di device (jauh lebih ringan lewat WiFi
    dibanding screenshot PNG berulang), lalu men-decode stream tersebut
    lewat ffmpeg menjadi frame mentah (BGR) yang bisa ditampilkan OpenCV.

    Berjalan sebagai thread terpisah supaya window video tetap responsif.
    'screenrecord' punya batas waktu per sesi di banyak versi Android,
    jadi worker ini otomatis me-restart pipeline kalau stream berhenti.
    """

    def __init__(self, max_dimension=720, bit_rate="8M"):
        self.max_dimension = max_dimension
        self.bit_rate = bit_rate
        self.lock = threading.Lock()
        self.latest_frame = None
        self.last_update_time = None
        self.is_connecting = True
        self.status_message = "Menghubungkan..."
        self.error = None
        self._stop = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._adb_proc = None
        self._ffmpeg_proc = None

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop = True
        self._kill_procs()

    def _kill_procs(self):
        for proc in (self._ffmpeg_proc, self._adb_proc):
            if proc is not None:
                try:
                    proc.kill()
                except Exception:
                    pass

    def _set_status(self, msg, connecting=True):
        with self.lock:
            self.status_message = msg
            self.is_connecting = connecting

    def _run(self):
        while not self._stop:
            try:
                self._stream_once()
            except Exception as e:
                with self.lock:
                    self.error = str(e)
            if self._stop:
                break
            self._set_status("Stream terputus, menyambung ulang...", connecting=True)
            time.sleep(1.0)

    def _stream_once(self):
        self._set_status("Membaca resolusi device...", connecting=True)
        size = get_device_screen_size()
        if size is None:
            self._set_status("Gagal baca resolusi device (adb shell wm size gagal)", connecting=True)
            time.sleep(2.0)
            return

        native_w, native_h = size
        stream_w, stream_h = compute_stream_size(native_w, native_h, self.max_dimension)
        frame_size = stream_w * stream_h * 3  # BGR24 = 3 byte per piksel

        self._set_status(f"Menghubungkan stream {stream_w}x{stream_h}...", connecting=True)

        # 1) adb: encode layar device jadi H.264 mentah, stream ke stdout
        adb_cmd = [
            "adb", "exec-out", "screenrecord",
            "--output-format=h264",
            f"--size={stream_w}x{stream_h}",
            f"--bit-rate={self.bit_rate}",
            "-"
        ]
        self._adb_proc = subprocess.Popen(
            adb_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )

        # 2) ffmpeg: decode H.264 -> frame mentah BGR24
        ffmpeg_cmd = [
            "ffmpeg", "-loglevel", "quiet",
            "-f", "h264", "-i", "pipe:0",
            "-f", "rawvideo", "-pix_fmt", "bgr24",
            "-an", "-sn", "pipe:1"
        ]
        self._ffmpeg_proc = subprocess.Popen(
            ffmpeg_cmd,
            stdin=self._adb_proc.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )

        self._set_status("Live", connecting=False)

        buffer = b""
        pipe = self._ffmpeg_proc.stdout
        while not self._stop:
            chunk = pipe.read(frame_size - len(buffer))
            if not chunk:
                break  # stream berakhir (screenrecord kena limit waktu / device disconnect)
            buffer += chunk
            if len(buffer) >= frame_size:
                frame = np.frombuffer(buffer[:frame_size], dtype="uint8").reshape((stream_h, stream_w, 3))
                with self.lock:
                    self.latest_frame = frame.copy()
                    self.last_update_time = time.time()
                    self.error = None
                buffer = b""

        self._kill_procs()

    def snapshot(self):
        with self.lock:
            return (
                self.latest_frame.copy() if self.latest_frame is not None else None,
                self.last_update_time,
                self.is_connecting,
                self.status_message,
                self.error,
            )


SPINNER_FRAMES = ["|", "/", "-", "\\"]


def draw_hacker_hud(frame, fps, is_connecting, status_message):
    """Overlay HUD hijau ala hacker di atas frame video."""
    h, w = frame.shape[:2]
    overlay = frame.copy()

    cv2.rectangle(overlay, (0, 0), (w, 40), (0, 0, 0), -1)
    frame = cv2.addWeighted(overlay, 0.55, frame, 0.45, 0)

    green = (60, 255, 60)
    yellow = (60, 220, 255)
    red = (40, 40, 255)

    if is_connecting:
        spin = SPINNER_FRAMES[int(time.time() * 4) % len(SPINNER_FRAMES)]
        cv2.circle(frame, (18, 20), 6, yellow, -1)
        cv2.putText(frame, f"{spin} {status_message}", (30, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.5, yellow, 1, cv2.LINE_AA)
    else:
        # REC indicator berkedip saat live
        if int(time.time() * 2) % 2 == 0:
            cv2.circle(frame, (18, 20), 6, red, -1)
        cv2.putText(frame, "LIVE", (30, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, green, 1, cv2.LINE_AA)

    text_right = f"{datetime.now().strftime('%H:%M:%S')}  |  {fps:.1f} FPS  |  {w}x{h}"
    (tw, th), _ = cv2.getTextSize(text_right, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    cv2.putText(frame, text_right, (w - tw - 12, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.5, green, 1, cv2.LINE_AA)

    border_color = yellow if is_connecting else green
    cv2.line(frame, (0, 40), (w, 40), border_color, 1)
    cv2.rectangle(frame, (0, 0), (w - 1, h - 1), border_color, 1)

    return frame


def main():
    banner()
    check_wireless_adb()

    if shutil.which("ffmpeg") is None:
        log("FATAL", "ffmpeg tidak ditemukan. Install dulu: sudo apt install ffmpeg", RED)
        sys.exit(1)

    input(f"{YELLOW}Tekan [ENTER] untuk meluncurkan ANONYMSH Wireless Stream...{RESET}")
    log("BOOT", "Menjalankan stream nirkabel (mode scrcpy-like)... tekan 'q' untuk keluar.", CYAN)
    print()

    window_name = "ANONYMSH - Wireless Live Screen"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 480, 854)

    worker = StreamWorker(max_dimension=720, bit_rate="8M")
    worker.start()

    last_window_size = (480, 854)
    placeholder = np.zeros((854, 480, 3), dtype="uint8")
    last_frame_time = time.time()
    fps = 0.0

    try:
        while True:
            frame, last_update_time, is_connecting, status_message, error = worker.snapshot()
            now = time.time()

            if frame is not None:
                dt = now - last_frame_time
                last_frame_time = now
                if 0 < dt < 1.0:
                    fps = (fps * 0.9) + ((1.0 / dt) * 0.1)
                display = frame
            else:
                display = placeholder.copy()
                text = status_message
                (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
                cv2.putText(display, text, ((display.shape[1] - tw) // 2, display.shape[0] // 2),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (60, 220, 255), 1, cv2.LINE_AA)

            frame_hud = draw_hacker_hud(display, fps, is_connecting, status_message)

            current_size = (frame_hud.shape[1], frame_hud.shape[0])
            if current_size != last_window_size:
                cv2.resizeWindow(window_name, current_size[0], current_size[1])
                last_window_size = current_size

            cv2.imshow(window_name, frame_hud)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                log("EXIT", "Menutup ANONYMSH...", RED)
                break

    except KeyboardInterrupt:
        log("EXIT", "Dihentikan oleh user (Ctrl+C).", RED)
    finally:
        worker.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
