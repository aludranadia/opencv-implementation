"""Kalibrasi, smoothing, dan penentuan status postur."""
import numpy as np

from config import (
    AWAY_FACE_RATIO,
    AWAY_YAW_DELTA,
    CALIBRATION_MIN_VALID,
    CHIN_DROP_DELTA,
    EYE_DROP_DELTA,
    HEAD_PITCH_DELTA,
    HEAD_ROLL_DELTA,
    INDICATORS,
    MAX_FACE_RATIO,
    NECK_CHANGE_RATIO,
    SHOULDER_DROP,
    SHOULDER_TILT_DELTA,
    SMOOTH_WINDOW,
)

# ============================================================
# Langkah 3: Kalibrasi, smoothing, dan penentuan status postur
# ============================================================
def build_baseline(samples):
    """Acuan postur pribadi = nilai median setiap indikator saat kalibrasi."""
    baseline = {}
    for key in ("head", "tilt", "sh_y", "face", "yaw"):
        baseline[key] = float(np.median([s[key] for s in samples]))
    ears = [s["ear"] for s in samples if s["ear"] is not None]
    baseline["ear"] = float(np.median(ears)) if len(ears) >= len(samples) / 2 else None
    for key in ("chin", "eye_sh", "pitch", "roll", "yaw_deg", "face_scale"):
        baseline[key] = float(np.median([s[key] for s in samples]))
    return baseline

def calibration_sample_valid(ind):
    """Kalibrasi memerlukan wajah atas, dagu, dan kedua bahu yang terbaca."""
    return (ind is not None and all(ind.get(k) is not None and np.isfinite(ind[k])
                                   for k in INDICATORS if k != "ear")
            and ind["face_scale"] > 0)

def calibration_motion_issue(samples):
    """Periksa gerakan setiap sampel baru, tanpa menunggu hitungan selesai."""
    if len(samples) < 2:
        return None
    limits = {"pitch": 8.0, "roll": 6.0, "yaw_deg": 12.0, "tilt": 6.0,
              "chin": 0.06, "eye_sh": 0.06, "sh_y": 0.04, "face_scale": 0.10}
    for key, limit in limits.items():
        values = np.array([s[key] for s in samples], np.float64)
        previous = float(np.median(values[:-1]))
        if key == "face_scale":
            latest_change = abs(values[-1] - previous) / max(abs(previous), 1e-6)
            values = values / max(float(np.median(values)), 1e-6)
        else:
            latest_change = abs(values[-1] - previous)
        if (latest_change > limit
                or float(np.percentile(values, 90) - np.percentile(values, 10)) > limit):
            return "Terlalu banyak gerakan. Ulangi sambil diam."
    return None

def calibration_issue(samples, total):
    """Alasan kalibrasi ditolak, atau None bila sampel cukup dan relatif stabil."""
    if total <= 0 or len(samples) < 20 or len(samples) / total < CALIBRATION_MIN_VALID:
        return "Ulangi: wajah, dagu, dan bahu harus terlihat."
    motion_issue = calibration_motion_issue(samples)
    if motion_issue:
        return motion_issue
    base = build_baseline(samples)
    if abs(base["roll"]) > HEAD_ROLL_DELTA or base["tilt"] > 8:
        return "Ulangi: luruskan kepala dan ratakan bahu."
    if abs(base["yaw_deg"]) > 15 or abs(base["pitch"]) > 35:
        return "Ulangi: hadapkan wajah ke kamera."
    # Posisi membungkuk yang stabil tidak bisa dipastikan dari kamera depan saja.
    return None

def face_size_ratio(s, base):
    """Ukuran wajah saat ini dibanding acuan kalibrasi (1.0 = sama dengan acuan).

    Bukan sensor kedalaman dan bukan jarak dalam cm. Akurasi bergantung pada
    sudut wajah dan landmark; jangan pindahkan kamera setelah kalibrasi.
    """
    if s is None or s.get("face_scale") is None or s["face_scale"] <= 0:
        return None
    return s["face_scale"] / base["face_scale"]

def posture_visible(s):
    return s is not None and all(s.get(k) is not None
                                 for k in ("head", "tilt", "sh_y", "chin", "pitch", "roll"))

def new_history():
    return {key: [] for key in INDICATORS}

def smooth(history, ind):
    """Rata-rata bergerak (beberapa frame terakhir) untuk mengurangi jitter."""
    out = {}
    for key, value in ind.items():
        if value is None:
            history[key].clear()   # jangan memakai sudut/dagu lama saat tracking hilang
            out[key] = None
            continue
        if value is not None:
            history[key].append(value)
            history[key] = history[key][-SMOOTH_WINDOW:]
        out[key] = sum(history[key]) / len(history[key]) if history[key] else None
    return out

def classify(s, base):
    """Mengembalikan daftar masalah postur dibanding acuan kalibrasi."""
    issues = []
    pitch_delta = s["pitch"] - base["pitch"] if s.get("pitch") is not None else None
    roll_delta = s["roll"] - base["roll"] if s.get("roll") is not None else None
    head_down = pitch_delta is not None and pitch_delta > HEAD_PITCH_DELTA
    head_tilt = roll_delta is not None and abs(roll_delta) > HEAD_ROLL_DELTA
    if head_down:
        issues.append("kepala menunduk")
    if head_tilt:
        issues.append("kepala miring")

    if s["tilt"] is not None and abs(s["tilt"] - base["tilt"]) > SHOULDER_TILT_DELTA:
        issues.append("bahu miring")

    # Bahu turun dan dagu turun sama-sama menjadi indikasi badan membungkuk.
    shoulder_down = s["sh_y"] is not None and (s["sh_y"] - base["sh_y"]) > SHOULDER_DROP
    shoulder_hunch = False
    if base["ear"] is not None and abs(base["ear"]) > 1e-6 and s["ear"] is not None:
        neck_ratio = s["ear"] / base["ear"]
        shoulder_down = shoulder_down or neck_ratio > 1 + NECK_CHANGE_RATIO
        shoulder_hunch = (neck_ratio < 1 - NECK_CHANGE_RATIO and pitch_delta is not None
                          and abs(pitch_delta) < HEAD_PITCH_DELTA and not head_tilt)
    # Dagu dan mata ikut turun terhadap bahu, meskipun bahu tertahan lengan di meja.
    # Gerakan mengangguk/menunduk dipisahkan lewat pitch wajah atas; rahang terbuka
    # saja tidak cukup karena posisi mata juga harus turun.
    chin_hunch = (posture_visible(s) and abs(pitch_delta) < HEAD_PITCH_DELTA
                  and not head_tilt and base["chin"] - s["chin"] > CHIN_DROP_DELTA
                  and base["eye_sh"] - s["eye_sh"] > EYE_DROP_DELTA)
    if shoulder_down or shoulder_hunch or chin_hunch:
        issues.append("badan membungkuk")

    ratio = face_size_ratio(s, base)
    if ratio is not None and ratio > MAX_FACE_RATIO:
        issues.append("wajah terlalu dekat")
    return issues

def is_away(s, base):
    """Pengguna dianggap menjauh/berpaling dari layar."""
    return (s["face"] < base["face"] * AWAY_FACE_RATIO
            or abs(s["yaw"] - base["yaw"]) > AWAY_YAW_DELTA)