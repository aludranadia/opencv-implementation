"""Tampilan jendela utama (digambar dengan OpenCV): tombol, panel, banner, layar."""
import math

import cv2
import numpy as np

from config import (
    APP_NAME,
    BREAK_DURATION,
    BREAK_INTERVAL,
    CALIBRATION_SECONDS,
    HEAD_POSE_NAMES,
    MAX_BAD_DELAY,
    MAX_FACE_RATIO,
    MIN_BAD_DELAY,
    REQUIRED,
)
from posture import face_size_ratio, posture_visible


# ============================================================
# Langkah 5: Tampilan (semua digambar dengan OpenCV)
# ============================================================
def rgb(r, g, b):
    return (b, g, r)    # OpenCV memakai urutan BGR


# Tema terang
BG = rgb(244, 246, 250)
CARD = (255, 255, 255)
WHITE = (255, 255, 255)
BORDER = rgb(222, 228, 238)
SHADOW = rgb(228, 232, 240)
TRACK = rgb(226, 232, 240)
TEXT = rgb(30, 41, 59)
MUTED = rgb(100, 116, 139)
ACCENT, ACCENT_L = rgb(37, 99, 235), rgb(219, 234, 254)
GREEN, GREEN_L = rgb(22, 163, 74), rgb(220, 252, 231)
RED, RED_L = rgb(220, 38, 38), rgb(254, 226, 226)
AMBER, AMBER_L = rgb(217, 119, 6), rgb(254, 243, 199)
VIDEO_BG = rgb(30, 41, 59)
FONT = cv2.FONT_HERSHEY_SIMPLEX

# Gaya tombol: (warna isi, warna garis, warna teks)
BUTTON_STYLES = {
    "primary": (ACCENT, ACCENT, WHITE),
    "secondary": (CARD, rgb(203, 213, 225), TEXT),
    "on": (ACCENT_L, ACCENT, ACCENT),
    "danger": (RED_L, rgb(252, 165, 165), RED),
}

# Tata letak jendela utama (piksel)
PAD = 16
HEADER_H = 64
VIDEO_W, VIDEO_H = 720, 540
PANEL_W = 330
VX, VY = PAD, HEADER_H + 8
PX = VX + VIDEO_W + PAD
CANVAS_W = PX + PANEL_W + PAD
CANVAS_H = VY + VIDEO_H + PAD

# ------------------------------------------------------------
# 5a. Klik mouse pada tombol
# ------------------------------------------------------------
buttons = []                # [(nama, x, y, lebar, tinggi)] dibangun ulang tiap frame
mouse = {"click": None}     # posisi klik terakhir yang belum diproses
viewports = {}              # skala dan padding tampilan untuk pemetaan klik mouse


def on_mouse(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        view = viewports.get(param)
        if view is not None:
            ox, oy, sx, sy, width, height = view
            x, y = (x - ox) / sx, (y - oy) / sy
            if not (0 <= x < width and 0 <= y < height):
                return
        mouse["click"] = (x, y)


def clicked_button():
    """Mengembalikan nama tombol yang baru diklik (atau None)."""
    pos, mouse["click"] = mouse["click"], None
    if pos:
        for name, x, y, w, h in buttons:
            if x <= pos[0] <= x + w and y <= pos[1] <= y + h:
                return name
    return None


def window_closed(name):
    """True jika jendela ditutup pengguna (tombol X)."""
    try:
        return cv2.getWindowProperty(name, cv2.WND_PROP_VISIBLE) < 1
    except cv2.error:
        return True


def toggle_fullscreen(name):
    """WINDOW_NORMAL memungkinkan resize/maximize; [f] mengganti mode fullscreen."""
    try:
        active = cv2.getWindowProperty(name, cv2.WND_PROP_FULLSCREEN) == cv2.WINDOW_FULLSCREEN
        cv2.setWindowProperty(name, cv2.WND_PROP_FULLSCREEN,
                              cv2.WINDOW_NORMAL if active else cv2.WINDOW_FULLSCREEN)
    except cv2.error:
        pass


def show_responsive(name, canvas):
    """Skalakan seluruh UI tanpa terpotong/distorsi, termasuk pada layar lebar.

    Letterbox dibuat sendiri agar Windows juga mempertahankan rasio gambar.
    Koordinat tombol tetap memakai kanvas asli dan dipetakan balik di on_mouse.
    """
    height, width = canvas.shape[:2]
    try:
        _, _, target_w, target_h = cv2.getWindowImageRect(name)
    except cv2.error:
        target_w, target_h = width, height
    if target_w < 1 or target_h < 1:
        target_w, target_h = width, height
    scale = min(target_w / width, target_h / height)
    shown_w = max(1, min(target_w, round(width * scale)))
    shown_h = max(1, min(target_h, round(height * scale)))
    ox, oy = (target_w - shown_w) // 2, (target_h - shown_h) // 2
    display = np.full((target_h, target_w, 3), BG, np.uint8)
    display[oy:oy + shown_h, ox:ox + shown_w] = cv2.resize(
        canvas, (shown_w, shown_h), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
    viewports[name] = (ox, oy, shown_w / width, shown_h / height, width, height)
    cv2.imshow(name, display)


# ------------------------------------------------------------
# 5b. Elemen dasar: teks, kartu, progress bar, tombol
# ------------------------------------------------------------
def text_w(s, scale, thick=1):
    return cv2.getTextSize(s, FONT, scale, thick)[0][0]


def text(img, s, x, y, scale=0.5, color=TEXT, thick=1, align="l"):
    """y = garis dasar teks; align: l (kiri), c (tengah), r (kanan)."""
    w = text_w(s, scale, thick)
    if align == "c":
        x -= w // 2
    elif align == "r":
        x -= w
    cv2.putText(img, s, (int(x), int(y)), FONT, scale, color, thick, cv2.LINE_AA)


def fit(s, max_w, scale, thick=1):
    """Memotong teks agar muat dalam lebar tertentu."""
    if text_w(s, scale, thick) <= max_w:
        return s
    while len(s) > 1 and text_w(s + "..", scale, thick) > max_w:
        s = s[:-1]
    return s + ".."


def wrap(s, max_w, scale, thick=1):
    """Memecah teks menjadi beberapa baris yang masing-masing muat dalam lebar tertentu."""
    lines, cur = [], ""
    for word in s.split():
        trial = (cur + " " + word).strip()
        if cur and text_w(trial, scale, thick) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def rrect(img, x, y, w, h, color, r=12):
    """Persegi panjang bersudut membulat."""
    r = min(r, w // 2, h // 2)
    cv2.rectangle(img, (x + r, y), (x + w - r, y + h), color, -1)
    cv2.rectangle(img, (x, y + r), (x + w, y + h - r), color, -1)
    for cx, cy in ((x + r, y + r), (x + w - r, y + r),
                   (x + r, y + h - r), (x + w - r, y + h - r)):
        cv2.circle(img, (cx, cy), r, color, -1, cv2.LINE_AA)


def card(img, x, y, w, h, r=14):
    rrect(img, x, y + 3, w, h, SHADOW, r)        # bayangan
    rrect(img, x, y, w, h, BORDER, r)            # garis tepi
    rrect(img, x + 1, y + 1, w - 2, h - 2, CARD, r - 1)


def pbar(img, x, y, w, h, frac, color):
    """Progress bar; frac = 0..1."""
    frac = min(1.0, max(0.0, frac))
    rrect(img, x, y, w, h, TRACK, h // 2)
    if frac > 0:
        rrect(img, x, y, max(h, int(w * frac)), h, color, h // 2)


def button(canvas, name, x, y, w, h, label, kind="secondary", scale=0.5, thick=1):
    fill, border, fg = BUTTON_STYLES[kind]
    rrect(canvas, x, y, w, h, border, 10)
    rrect(canvas, x + 1, y + 1, w - 2, h - 2, fill, 9)
    label = fit(label, w - 8, scale, thick)
    th = cv2.getTextSize(label, FONT, scale, thick)[0][1]
    text(canvas, label, x + w // 2, y + (h + th) // 2, scale, fg, thick, "c")
    buttons.append((name, x, y, w, h))


def mmss(seconds):
    return f"{int(seconds) // 60:02d}:{int(seconds) % 60:02d}"


# ------------------------------------------------------------
# 5d. Header, video, dan footer
# ------------------------------------------------------------
def draw_header(canvas, pill, kind):
    cv2.rectangle(canvas, (0, 0), (CANVAS_W, HEADER_H), CARD, -1)
    cv2.line(canvas, (0, HEADER_H), (CANVAS_W, HEADER_H), BORDER, 1)
    cv2.circle(canvas, (PAD + 22, 32), 19, ACCENT, -1, cv2.LINE_AA)
    text(canvas, APP_NAME[0], PAD + 22, 40, 0.8, WHITE, 2, "c")
    tx = PAD + 52
    text(canvas, APP_NAME, tx, 29, 0.75, TEXT, 2)
    text(canvas, "Pemantau Postur Duduk dan Istirahat Mata", tx, 50, 0.42, MUTED)

    fg, bg = {"ok": (GREEN, GREEN_L), "warn": (AMBER, AMBER_L),
              "info": (ACCENT, ACCENT_L)}[kind]
    w = text_w(pill, 0.5) + 44
    x = CANVAS_W - PAD - w
    rrect(canvas, x, 17, w, 30, bg, 15)
    cv2.circle(canvas, (x + 16, 32), 5, fg, -1, cv2.LINE_AA)
    text(canvas, pill, x + 28, 37, 0.5, fg)


def place_video(canvas, frame):
    """Menaruh frame kamera di area video (rasio asli dipertahankan)."""
    h, w = frame.shape[:2]
    scale = min(VIDEO_W / w, VIDEO_H / h)
    nw, nh = int(w * scale), int(h * scale)
    x, y = VX + (VIDEO_W - nw) // 2, VY + (VIDEO_H - nh) // 2
    cv2.rectangle(canvas, (VX - 1, VY - 1), (VX + VIDEO_W, VY + VIDEO_H), BORDER, -1)
    cv2.rectangle(canvas, (VX, VY), (VX + VIDEO_W - 1, VY + VIDEO_H - 1), VIDEO_BG, -1)
    canvas[y:y + nh, x:x + nw] = cv2.resize(frame, (nw, nh))


def draw_landmarks(frame, pts, color):
    """Titik tubuh dengan ring putih agar jelas di latar apa pun."""
    for p in pts.values():
        if p is not None:
            c = (int(p[0]), int(p[1]))
            cv2.circle(frame, c, 8, WHITE, -1, cv2.LINE_AA)
            cv2.circle(frame, c, 5, color, -1, cv2.LINE_AA)
    if pts["l_sh"] is not None and pts["r_sh"] is not None:
        a, b = tuple(map(int, pts["l_sh"])), tuple(map(int, pts["r_sh"]))
        cv2.line(frame, a, b, WHITE, 5, cv2.LINE_AA)
        cv2.line(frame, a, b, color, 3, cv2.LINE_AA)
    if pts.get("face_l_eye") is not None and pts.get("face_r_eye") is not None:
        a, b = tuple(map(int, pts["face_l_eye"])), tuple(map(int, pts["face_r_eye"]))
        cv2.line(frame, a, b, color, 2, cv2.LINE_AA)


BANNER_H, BANNER_GAP = 44, 8


def video_banners(canvas, banners):
    """Pita peringatan di bagian bawah video; beberapa pita disusun ke atas
    tanpa saling menimpa. Mengembalikan batas atas pita teratas."""
    x, w = VX + 16, VIDEO_W - 32
    y = VY + VIDEO_H - 16
    for label, bg, fg in banners:
        y -= BANNER_H
        rrect(canvas, x, y, w, BANNER_H, bg, 14)
        text(canvas, fit(label, w - 24, 0.65, 2), x + w // 2, y + BANNER_H // 2 + 8,
             0.65, fg, 2, "c")
        y -= BANNER_GAP
    return y + BANNER_GAP


# ------------------------------------------------------------
# 5e. Panel samping untuk tiap tahap
# ------------------------------------------------------------
def check_row(canvas, x, y, label, ok):
    color = GREEN if ok else AMBER
    cv2.circle(canvas, (x + 8, y - 5), 6, color, -1, cv2.LINE_AA)
    text(canvas, label, x + 24, y, 0.5, TEXT)
    text(canvas, "Siap" if ok else "Belum", x + PANEL_W - 32, y, 0.5, color, 1, "r")


def panel_welcome(canvas, face_ok, light_ok):
    x, w = PX, PANEL_W
    y = VY
    card(canvas, x, y, w, 220)
    text(canvas, "Panduan Singkat", x + 16, y + 32, 0.62, TEXT, 2)
    steps = [
        "Duduk tegak dan senyaman mungkin",
        "Pastikan wajah dan bahu terlihat jelas di kamera",
        f"Tekan Mulai lalu diam selama {CALIBRATION_SECONDS} detik untuk kalibrasi",
    ]
    for i, step in enumerate(steps):
        sy = y + 76 + i * 56
        cv2.circle(canvas, (x + 32, sy - 4), 15, ACCENT_L, -1, cv2.LINE_AA)
        text(canvas, str(i + 1), x + 32, sy + 2, 0.55, ACCENT, 2, "c")
        lines = wrap(step, w - 74, 0.5)
        first = sy + 1 - (len(lines) - 1) * 10      # rata tengah terhadap lingkaran
        for j, line in enumerate(lines):
            text(canvas, line, x + 58, first + j * 20, 0.5, TEXT)

    y = VY + 228
    card(canvas, x, y, w, 106)
    text(canvas, "Cek Kesiapan", x + 16, y + 28, 0.62, TEXT, 2)
    check_row(canvas, x + 16, y + 60, "Wajah dan bahu terlihat", face_ok)
    check_row(canvas, x + 16, y + 90, "Pencahayaan cukup", light_ok)

    y = VY + 466
    card(canvas, x, y, w, 74)
    button(canvas, "start", x + 14, y + 14, w - 112, 46, "Mulai Kalibrasi",
           "primary", 0.55, 2)
    button(canvas, "quit", x + w - 88, y + 14, 74, 46, "Keluar")


def panel_calibration(canvas, elapsed, note):
    x, w = PX, PANEL_W
    y = VY
    card(canvas, x, y, w, 200)
    text(canvas, "Kalibrasi postur", x + 16, y + 32, 0.62, TEXT, 2)
    text(canvas, "Duduk tegak dengan nyaman dan", x + 16, y + 62, 0.48, TEXT)
    text(canvas, "tatap layar seperti biasa.", x + 16, y + 84, 0.48, TEXT)
    if elapsed is None:
        pbar(canvas, x + 16, y + 112, w - 32, 12, 0, ACCENT)
        text(canvas, fit(note or "Menunggu wajah dan kedua bahu terlihat...", w - 32, 0.45),
             x + 16, y + 150, 0.45, AMBER)
    else:
        remaining = max(0, math.ceil(CALIBRATION_SECONDS - elapsed))
        pbar(canvas, x + 16, y + 112, w - 32, 12, elapsed / CALIBRATION_SECONDS, ACCENT)
        text(canvas, f"Tahan posisi... {remaining} dtk lagi", x + 16, y + 150, 0.5, ACCENT)

    y = VY + 208
    card(canvas, x, y, w, 232)
    text(canvas, "Tips", x + 16, y + 32, 0.62, TEXT, 2)
    tips = ["Jangan banyak bergerak", "Wajah dan kedua bahu terlihat",
            "Cahaya cukup, hindari backlight", "Jarak layar seperti biasa"]
    for i, tip in enumerate(tips):
        ty = y + 70 + i * 36
        cv2.circle(canvas, (x + 24, ty - 5), 4, ACCENT, -1, cv2.LINE_AA)
        text(canvas, fit(tip, w - 60, 0.5), x + 40, ty, 0.5, TEXT)

    y = VY + 448
    card(canvas, x, y, w, 92)
    button(canvas, "quit", x + 14, y + 20, w - 28, 52, "Keluar", "danger", 0.55)


def panel_monitor(canvas, sess, status, bad_delay, muted):
    title, fg, bg = status
    x, w = PX, PANEL_W

    # Kartu A: status postur
    y = VY
    card(canvas, x, y, w, 84)
    cv2.circle(canvas, (x + 40, y + 42), 22, bg, -1, cv2.LINE_AA)
    cv2.circle(canvas, (x + 40, y + 42), 9, fg, -1, cv2.LINE_AA)
    text(canvas, "STATUS", x + 76, y + 24, 0.4, MUTED)
    text(canvas, fit(title, w - 90, 0.62, 2), x + 76, y + 58, 0.62, fg, 2)

    # Kartu B: pengingat istirahat mata 20-20-20
    y = VY + 92
    card(canvas, x, y, w, 96)
    if sess["break_state"] == "REMINDER":
        title_b, color = "Waktunya istirahat mata!", AMBER
        frac = sess["away_secs"] / BREAK_DURATION
        left = "Lihat objek jauh (~6 m)"
        right = f"{int(sess['away_secs'])}/{BREAK_DURATION} dtk"
    else:
        title_b, color = "Istirahat mata 20-20-20", ACCENT
        frac = sess["screen_time"] / BREAK_INTERVAL
        left = "Waktu menatap layar"
        right = f"{mmss(sess['screen_time'])} / {mmss(BREAK_INTERVAL)}"
    text(canvas, title_b, x + 16, y + 28, 0.52, color if color == AMBER else TEXT, 2)
    pbar(canvas, x + 16, y + 42, w - 32, 12, frac, color)
    text(canvas, left, x + 16, y + 78, 0.42, MUTED)
    text(canvas, right, x + w - 16, y + 78, 0.45, TEXT, 1, "r")

    # Kartu C: statistik sesi berjalan
    y = VY + 196
    card(canvas, x, y, w, 92)
    monitored = sess["time_good"] + sess["time_bad"]
    pct = f"{sess['time_good'] / monitored * 100:.0f}%" if monitored > 0 else "--"
    alert_color = RED if sess["posture_alerts"] else TEXT
    stats = [(pct, "Postur baik", GREEN), (str(sess["breaks_done"]), "Jeda mata", ACCENT),
             (str(sess["posture_alerts"]), "Peringatan", alert_color)]
    col_w = (w - 28) // 3
    for i, (value, label, color) in enumerate(stats):
        cx = x + 14 + col_w * i + col_w // 2
        text(canvas, value, cx, y + 44, 0.95, color, 2, "c")
        text(canvas, label, cx, y + 70, 0.42, MUTED, 1, "c")
        if i:
            cv2.line(canvas, (x + 14 + col_w * i, y + 20), (x + 14 + col_w * i, y + 72), BORDER, 1)

    # Kartu D: jeda sebelum peringatan postur
    y = VY + 296
    card(canvas, x, y, w, 100)
    text(canvas, fit(f"Peringatan setelah {bad_delay} dtk", w - 100, 0.5), x + 16, y + 30, 0.5, TEXT)
    button(canvas, "delay_minus", x + w - 14 - 58, y + 12, 26, 26, "-", "secondary", 0.6, 2)
    button(canvas, "delay_plus", x + w - 14 - 26, y + 12, 26, 26, "+", "secondary", 0.6, 2)
    pbar(canvas, x + 16, y + 56, w - 32, 12,
         (bad_delay - MIN_BAD_DELAY) / (MAX_BAD_DELAY - MIN_BAD_DELAY), ACCENT)
    text(canvas, f"{MIN_BAD_DELAY} dtk", x + 16, y + 90, 0.38, MUTED)
    text(canvas, f"{MAX_BAD_DELAY} dtk", x + w - 16, y + 90, 0.38, MUTED, 1, "r")

    # Kartu E: tombol kontrol
    y = VY + 404
    card(canvas, x, y, w, 136)
    bw = (w - 28 - 10) // 2
    b1, b2 = x + 14, x + 14 + bw + 10
    button(canvas, "calib", b1, y + 14, bw, 50, "Kalibrasi ulang")
    button(canvas, "mute", b2, y + 14, bw, 50,
           "Suara: OFF" if muted else "Suara: ON", "secondary" if muted else "on")
    button(canvas, "quit", b1, y + 72, w - 28, 50, "Keluar", "danger")


# ------------------------------------------------------------
# 5f. Satu fungsi per layar (mengembalikan teks dan jenis pill header)
# ------------------------------------------------------------
def screen_welcome(canvas, frame, pts):
    if pts:
        draw_landmarks(frame, pts, ACCENT)
    light_ok = float(frame.mean()) > 60           # cukup terang?
    place_video(canvas, frame)
    video_banners(canvas, [("Posisikan wajah dan bahu di dalam frame", WHITE, TEXT)])
    face_ok = pts is not None and all(pts.get(k) is not None
                                     for k in (*REQUIRED, "chin", *HEAD_POSE_NAMES))
    panel_welcome(canvas, face_ok, light_ok)
    return "Siap dimulai", "info"


def screen_calibration(canvas, frame, pts, elapsed, note):
    if pts:
        draw_landmarks(frame, pts, AMBER)
    place_video(canvas, frame)
    if elapsed is not None:
        center = (VX + VIDEO_W // 2, VY + VIDEO_H // 2)
        cv2.circle(canvas, center, 52, BORDER, -1, cv2.LINE_AA)
        cv2.circle(canvas, center, 50, WHITE, -1, cv2.LINE_AA)
        text(canvas, str(max(0, math.ceil(CALIBRATION_SECONDS - elapsed))),
             center[0], center[1] + 24, 2.2, ACCENT, 4, "c")
    panel_calibration(canvas, elapsed, note)
    return "Kalibrasi berlangsung", "warn"


def screen_monitor(canvas, frame, pts, ind, baseline, sess, issues, bad_delay,
                   muted):
    reminder = sess["break_state"] == "REMINDER"
    if ind is None:
        status = ("Tidak terdeteksi", AMBER, AMBER_L)
        header = ("Menunggu pengguna", "warn")
    elif reminder:
        status = ("Jeda istirahat mata", AMBER, AMBER_L)
        header = ("Jeda istirahat mata", "warn")
    elif issues:
        status = ("Postur tidak ideal", RED, RED_L)
        header = ("Pemantauan aktif", "ok")
    elif not posture_visible(ind):
        status = ("Deteksi sebagian", AMBER, AMBER_L)
        header = ("Pemantauan terbatas", "warn")
    else:
        status = ("Postur baik", GREEN, GREEN_L)
        header = ("Pemantauan aktif", "ok")

    if pts:
        draw_landmarks(frame, pts, status[1])
    place_video(canvas, frame)

    banners = []
    if reminder:
        banners.append(("ISTIRAHAT MATA: lihat objek jauh "
                        f"({int(sess['away_secs'])}/{BREAK_DURATION} dtk)", AMBER, WHITE))
    elif sess["bad_secs"] >= bad_delay:
        # Setiap kesalahan ditulis langsung sebagai pita terpisah yang ditumpuk rapi.
        for issue in issues:
            banners.append((issue.capitalize(), RED, WHITE))
    top = video_banners(canvas, banners)

    ratio = face_size_ratio(ind, baseline)
    distance_note = (f"Ukuran wajah: {ratio * 100:.0f}% dari acuan | maks. "
                     f"{MAX_FACE_RATIO * 100:.0f}%"
                     if ratio is not None else "Ukuran wajah belum terbaca: hadap kamera")
    note_y = top - 40 if banners else VY + VIDEO_H - 104
    rrect(canvas, VX + 16, note_y, 360, 28, WHITE, 10)
    text(canvas, distance_note, VX + 28, note_y + 19, 0.45,
         RED if ratio is not None and ratio > MAX_FACE_RATIO else MUTED)

    panel_monitor(canvas, sess, status, bad_delay, muted)
    return header
