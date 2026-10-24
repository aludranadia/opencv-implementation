"""Deteksi landmark (Pose + Face Mesh) dan penghitungan indikator postur."""
import math

import cv2
import numpy as np

from config import (
    FACE_LANDMARKS,
    HEAD_POSE_NAMES,
    LANDMARKS,
    UPPER_FACE_MODEL,
    VISIBILITY_MIN,
)


# ============================================================
# Langkah 2: Deteksi landmark dan ekstraksi fitur postur
# ============================================================
def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def get_points(results, w, h, face_results=None):
    """Landmark dalam piksel; wajah tetap dipantau saat bahu keluar dari frame."""
    lm = results.pose_landmarks.landmark if results.pose_landmarks else None
    pts = {}
    for name, idx in LANDMARKS.items():
        p = lm[idx] if lm is not None else None
        pts[name] = ((p.x * w, p.y * h) if p is not None
                     and p.visibility >= VISIBILITY_MIN
                     and 0 <= p.x <= 1 and 0 <= p.y <= 1 else None)
    for name in FACE_LANDMARKS:
        pts[name] = None
    if face_results and face_results.multi_face_landmarks:
        face = face_results.multi_face_landmarks[0].landmark
        for name, idx in FACE_LANDMARKS.items():
            p = face[idx]
            if 0 <= p.x <= 1 and 0 <= p.y <= 1:
                pts[name] = (p.x * w, p.y * h)
        # Sudut mata Face Mesh lebih stabil untuk ukuran wajah dan kepala miring.
        for name, face_name in (("nose", "face_nose"), ("l_eye", "face_l_eye"),
                                ("r_eye", "face_r_eye")):
            if pts[face_name] is not None:
                pts[name] = pts[face_name]
    if any(pts[k] is None for k in ("nose", "l_eye", "r_eye")):
        return None
    return pts


def upper_face_angles(pts, w, h):
    """Perkiraan pitch/yaw dari wajah atas, tanpa memakai dagu untuk menunduk.

    Intrinsik kamera merupakan pendekatan; perubahan sudut dibandingkan dengan
    kalibrasi pribadi. Hasil ini bukan pengukuran sudut anatomis leher.
    """
    if any(pts.get(name) is None for name in HEAD_POSE_NAMES):
        return None
    image_points = np.array([pts[name] for name in HEAD_POSE_NAMES], np.float64)
    focal = float(max(w, h))
    camera = np.array(((focal, 0, w / 2), (0, focal, h / 2), (0, 0, 1)), np.float64)
    distortion = np.zeros(4, np.float64)
    try:
        ok, rvec, tvec = cv2.solvePnP(UPPER_FACE_MODEL, image_points, camera,
                                     distortion, flags=cv2.SOLVEPNP_SQPNP)
        if not ok or not np.isfinite(tvec).all() or tvec[2, 0] <= 0:
            return None
        rotation, _ = cv2.Rodrigues(rvec)
        pitch = math.degrees(math.atan2(rotation[2, 1], rotation[2, 2]))
        yaw = math.degrees(math.atan2(-rotation[2, 0],
                                      math.hypot(rotation[0, 0], rotation[1, 0])))
        projected, _ = cv2.projectPoints(UPPER_FACE_MODEL, rvec, tvec, camera, distortion)
        error = float(np.sqrt(np.mean(np.sum((projected[:, 0] - image_points) ** 2, axis=1))))
        eye_width = dist(pts["face_l_eye"], pts["face_r_eye"])
        if error > eye_width * 0.10 or abs(pitch) > 60 or abs(yaw) > 60:
            return None
        return pitch, yaw
    except (cv2.error, ValueError, FloatingPointError):
        return None


def compute_indicators(pts, frame_width, frame_height):
    """Menghitung indikator postur dari koordinat landmark.

    head : jarak vertikal hidung ke garis bahu (dinormalisasi lebar bahu)
    tilt : sudut kemiringan garis bahu (derajat)
    ear  : jarak vertikal telinga ke garis bahu (dinormalisasi lebar bahu)
    sh_y : posisi vertikal bahu relatif terhadap tinggi frame (makin besar =
           bahu makin turun di dalam gambar)
    face : lebar wajah (jarak kedua mata) relatif terhadap lebar frame.
           TIDAK dinormalisasi lebar bahu, karena lebar bahu ikut berubah
           saat pengguna mendekat ke kamera sehingga rasionya tidak berubah.
    yaw  : arah wajah (pergeseran hidung terhadap titik tengah mata)
    chin : tinggi dagu terhadap bahu; dipakai untuk indikasi badan membungkuk
    eye_sh : tinggi mata terhadap bahu untuk membedakan dagu turun dan rahang buka
    pitch/roll : menunduk dan miringnya kepala, terpisah dari kemiringan bahu
    face_scale : lebar mata terkoreksi yaw, dibandingkan dengan acuan kalibrasi
                 untuk mendeteksi wajah yang terlalu dekat
    """
    l_sh, r_sh = pts["l_sh"], pts["r_sh"]
    l_eye, r_eye = pts["l_eye"], pts["r_eye"]
    shoulder_width = dist(l_sh, r_sh) if l_sh is not None and r_sh is not None else 0
    eye_width = dist(l_eye, r_eye)
    if eye_width < 1:
        return None

    body_ok = shoulder_width >= 1
    shoulder_mid_y = (l_sh[1] + r_sh[1]) / 2 if body_ok else None
    ear = None
    if body_ok and pts["l_ear"] and pts["r_ear"]:
        ear_mid_y = (pts["l_ear"][1] + pts["r_ear"][1]) / 2
        ear = (shoulder_mid_y - ear_mid_y) / shoulder_width

    eye_mid_x = (l_eye[0] + r_eye[0]) / 2
    eye_mid_y = (l_eye[1] + r_eye[1]) / 2
    angles = upper_face_angles(pts, frame_width, frame_height)
    pitch, yaw_deg = angles if angles is not None else (None, None)
    eye_left, eye_right = sorted((l_eye, r_eye), key=lambda p: p[0])
    roll = math.degrees(math.atan2(eye_right[1] - eye_left[1],
                                   eye_right[0] - eye_left[0]))
    face_scale = None
    if angles is not None and abs(yaw_deg) <= 25 and abs(pitch) <= 35:
        face_scale = eye_width / frame_width / math.cos(math.radians(yaw_deg))
    return {
        "head": (shoulder_mid_y - pts["nose"][1]) / shoulder_width if body_ok else None,
        "tilt": math.degrees(math.atan2(abs(r_sh[1] - l_sh[1]),
                                        abs(r_sh[0] - l_sh[0]))) if body_ok else None,
        "ear": ear,
        "sh_y": shoulder_mid_y / frame_height if body_ok else None,
        "face": eye_width / frame_width,
        "yaw": (pts["nose"][0] - eye_mid_x) / eye_width,
        "chin": ((shoulder_mid_y - pts["chin"][1]) / shoulder_width
                 if body_ok and pts.get("chin") is not None else None),
        "eye_sh": (shoulder_mid_y - eye_mid_y) / shoulder_width if body_ok else None,
        "pitch": pitch, "roll": roll, "yaw_deg": yaw_deg, "face_scale": face_scale,
    }
