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
    print(f"{DIM}{GREEN}   v2.0-hacker  |  by anonymsh404  |  github.com/anonymsh404/Anonymsh{RESET}")
    print(f"{DIM}{GREEN}{'═' * width}{RESET}\n")


def get_device_info(serial):
    """Ambil info ringkas device (merk, model, versi Android) ala scrcpy."""
    def prop(name):
        try:
            r = subprocess.run(["adb", "-s", serial, "shell", "getprop", name],
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                text=True, timeout=5)
            return r.stdout.strip()
        except Exception:
            return ""

    manufacturer = prop("ro.product.manufacturer").capitalize()
    model = prop("ro.product.model")
    android_ver = prop("ro.build.version.release")

    name = " ".join(p for p in [manufacturer, model] if p) or "Unknown Device"
    if android_ver:
        name += f" (Android {android_ver})"
    return name


def print_device_info(serial):
    width = max(65, min(term_width(), 90))
    device_name = get_device_info(serial)
    print(f"{DIM}{GREEN}{'─' * width}{RESET}")
    print(f"{GREEN}   Device: {BRIGHT_GREEN}{BOLD}{device_name}{RESET}{GREEN}   |   Serial: {serial}{RESET}")
    print(f"{DIM}{GREEN}{'─' * width}{RESET}\n")


def log(tag, msg, color=GREEN):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{DIM}[{ts}]{RESET} {color}[{tag}]{RESET} {msg}")


def check_wireless_adb():
    log("SCAN", "Memeriksa status koneksi ADB...", CYAN)
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
    devices = []  # list of (serial, status)

    for line in lines[1:]:  # skip header "List of devices attached"
        parts = line.split()
        if len(parts) >= 2:
            devices.append((parts[0], parts[1]))

    if not devices:
        log("ERROR", "Tidak ada perangkat ADB yang terdeteksi sama sekali!", RED)
        log("HINT", "Sambungkan lewat USB, atau pairing/connect WiFi, contoh:", YELLOW)
        log("HINT", "    adb pair <IP>:<PORT>", YELLOW)
        log("HINT", "    adb connect <IP>:<PORT>", YELLOW)
        sys.exit(1)

    ready_devices = [(s, st) for s, st in devices if st == "device"]

    if not ready_devices:
        # Semua device yang terdeteksi statusnya bermasalah
        serial, status = devices[0]
        if status == "unauthorized":
            log("ERROR", f"Device {serial} berstatus UNAUTHORIZED.", RED)
            log("HINT", "Cek layar HP kamu, pasti ada popup 'Allow debugging?' "
                         "yang belum di-tap Allow.", YELLOW)
        elif status == "offline":
            log("ERROR", f"Device {serial} berstatus OFFLINE.", RED)
            log("HINT", "Koneksi terputus. Coba 'adb disconnect' lalu 'adb connect <IP>:<PORT>' lagi "
                         "(atau cabut-pasang ulang kalau USB).", YELLOW)
        else:
            log("ERROR", f"Device {serial} status tidak dikenal: {status}", RED)
        sys.exit(1)

    if len(ready_devices) == 1:
        chosen_serial = ready_devices[0][0]
    else:
        # Lebih dari satu device siap pakai (misal USB + WiFi bersamaan).
        # Prioritaskan yang BUKAN format IP:PORT (biasanya USB), karena
        # USB jauh lebih stabil & cepat dibanding WiFi untuk streaming.
        usb_like = [s for s, st in ready_devices if ":" not in s]
        chosen_serial = usb_like[0] if usb_like else ready_devices[0][0]
        log("INFO", f"Ada {len(ready_devices)} device aktif, otomatis pilih: {chosen_serial}"
                     f"{' (prioritas USB)' if usb_like else ''}", CYAN)

    log("OK", f"Terhubung ke perangkat: {BRIGHT_GREEN}{chosen_serial}{RESET}{GREEN} (status: device)", GREEN)
    print()
    return chosen_serial


def get_device_screen_size(serial):
    """Ambil resolusi asli layar device via 'adb shell wm size'."""
    try:
        result = subprocess.run(["adb", "-s", serial, "shell", "wm", "size"],
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


def _drain_stderr(proc, buffer_list, max_lines=30):
    """Baca stderr sebuah proses di thread terpisah, simpan beberapa baris
    terakhir untuk diagnosa kalau proses gagal/berhenti tanpa sebab jelas."""
    try:
        for line in iter(proc.stderr.readline, b""):
            text = line.decode(errors="ignore").rstrip()
            if text:
                buffer_list.append(text)
                if len(buffer_list) > max_lines:
                    buffer_list.pop(0)
    except Exception:
        pass


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

    def __init__(self, serial, max_dimension=720, bit_rate=8_000_000):
        self.serial = serial
        self.max_dimension = max_dimension
        self.bit_rate = bit_rate  # angka murni (bits per second), BUKAN format "8M"
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
        self.connect_start_time = None

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop = True
        self._kill_procs()

    def _kill_procs(self):
        for proc in (self._ffmpeg_proc, self._adb_proc):
            if proc is not None:
                try:
                    proc.terminate()
                except Exception:
                    pass
        time.sleep(0.2)  # beri kesempatan proses flush stderr sebelum benar-benar mati
        for proc in (self._ffmpeg_proc, self._adb_proc):
            if proc is not None and proc.poll() is None:
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
                self._set_status(f"Error: {e}", connecting=True)
            if self._stop:
                break
            time.sleep(1.5)

    def _stream_once(self):
        # Hardware encoder di beberapa device (termasuk yang dites di sini,
        # Redmi Pad 2) menolak resolusi custom sembarangan untuk H.264
        # (err=-22 / EINVAL). Saat --size tidak diisi, Android sendiri
        # otomatis fallback ke 720x1280 (portrait, width x height) waktu
        # resolusi asli gagal di-encode -- ini dikonfirmasi lewat testing
        # manual di device ini. Kita pakai ukuran itu persis.
        stream_w, stream_h = 720, 1280
        frame_size = stream_w * stream_h * 3  # BGR24 = 3 byte per piksel

        self._set_status(f"Menghubungkan stream {stream_w}x{stream_h}...", connecting=True)
        with self.lock:
            self.connect_start_time = time.time()

        adb_stderr_lines = []
        ffmpeg_stderr_lines = []

        # 1) adb: encode layar device jadi H.264 mentah, stream ke stdout
        adb_cmd = [
            "adb", "-s", self.serial, "exec-out", "screenrecord",
            "--output-format=h264",
            f"--size={stream_w}x{stream_h}",
            "--bit-rate", str(self.bit_rate),
            "-"
        ]
        self._adb_proc = subprocess.Popen(
            adb_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        threading.Thread(target=_drain_stderr, args=(self._adb_proc, adb_stderr_lines), daemon=True).start()

        # 2) ffmpeg: decode H.264 -> frame mentah BGR24
        ffmpeg_cmd = [
            "ffmpeg", "-loglevel", "error",
            "-f", "h264", "-i", "pipe:0",
            "-f", "rawvideo", "-pix_fmt", "bgr24",
            "-an", "-sn", "pipe:1"
        ]
        self._ffmpeg_proc = subprocess.Popen(
            ffmpeg_cmd,
            stdin=self._adb_proc.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        threading.Thread(target=_drain_stderr, args=(self._ffmpeg_proc, ffmpeg_stderr_lines), daemon=True).start()

        self._set_status("Live", connecting=False)

        buffer = b""
        pipe = self._ffmpeg_proc.stdout
        got_any_frame = False
        first_frame_event = threading.Event()

        def watchdog():
            # Link WiFi ADB kamu terukur lambat (~9-10 KB/s), jadi butuh waktu
            # cukup lama untuk terkumpul cukup data H.264 sebelum ffmpeg bisa
            # menghasilkan satu frame mentah utuh. Watchdog dinaikkan jadi 40
            # detik supaya tidak keburu di-kill padahal data sebenarnya masih
            # mengalir (hanya lambat, bukan macet total).
            if not first_frame_event.wait(timeout=40.0):
                self._kill_procs()

        watchdog_thread = threading.Thread(target=watchdog, daemon=True)
        watchdog_thread.start()

        while not self._stop:
            chunk = pipe.read(frame_size - len(buffer))
            if not chunk:
                break  # stream berakhir (normal, error, atau kena watchdog kill)
            buffer += chunk
            if len(buffer) >= frame_size:
                frame = np.frombuffer(buffer[:frame_size], dtype="uint8").reshape((stream_h, stream_w, 3))
                with self.lock:
                    self.latest_frame = frame.copy()
                    self.last_update_time = time.time()
                    self.error = None
                buffer = b""
                got_any_frame = True
                first_frame_event.set()
                with self.lock:
                    self.connect_start_time = None

        self._kill_procs()
        time.sleep(0.3)  # beri waktu thread stderr menangkap baris terakhir

        if not got_any_frame:
            diag = (adb_stderr_lines[-5:] or []) + (ffmpeg_stderr_lines[-5:] or [])
            diag_text = " | ".join(diag) if diag else "tidak ada output error (silent failure)"
            with self.lock:
                self.error = diag_text
            self._set_status(f"Gagal mulai stream: {diag_text[:120]}", connecting=True)
        else:
            self._set_status("Stream terputus, menyambung ulang...", connecting=True)

    def snapshot(self):
        with self.lock:
            return (
                self.latest_frame.copy() if self.latest_frame is not None else None,
                self.last_update_time,
                self.is_connecting,
                self.status_message,
                self.error,
                self.connect_start_time,
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
    device_serial = check_wireless_adb()
    print_device_info(device_serial)

    if shutil.which("ffmpeg") is None:
        log("FATAL", "ffmpeg tidak ditemukan. Install dulu: sudo apt install ffmpeg", RED)
        sys.exit(1)

    input(f"{YELLOW}Tekan [ENTER] untuk meluncurkan ANONYMSH Wireless Stream...{RESET}")
    log("BOOT", "Menjalankan stream nirkabel (mode scrcpy-like)... tekan 'q' untuk keluar.", CYAN)
    print()

    window_name = "ANONYMSH - Wireless Live Screen"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 480, 854)

    worker = StreamWorker(device_serial, max_dimension=720, bit_rate=8_000_000)
    worker.start()

    last_window_size = (480, 854)
    placeholder = np.zeros((854, 480, 3), dtype="uint8")
    last_frame_time = time.time()
    fps = 0.0
    last_logged_error = None

    try:
        while True:
            frame, last_update_time, is_connecting, status_message, error, connect_start_time = worker.snapshot()
            now = time.time()

            if error and error != last_logged_error:
                log("ERROR", f"Stream gagal: {error}", RED)
                last_logged_error = error
            elif not error:
                last_logged_error = None

            if frame is not None:
                dt = now - last_frame_time
                last_frame_time = now
                if 0 < dt < 1.0:
                    fps = (fps * 0.9) + ((1.0 / dt) * 0.1)
                display = frame
            else:
                display = placeholder.copy()
                # Tampilkan status/error, ditambah hitungan detik nunggu kalau lagi connecting
                base_text = error if error else status_message
                if connect_start_time is not None:
                    elapsed = now - connect_start_time
                    base_text = f"{base_text} ({elapsed:.0f}s)"
                text = (base_text[:70] + "...") if len(base_text) > 70 else base_text
                (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.putText(display, text, (max(10, (display.shape[1] - tw) // 2), display.shape[0] // 2),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                            (60, 60, 255) if error else (60, 220, 255), 1, cv2.LINE_AA)

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
