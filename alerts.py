"""Data sesi, suara peringatan, dan logika pengingat (postur dan istirahat mata)."""
import os

from config import (
    ABSENCE_RESET_SECONDS,
    AUDIO_DIR,
    AUDIO_EXTS,
    AUDIO_FILES,
    BREAK_DURATION,
    BREAK_INTERVAL,
    BREAK_REPEAT,
)
from posture import classify, is_away, new_history, posture_visible, smooth

try:
    import pygame   # memutar audio lokal (pip install pygame)
except ImportError:
    pygame = None

try:
    import winsound  # bawaan Windows, dipakai untuk beep cadangan
except ImportError:
    winsound = None


# ============================================================
# Langkah 4: Data sesi, suara peringatan, dan logika pengingat
# ============================================================
def new_session():
    sess = {"time_good": 0.0, "time_bad": 0.0, "breaks_done": 0,
            "posture_alerts": 0, "last_posture_alert": -1e9}
    reset_timers(sess)
    return sess


def reset_timers(sess):
    sess["screen_time"] = 0.0         # lama menatap layar sejak istirahat terakhir
    sess["bad_secs"] = 0.0            # lama postur buruk berturut-turut
    sess["alert_active"] = False      # True selama satu episode peringatan berlangsung
    sess["absent_secs"] = 0.0         # lama pengguna tidak terdeteksi
    sess["away_secs"] = 0.0           # lama berpaling saat jeda istirahat
    sess["break_state"] = "WORKING"   # WORKING atau REMINDER
    sess["last_remind"] = 0.0


def init_audio():
    """Menyalakan pemutar audio. True jika siap dipakai."""
    if pygame is None:
        print("[audio] pygame belum terpasang. Jalankan: python -m pip install pygame==2.6.1")
        return False
    try:
        pygame.mixer.init()
        print("[audio] Pemutar pygame siap.")
        return True
    except Exception as exc:
        print(f"[audio] Perangkat suara gagal dibuka: {exc}. Memakai beep.")
        return False


def find_audio(kind):
    """Mencari file suara lokal (.mp3/.wav) untuk jenis peringatan; None jika belum ada."""
    for ext in AUDIO_EXTS:
        path = os.path.join(AUDIO_DIR, AUDIO_FILES[kind] + ext)
        if os.path.exists(path):
            return path
    return None


def play_alert(kind, muted):
    """Memutar file peringatan; beep menjadi cadangan bila pemutar/file gagal."""
    if muted:
        return
    try:
        path = find_audio(kind)
        if path and pygame and pygame.mixer.get_init():
            if not pygame.mixer.music.get_busy():        # jangan tumpang tindih
                pygame.mixer.music.load(path)
                pygame.mixer.music.play()                # berjalan di latar belakang
            return
    except Exception as exc:
        print(f"[audio] Gagal memutar {kind}: {exc}. Memakai beep.")
    try:
        if winsound:
            winsound.Beep(1000 if kind == "posture" else 700, 300)
        else:
            print("\a", end="", flush=True)
    except Exception:
        pass   # kegagalan perangkat suara tidak menghentikan pemantauan kamera


def update_monitoring(sess, base, history, ind, dt, now, bad_delay, muted):
    """Memperbarui seluruh penghitung untuk satu frame.

    Mengembalikan (daftar masalah postur, apakah pengguna sedang menjauh).
    """
    issues, away = [], True

    if ind is None:
        # Pengguna tidak terdeteksi: postur tidak dinilai
        sess["absent_secs"] += dt
        if sess["break_state"] == "WORKING" and sess["absent_secs"] >= ABSENCE_RESET_SECONDS:
            reset_timers(sess)
            history.update(new_history())
    else:
        sess["absent_secs"] = 0.0
        s = smooth(history, ind)
        away = is_away(s, base)

        # Postur hanya dinilai saat bekerja (bukan saat jeda istirahat mata)
        if sess["break_state"] == "WORKING":
            issues = classify(s, base)
            if issues:
                sess["time_bad"] += dt
                sess["bad_secs"] += dt
            elif posture_visible(s):
                sess["time_good"] += dt
                sess["bad_secs"] = 0.0
            else:
                sess["bad_secs"] = 0.0   # wajah saja belum cukup untuk menilai postur baik
            if not away:
                sess["screen_time"] += dt
            if sess["bad_secs"] >= bad_delay:
                # Statistik dihitung per episode peringatan (sekali saat peringatan
                # mulai muncul), bukan per pemutaran audio yang berulang.
                if not sess["alert_active"]:
                    sess["alert_active"] = True
                    sess["posture_alerts"] += 1
                if now - sess["last_posture_alert"] >= bad_delay:
                    sess["last_posture_alert"] = now
                    # Jika kedua masalah muncul bersamaan, prioritaskan jauhi layar.
                    kind = "close" if "wajah terlalu dekat" in issues else "posture"
                    play_alert(kind, muted)
            else:
                sess["alert_active"] = False   # episode berakhir, siap dihitung lagi

    # Pengingat istirahat mata 20-20-20
    if sess["break_state"] == "WORKING":
        if sess["screen_time"] >= BREAK_INTERVAL:
            sess["break_state"] = "REMINDER"
            sess["away_secs"] = 0.0
            sess["last_remind"] = now
            play_alert("break", muted)
    else:
        sess["away_secs"] = sess["away_secs"] + dt if away else 0.0
        if sess["away_secs"] >= BREAK_DURATION:
            sess["breaks_done"] += 1
            reset_timers(sess)
        elif now - sess["last_remind"] >= BREAK_REPEAT:
            sess["last_remind"] = now
            play_alert("break", muted)

    return issues, away
