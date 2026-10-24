"""Ringkasan sesi: penyimpanan CSV dan jendela ringkasan akhir."""
from datetime import datetime
import csv
import os

import cv2
import numpy as np

from config import APP_NAME, LOG_FILE
from ui import (
    ACCENT,
    AMBER,
    AMBER_L,
    BG,
    BORDER,
    CARD,
    GREEN,
    GREEN_L,
    MUTED,
    RED,
    RED_L,
    TEXT,
    TRACK,
    button,
    buttons,
    card,
    clicked_button,
    fit,
    mmss,
    on_mouse,
    pbar,
    rrect,
    show_responsive,
    text,
    toggle_fullscreen,
    window_closed,
)


# ------------------------------------------------------------
# 5g. Ringkasan sesi (jendela terpisah dengan grafik)
# ------------------------------------------------------------
def render_summary(sess, duration, pct_good, pct_bad, monitored):
    buttons.clear()
    W, H = 900, 560
    img = np.full((H, W, 3), BG, np.uint8)
    text(img, "Ringkasan Sesi", 30, 52, 1.0, TEXT, 2)
    text(img, f"{APP_NAME}  -  " + datetime.now().strftime("%d/%m/%Y  %H:%M"), 30, 78, 0.5, MUTED)

    # Kartu kiri: grafik donat kualitas postur
    x0, y0, cw, ch = 30, 100, 400, 340
    card(img, x0, y0, cw, ch)
    text(img, "Kualitas postur", x0 + 20, y0 + 34, 0.65, TEXT, 2)
    center, radius, thick = (x0 + cw // 2, y0 + 150), 85, 28
    if monitored <= 0:
        cv2.ellipse(img, center, (radius, radius), 0, 0, 360, TRACK, thick, cv2.LINE_AA)
        big = "--"
    else:
        angle = int(round(360 * pct_good / 100))
        if angle > 0:
            cv2.ellipse(img, center, (radius, radius), -90, 0, angle, GREEN, thick, cv2.LINE_AA)
        if angle < 360:
            cv2.ellipse(img, center, (radius, radius), -90, angle, 360, RED, thick, cv2.LINE_AA)
        big = f"{pct_good:.0f}%"
    text(img, big, center[0], center[1] + 12, 1.2, TEXT, 2, "c")
    text(img, "postur baik", center[0], center[1] + 38, 0.45, MUTED, 1, "c")
    legend = [("Postur baik", sess["time_good"], pct_good, GREEN),
              ("Tidak ideal", sess["time_bad"], pct_bad, RED)]
    for i, (label, secs, pct, color) in enumerate(legend):
        ly = y0 + 270 + i * 32
        cv2.circle(img, (x0 + 40, ly - 5), 7, color, -1, cv2.LINE_AA)
        text(img, f"{label}   {mmss(secs)}", x0 + 60, ly, 0.55, TEXT)
        text(img, f"{pct:.1f}%" if monitored > 0 else "--", x0 + cw - 30, ly, 0.55, MUTED, 1, "r")

    # Kartu kanan: aktivitas dan statistik
    rx, ry, rw, rh = 450, 100, 420, 340
    card(img, rx, ry, rw, rh)
    text(img, "Aktivitas sesi", rx + 20, ry + 34, 0.65, TEXT, 2)
    top = max(5, sess["breaks_done"], sess["posture_alerts"])
    activity = [("Jeda istirahat mata", sess["breaks_done"], ACCENT),
                ("Peringatan postur", sess["posture_alerts"], RED)]
    for i, (label, value, color) in enumerate(activity):
        by = ry + 78 + i * 56
        text(img, label, rx + 24, by, 0.52, TEXT)
        text(img, f"{value} kali", rx + rw - 24, by, 0.52, TEXT, 2, "r")
        pbar(img, rx + 24, by + 12, rw - 48, 14, value / top, color)
    cv2.line(img, (rx + 24, ry + 186), (rx + rw - 24, ry + 186), BORDER, 1)
    text(img, "Durasi sesi", rx + 24, ry + 220, 0.52, MUTED)
    text(img, mmss(duration), rx + rw - 24, ry + 220, 0.55, TEXT, 2, "r")

    # Pesan evaluasi dan tombol tutup
    if monitored <= 0:
        tip, tip_color, tip_bg = "Belum ada data postur yang terekam.", MUTED, CARD
    elif pct_good >= 80:
        tip, tip_color, tip_bg = "Postur Anda sudah baik", GREEN, GREEN_L
    elif pct_good >= 50:
        tip, tip_color, tip_bg = "Postur Anda cukup baik", AMBER, AMBER_L
    else:
        tip, tip_color, tip_bg = "Perbaiki postur Anda", RED, RED_L
    rrect(img, 30, 456, 630, 56, tip_bg, 14)
    text(img, fit(tip, 590, 0.6, 2), 50, 490, 0.6, tip_color, 2)
    button(img, "close", 680, 456, 190, 56, "Tutup", "primary", 0.65, 2)
    return img


def finish_session(sess, duration, frames):
    """Menyimpan angka ringkasan ke CSV lalu menampilkan ringkasan sesi."""
    monitored = sess["time_good"] + sess["time_bad"]
    pct_good = sess["time_good"] / monitored * 100 if monitored else 0.0
    pct_bad = 100 - pct_good if monitored else 0.0
    avg_fps = frames / duration if duration > 0 else 0.0

    print(f"Durasi {mmss(duration)} | postur baik {pct_good:.1f}% | "
          f"jeda {sess['breaks_done']} | peringatan {sess['posture_alerts']}")

    new_file = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["waktu", "durasi_detik", "persen_baik", "persen_tidak_ideal",
                             "jumlah_jeda", "jumlah_peringatan_postur", "rata_rata_fps"])
        writer.writerow([datetime.now().isoformat(timespec="seconds"), round(duration),
                         round(pct_good, 1), round(pct_bad, 1), sess["breaks_done"],
                         sess["posture_alerts"], round(avg_fps, 1)])

    window = APP_NAME + " - Ringkasan"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL | cv2.WINDOW_FREERATIO)
    cv2.resizeWindow(window, 900, 560)
    cv2.setMouseCallback(window, on_mouse, window)
    while True:
        show_responsive(window, render_summary(sess, duration, pct_good, pct_bad, monitored))
        key = cv2.waitKey(30)
        if key in (ord("f"), ord("F")):
            toggle_fullscreen(window)
            continue
        if key != -1 or clicked_button() == "close" or window_closed(window):
            break
    cv2.destroyAllWindows()
