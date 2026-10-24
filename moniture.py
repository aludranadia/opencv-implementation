"""Moniture - Pemantauan Postur Duduk dan Kebiasaan Istirahat Mata Mahasiswa.

Menjalankan: python moniture.py

Berkas yang disiapkan sendiri (folder dibuat otomatis saat program dijalankan):
  audio/perbaiki_postur.mp3      -> suara saat postur buruk (.mp3 atau .wav)
  audio/jauhi_layar.mp3          -> suara saat wajah terlalu dekat (.mp3 atau .wav)
  audio/istirahat_mata.mp3       -> suara saat pengingat istirahat mata

Kontrol: klik tombol di jendela, atau gunakan pintasan keyboard:
  [Spasi/Enter] mulai   [c] kalibrasi ulang   [m] suara on/off
  [+]/[-] atur jeda peringatan   [q] keluar
  [f] masuk/keluar fullscreen; ukuran jendela juga dapat diubah dengan mouse

Kalibrasi dilakukan dengan duduk tegak seperti biasa. Jarak wajah ke layar dinilai
dari perubahan ukuran wajah terhadap acuan kalibrasi, bukan dari jarak dalam cm.
"""
import os
import time

import cv2
import mediapipe as mp
import numpy as np

from config import (
    APP_NAME,
    AUDIO_DIR,
    AUDIO_FILES,
    CALIBRATION_RETRY_PAUSE,
    CALIBRATION_SECONDS,
    CAMERA_INDEX,
    DEFAULT_BAD_DELAY,
    MAX_BAD_DELAY,
    MIN_BAD_DELAY,
)
from detection import compute_indicators, get_points
from posture import (
    build_baseline,
    calibration_issue,
    calibration_motion_issue,
    calibration_sample_valid,
    new_history,
)
from alerts import (
    find_audio,
    init_audio,
    new_session,
    pygame,
    reset_timers,
    update_monitoring,
)
from ui import (
    BG,
    CANVAS_H,
    CANVAS_W,
    buttons,
    clicked_button,
    draw_header,
    on_mouse,
    screen_calibration,
    screen_monitor,
    screen_welcome,
    show_responsive,
    toggle_fullscreen,
    window_closed,
)
from summary import finish_session


# ============================================================
# Langkah z: Program utama (perulangan pemantauan real-time)
# ============================================================
def main():
    # 6a. Persiapan: folder audio, kamera, dan model Pose
    os.makedirs(AUDIO_DIR, exist_ok=True)
    init_audio()
    for kind in AUDIO_FILES:
        print(f"[audio] {kind}: {find_audio(kind) or 'belum ada (memakai beep)'}")

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        raise RuntimeError("Kamera tidak dapat dibuka. Periksa CAMERA_INDEX.")
    pose = mp.solutions.pose.Pose(model_complexity=0,
                                  min_detection_confidence=0.5,
                                  min_tracking_confidence=0.5)
    face_mesh = mp.solutions.face_mesh.FaceMesh(max_num_faces=1,
                                                min_detection_confidence=0.5,
                                                min_tracking_confidence=0.5)

    # WINDOW_NORMAL mengizinkan maximize; show_responsive mempertahankan rasio UI.
    cv2.namedWindow(APP_NAME, cv2.WINDOW_NORMAL | cv2.WINDOW_FREERATIO)
    cv2.resizeWindow(APP_NAME, CANVAS_W, CANVAS_H)
    cv2.setMouseCallback(APP_NAME, on_mouse, APP_NAME)
    base_canvas = np.full((CANVAS_H, CANVAS_W, 3), BG, np.uint8)

    sess, history, baseline = new_session(), new_history(), None
    stage = "welcome"                 # welcome -> calib -> monitor
    cal_samples, cal_total, cal_start, cal_note = [], 0, None, ""
    cal_retry_after = 0.0
    muted, bad_delay = False, DEFAULT_BAD_DELAY
    frames = 0
    t_start = last = time.time()
    running = True

    while running:
        # 6b. Akuisisi gambar dan pra-pemrosesan (BGR -> RGB untuk MediaPipe)
        ok, frame = cap.read()
        if not ok:
            break
        frame = cv2.flip(frame, 1)    # cermin agar pratinjau terasa natural
        now = time.time()
        dt = min(now - last, 0.5)
        last = now
        frames += 1
        h, w = frame.shape[:2]
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # 6c. Deteksi landmark dan ekstraksi indikator postur
        pts = get_points(pose.process(rgb_frame), w, h, face_mesh.process(rgb_frame))
        ind = compute_indicators(pts, w, h) if pts else None

        # 6d. Menggambar layar sesuai tahap
        buttons.clear()
        canvas = base_canvas.copy()

        if stage == "welcome":
            header = screen_welcome(canvas, frame, pts)

        elif stage == "calib":
            valid_sample = calibration_sample_valid(ind)
            if valid_sample and cal_start is None and now >= cal_retry_after:
                cal_start = now           # hitung mundur dimulai saat pengguna terlihat
                cal_note = ""
            elapsed = None
            if cal_start is not None:
                cal_total += 1
                if valid_sample:
                    cal_samples.append(ind)
                    reason = calibration_motion_issue(cal_samples)
                    if reason:
                        cal_note = reason
                        cal_retry_after = now + CALIBRATION_RETRY_PAUSE
                        cal_samples, cal_total, cal_start = [], 0, None
                if cal_start is not None:
                    elapsed = now - cal_start
            header = screen_calibration(canvas, frame, pts, elapsed, cal_note)

            if elapsed is not None and elapsed >= CALIBRATION_SECONDS:
                reason = calibration_issue(cal_samples, cal_total)
                if reason is None:
                    baseline = build_baseline(cal_samples)
                    reset_timers(sess)
                    history = new_history()
                    stage = "monitor"
                else:                     # data kurang memadai -> ulangi
                    cal_note = reason
                    cal_retry_after = now + CALIBRATION_RETRY_PAUSE
                    cal_samples, cal_total, cal_start = [], 0, None

        else:
            issues, _ = update_monitoring(sess, baseline, history, ind, dt, now,
                                          bad_delay, muted)
            header = screen_monitor(canvas, frame, pts, ind, baseline, sess, issues,
                                    bad_delay, muted)

        draw_header(canvas, header[0], header[1])

        # 6e. Tampilkan hasil, lalu baca klik mouse dan tombol keyboard
        show_responsive(APP_NAME, canvas)
        key = cv2.waitKey(1) & 0xFF
        if window_closed(APP_NAME):
            break

        # 6f. Menjalankan aksi (dari klik mouse atau pintasan keyboard)
        events = []
        clicked = clicked_button()
        if clicked:
            events.append(clicked)
        if key == ord("q"):
            events.append("quit")
        elif key in (13, 32) and stage == "welcome":
            events.append("start")
        elif key == ord("c"):
            events.append("start" if stage == "welcome" else "calib")
        elif key == ord("m"):
            events.append("mute")
        elif key in (ord("+"), ord("=")):
            events.append("delay_plus")
        elif key in (ord("-"), ord("_")):
            events.append("delay_minus")
        elif key in (ord("f"), ord("F")):
            events.append("fullscreen")

        for event in events:
            if event == "start" and stage == "welcome":
                stage = "calib"
                cal_samples, cal_total, cal_start, cal_note = [], 0, None, ""
                cal_retry_after = 0.0
            elif event == "calib" and stage == "monitor":
                baseline, stage = None, "welcome"
                cal_samples, cal_total, cal_start, cal_note = [], 0, None, ""
            elif event == "mute":
                muted = not muted
            elif event == "fullscreen":
                toggle_fullscreen(APP_NAME)
            elif event == "delay_plus":
                bad_delay = min(MAX_BAD_DELAY, bad_delay + 5)
            elif event == "delay_minus":
                bad_delay = max(MIN_BAD_DELAY, bad_delay - 5)
            elif event == "quit":
                running = False

    # 6g. Menutup kamera dan audio, lalu menampilkan ringkasan sesi
    duration = time.time() - t_start
    pose.close()
    face_mesh.close()
    cap.release()
    cv2.destroyAllWindows()
    if pygame and pygame.mixer.get_init():
        pygame.mixer.quit()
    finish_session(sess, duration, frames)


if __name__ == "__main__":
    main()
