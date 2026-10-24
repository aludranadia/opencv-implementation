"""Konfigurasi: seluruh konstanta, ambang batas, dan model wajah 3D."""
import os

import numpy as np


# ============================================================
# Langkah 1: Konfigurasi program
# Nilai ambang (THRESHOLD) di bawah ini adalah PERKIRAAN AWAL
# dan perlu disesuaikan melalui uji coba awal pada webcam masing-masing.
# ============================================================
APP_NAME = "Moniture"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # folder tempat script ini
AUDIO_DIR = os.path.join(BASE_DIR, "audio")
AUDIO_FILES = {"posture": "perbaiki_postur", "close": "jauhi_layar",
               "break": "istirahat_mata"}  # tanpa ekstensi
AUDIO_EXTS = (".mp3", ".wav")
LOG_FILE = os.path.join(BASE_DIR, "session_log.csv")    # hanya angka, bukan video

CAMERA_INDEX = 0                  # 0 = kamera bawaan laptop (ubah sesuai kameramu)
VISIBILITY_MIN = 0.5              # batas keyakinan landmark agar dianggap terlihat

CALIBRATION_SECONDS = 10          # lama kalibrasi saat duduk tegak
CALIBRATION_MIN_VALID = 0.8       # minimal 80% frame kalibrasi harus terdeteksi
CALIBRATION_RETRY_PAUSE = 2.5     # tampilkan alasan gagal sebelum mencoba ulang

SMOOTH_WINDOW = 15                # jumlah frame untuk rata-rata bergerak
HEAD_PITCH_DELTA = 8.0            # tambahan menunduk dari acuan (derajat)
HEAD_ROLL_DELTA = 8.0             # kepala miring ke kiri/kanan dari acuan (derajat)
CHIN_DROP_DELTA = 0.06            # dagu turun relatif ke bahu, satuan lebar bahu
EYE_DROP_DELTA = 0.04             # konfirmasi kepala ikut turun, bukan hanya rahang
NECK_CHANGE_RATIO = 0.20          # jarak telinga-bahu berubah > 20% dari acuan
                                  # (membesar = bahu turun, mengecil = membungkuk)
SHOULDER_DROP = 0.01              # posisi bahu turun > 1% tinggi frame dari acuan
SHOULDER_TILT_DELTA = 8.0         # selisih kemiringan bahu (derajat) dari acuan
# Wajah dianggap terlalu dekat bila ukurannya melebihi acuan kalibrasi sebesar ini
# (1.25 = 25% lebih besar dari saat kalibrasi).
MAX_FACE_RATIO = 1.25

DEFAULT_BAD_DELAY = 10            # detik postur buruk sebelum peringatan
MIN_BAD_DELAY, MAX_BAD_DELAY = 5, 60
ABSENCE_RESET_SECONDS = 10        # pengguna hilang selama ini -> timer direset

BREAK_INTERVAL = 20 * 60          # pengingat 20-20-20: setiap 20 menit (detik)
BREAK_DURATION = 20               # lama mengalihkan pandangan (detik)
BREAK_REPEAT = 60                 # ulangi pengingat jika belum istirahat (detik)
AWAY_FACE_RATIO = 0.85            # wajah < 85% acuan = menjauh dari layar
AWAY_YAW_DELTA = 0.40             # selisih arah wajah dari acuan = berpaling

# Indeks landmark MediaPipe Pose yang dipakai (hanya tubuh bagian atas)
LANDMARKS = {"nose": 0, "l_eye": 2, "r_eye": 5, "l_ear": 7, "r_ear": 8,
             "l_sh": 11, "r_sh": 12}
REQUIRED = ("nose", "l_eye", "r_eye", "l_sh", "r_sh")
INDICATORS = ("head", "tilt", "ear", "sh_y", "face", "yaw",
              "chin", "eye_sh", "pitch", "roll", "yaw_deg", "face_scale")

# Face Mesh menambahkan dagu dan titik wajah bagian atas yang tidak dimiliki Pose.
FACE_LANDMARKS = {"face_nose": 1, "forehead": 10, "face_l_eye": 33,
                  "l_temple": 127, "chin": 152, "nose_bridge": 168,
                  "face_r_eye": 263, "r_temple": 356}
HEAD_POSE_NAMES = ("face_nose", "forehead", "face_l_eye", "nose_bridge",
                   "face_r_eye", "l_temple", "r_temple")
# Tujuh vertex model kanonik MediaPipe (Google, Apache-2.0); tanpa titik dagu.
# Sumber: https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/modules/face_geometry/data/canonical_face_model.obj
# Sumbu Y/Z dibalik agar sesuai kamera OpenCV: X kanan, Y bawah, Z depan.
UPPER_FACE_MODEL = np.array([
    (0.0, 1.126865, -7.475604), (0.0, -8.261778, -4.481535),
    (-4.445859, -2.663991, -3.173422), (0.0, -3.271027, -5.236015),
    (4.445859, -2.663991, -3.173422), (-7.743095, -2.364999, 2.005167),
    (7.743095, -2.364999, 2.005167),
], dtype=np.float64)
