# Moniture

Pemantau postur duduk dan istirahat mata (OpenCV + MediaPipe).

## Menjalankan

```
pip install -r requirements.txt
python moniture.py
```

Letakkan file suara di folder `audio/`: `perbaiki_postur`, `jauhi_layar`, `istirahat_mata` (`.mp3` atau `.wav`).
Bila belum ada, program memakai beep.

## Pembagian modul

| Anggota | Berkas | Tanggung jawab |
|---|---|---|
| 1 | `config.py`, `detection.py` | Konstanta dan ambang batas; deteksi Pose + Face Mesh, `solvePnP`, indikator postur |
| 2 | `posture.py` | Kalibrasi, smoothing, `classify` (status postur) |
| 3 | `alerts.py` | Data sesi, suara peringatan, timer peringatan, pengingat 20-20-20 |
| 4 | `ui.py` | Tampilan jendela utama: tombol, panel, banner, layar awal/kalibrasi/pemantauan |
| 5 | `moniture.py`, `summary.py`, `README.md`, `requirements.txt` | Program utama (loop real-time), ringkasan sesi dan CSV, dokumentasi |

Urutan ketergantungan (tidak ada impor melingkar):
`config` → `detection` → `posture` → `alerts`; `ui` memakai `config` + `posture`; `summary` memakai `ui`; `moniture.py` memakai semuanya.

## Alur Git

- Satu cabang per anggota, misalnya `feat/deteksi`, `feat/postur`, `feat/alerts`, `feat/ui`, `feat/main`.
- Jangan push langsung ke `main`; gabungkan lewat pull request yang ditinjau minimal satu anggota lain.
- Commit kecil dengan pesan jelas, misalnya `ui: rapikan teks panduan singkat`.
- Ubah hanya berkas bagianmu. Bila perlu mengubah berkas anggota lain, beri tahu pemiliknya lebih dulu.
