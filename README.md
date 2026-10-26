# Moniture

**Sistem pemantauan postur duduk dan kebiasaan istirahat mata untuk mahasiswa pengguna laptop, berbasis computer vision (OpenCV dan MediaPipe).**

Mata Kuliah Teknologi Berkembang · Kelompok 02

| | |
|---|---|
| Repository | https://github.com/aludranadia/opencv-implementation |
| Akses | Public |
| Bahasa | Python 3 |
| Input | Webcam laptop |

---

## 1. Deskripsi Proyek

Mahasiswa sering duduk lama dengan postur yang kurang ergonomis dan menatap layar tanpa jeda istirahat. Kebiasaan ini berkaitan dengan keluhan nyeri punggung dan gejala kelelahan mata. Upaya pencegahan seperti edukasi dan pengingat berkala belum memantau kondisi pengguna secara langsung.

Moniture memanfaatkan kamera laptop sebagai sensor. Aplikasi membaca posisi wajah dan tubuh bagian atas pengguna, membandingkannya dengan acuan postur pribadi hasil kalibrasi, lalu memberi peringatan visual dan suara ketika postur tidak ideal bertahan beberapa detik. Aplikasi juga menjalankan pengingat istirahat mata dengan metode 20-20-20 (setiap 20 menit menatap layar, alihkan pandangan ke objek jauh selama 20 detik) dan menyajikan ringkasan sesi.

Moniture dirancang sebagai **alat bantu pengingat**.

### Fitur utama

- Kalibrasi 10 detik saat duduk tegak, sehingga penilaian menyesuaikan tubuh dan posisi laptop tiap pengguna.
- Deteksi kepala menunduk, kepala miring, bahu miring, badan membungkuk, dan wajah terlalu dekat dengan layar.
- Peringatan visual (label merah per masalah) dan suara dengan jeda sebelum peringatan yang dapat diatur.
- Pengingat istirahat mata 20-20-20 yang memantau apakah pengguna berpaling atau menjauh dari layar selama jeda.
- Ringkasan sesi (persentase postur baik, jumlah jeda, jumlah peringatan) yang dicatat ke file CSV.
- Seluruh pemrosesan dilakukan di laptop pengguna. Aplikasi tidak menyimpan rekaman video.

---

## 2. Kebutuhan Perangkat Lunak dan Dependensi

### Perangkat keras

- Laptop atau PC dengan webcam.
- Speaker atau headphone (untuk suara peringatan).
- Layar yang mampu menampilkan jendela sekitar 1100 × 630 piksel (ukuran jendela dapat diubah, dan tersedia mode fullscreen).

### Perangkat lunak

- Windows 10/11. Aplikasi dikembangkan dan dijalankan di Windows dengan Python 3.11.9.
- Python 3 (disarankan 3.11).
- Koneksi internet.

### Dependensi Python

| Paket | Versi | Kegunaan |
|---|---|---|
| `mediapipe` | **0.10.21** | Deteksi tubuh (Pose) dan wajah (Face Mesh) |
| `opencv-contrib-python` | ikut terpasang bersama MediaPipe (4.11.0.86) | Akuisisi video, pemrosesan gambar, menggambar tampilan, perkiraan sudut kepala |
| `numpy` | di bawah 2 (1.26.4), ikut terpasang | Perhitungan array dan median |
| `protobuf` | 4.25.x, ikut terpasang | Dependensi MediaPipe |
| `pygame` | 2.6.1 | Memutar file suara (.mp3 atau .wav) |

Library bawaan Python yang dipakai: `csv`, `math`, `os`, `time`, `datetime`, dan `winsound` (khusus Windows, untuk beep cadangan).

> **Saran: Jangan memakai MediaPipe versi terbaru.** Aplikasi memakai antarmuka `mp.solutions` yang sudah tidak tersedia pada MediaPipe 0.10.33. Karena itu versi dikunci ke 0.10.21.

---

## 3. Petunjuk Instalasi

Semua perintah dijalankan dari dalam folder proyek. Contoh di bawah untuk Windows PowerShell.

**1. Ambil kode**

```powershell
git clone https://github.com/aludranadia/opencv-implementation
cd opencv-implementation
```

Jika memakai berkas ZIP, ekstrak lalu masuk ke folder hasil ekstrak.

**2. Buat lingkungan virtual**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Jika PowerShell menolak menjalankan skrip aktivasi, jalankan perintah ini sekali pada jendela terminal yang sama, lalu ulangi aktivasi:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

Alternatif tanpa aktivasi: panggil Python di dalam folder venv secara langsung, yaitu `.\venv\Scripts\python.exe` pada semua perintah di bawah.

Pada macOS atau Linux, aktivasinya `source venv/bin/activate`.

**3. Pasang dependensi**

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Isi `requirements.txt`:

```
mediapipe==0.10.21
pygame==2.6.1
```

**4. Periksa instalasi**

```powershell
python -c "import cv2, mediapipe as mp; print(cv2.__version__, mp.__version__, hasattr(mp, 'solutions'))"
```

Hasil yang diharapkan: nomor versi OpenCV, `0.10.21`, dan `True`. Perintah ini tidak memerlukan webcam.

> Gunakan lingkungan virtual khusus. Jika TensorFlow terpasang pada Python yang sama, MediaPipe dapat gagal diimpor karena bentrok versi `protobuf` (error: `cannot import name 'runtime_version'`).

---

## 4. Cara Menjalankan Aplikasi

```powershell
python moniture.py
```

Jalankan dari dalam folder proyek. Jendela **Moniture** akan terbuka dengan layar awal. Untuk keluar, tekan `q` atau klik **Keluar**. Ringkasan sesi akan tampil sebelum program selesai.

Jika muncul pesan `Kamera tidak dapat dibuka`, ubah nilai `CAMERA_INDEX` di `config.py` (coba 0, 1, atau 2; 0 biasanya kamera bawaan laptop).

---

## 5. Cara Memberikan Input

**Input utama adalah webcam laptop** yang dibaca frame demi frame secara real-time. Tidak ada berkas gambar atau video yang perlu disiapkan.

Agar pembacaan baik:
- Duduk menghadap kamera seperti saat belajar biasa, **satu orang** di dalam frame.
- Pastikan wajah dan **kedua bahu** terlihat. Cahaya harus cukup dan tidak membelakangi jendela.
- Pada layar awal, panel **Cek Kesiapan** menunjukkan apakah wajah dan bahu sudah terbaca dan pencahayaan cukup.
- Klik **Mulai Kalibrasi**, lalu duduk tegak dan diam selama 10 detik.

**Kontrol**

| Aksi | Tombol di jendela | Pintasan |
|---|---|---|
| Mulai kalibrasi (layar awal) | Mulai Kalibrasi | `Spasi` / `Enter` / `c` |
| Kalibrasi ulang (saat pemantauan) | Kalibrasi ulang | `c` |
| Suara peringatan on/off | Suara: ON/OFF | `m` |
| Atur jeda sebelum peringatan postur (5–60 detik) | tombol `+` dan `−` | `+` / `-` |
| Fullscreen | (tidak ada) | `f` |
| Keluar dan tampilkan ringkasan | Keluar | `q` |

Ukuran jendela juga dapat diubah dengan mouse. Kalibrasi ulang disarankan setiap kali laptop atau kamera berpindah posisi.

---

## 6. Output yang Diharapkan

### Tampilan pada jendela utama

| Tahap | Tampilan |
|---|---|
| Layar awal | Pratinjau webcam dengan titik wajah dan bahu, panduan singkat, dan Cek Kesiapan |
| Kalibrasi | Hitung mundur besar dan progress bar selama 10 detik. Jika ditolak, muncul alasan seperti *Terlalu banyak gerakan. Ulangi sambil diam.* lalu kalibrasi diulang |
| Pemantauan | Status **Postur baik** (hijau), **Postur tidak ideal** (merah), **Deteksi sebagian**, atau **Tidak terdeteksi** (kuning); kartu progres 20-20-20; statistik sesi; pengaturan jeda peringatan |

Label merah di bagian bawah video muncul setelah postur tidak ideal bertahan melebihi jeda peringatan (bawaan 10 detik). Setiap masalah tampil sebagai label sendiri:

| Label | Arti |
|---|---|
| Kepala menunduk | Sudut menunduk kepala bertambah melebihi ambang dari acuan kalibrasi |
| Kepala miring | Kepala miring ke kiri atau kanan melebihi ambang |
| Bahu miring | Garis bahu miring melebihi ambang |
| Badan membungkuk | Bahu atau dagu turun, atau jarak telinga-bahu berubah, dibanding acuan |
| Wajah terlalu dekat | Ukuran wajah melebihi 125% ukuran saat kalibrasi (kolom ukuran wajah memerah) |

### Suara peringatan

| Kejadian | File suara |
|---|---|
| Postur tidak ideal | `audio/perbaiki_postur.mp3` (atau `.wav`) |
| Wajah terlalu dekat | `audio/jauhi_layar.mp3` (atau `.wav`) |
| Pengingat istirahat mata | `audio/istirahat_mata.mp3` (atau `.wav`) |

Jika file suara tidak ada, aplikasi tetap berjalan dan memakai beep sebagai cadangan.

### Pengingat istirahat mata (20-20-20)

Setelah 20 menit menatap layar, label kuning **ISTIRAHAT MATA** muncul disertai suara. Alihkan pandangan ke objek jauh. Hitungan 0–20 detik bertambah selama pengguna berpaling atau menjauh dari layar. Setelah 20 detik, jumlah **Jeda mata** bertambah satu dan timer diulang. Jika pengguna tetap menghadap layar, pengingat diulang setiap 60 detik.

### Ringkasan sesi

Saat keluar, jendela **Ringkasan Sesi** menampilkan grafik donat persentase postur baik dan tidak ideal, jumlah jeda istirahat mata, jumlah peringatan postur, dan durasi sesi. Satu baris angka ringkasan juga ditambahkan ke `session_log.csv`:

| Kolom | Isi |
|---|---|
| `waktu` | Waktu sesi berakhir |
| `durasi_detik` | Lama sesi |
| `persen_baik`, `persen_tidak_ideal` | Proporsi waktu dengan postur baik dan tidak ideal |
| `jumlah_jeda` | Jumlah jeda istirahat mata yang diselesaikan |
| `jumlah_peringatan_postur` | Jumlah episode peringatan postur |
| `rata_rata_fps` | Rata-rata frame per detik selama sesi |

Terminal juga mencetak status audio saat mulai dan satu baris ringkasan saat selesai. File CSV hanya berisi angka, tidak ada gambar atau video.

---

## 7. Struktur Proyek

```
.
├── moniture.py        # program utama (perulangan pemantauan real-time)
├── config.py          # konstanta, ambang batas, dan jalur file
├── detection.py       # deteksi Pose dan Face Mesh, indikator postur
├── posture.py         # kalibrasi, smoothing, penentuan status postur
├── alerts.py          # data sesi, suara, timer peringatan, pengingat 20-20-20
├── ui.py              # tombol, panel, banner, layar awal/kalibrasi/pemantauan
├── summary.py         # ringkasan sesi dan penyimpanan CSV
├── requirements.txt
├── audio/             # file suara peringatan
└── session_log.csv    # dibuat otomatis saat sesi pertama selesai
```

### Pembagian kontribusi

| Anggota | Berkas |
|---|---|
| Syahdu Szenovera Maharani | `config.py`, `detection.py` |
| Aludra Nadia Salwa | `posture.py` |
| Crystal Reinheart | `alerts.py` |
| Maria Arum Ningtyas | `ui.py` |
| Naufatuzaki Auliazahra Marjuki | `moniture.py`, `summary.py`, dokumentasi |

---

## 8. Model dan Konfigurasi Tambahan

**Model.** Moniture tidak memakai model yang dilatih sendiri dan tidak membutuhkan dataset. Model MediaPipe Pose (versi ringan, `model_complexity=0`) dan Face Mesh dipakai langsung dari pustaka. Model Pose ringan dapat diunduh otomatis oleh MediaPipe saat eksekusi pertama, sehingga **eksekusi pertama memerlukan internet**. Setelah itu tidak diperlukan lagi.

**Berkas suara.** Letakkan file suara pada folder `audio/` dengan nama persis seperti di tabel bagian 6 (format `.mp3` atau `.wav`). Folder dibuat otomatis jika belum ada. Berkas suara tidak wajib: tanpa berkas, aplikasi memakai beep.

**Konfigurasi di `config.py`.** Nilai-nilai berikut dapat disesuaikan:

| Konstanta | Fungsi |
|---|---|
| `CAMERA_INDEX` | Nomor kamera (0 = kamera bawaan laptop) |
| `CALIBRATION_SECONDS` | Lama kalibrasi (bawaan 10 detik) |
| `DEFAULT_BAD_DELAY` | Jeda sebelum peringatan postur (bawaan 10 detik, dapat diubah saat aplikasi berjalan) |
| `HEAD_PITCH_DELTA`, `HEAD_ROLL_DELTA`, `SHOULDER_TILT_DELTA`, `SHOULDER_DROP`, `CHIN_DROP_DELTA`, `EYE_DROP_DELTA`, `NECK_CHANGE_RATIO` | Ambang batas penilaian postur terhadap acuan kalibrasi |
| `MAX_FACE_RATIO` | Batas ukuran wajah dibanding acuan (bawaan 1,25) |
| `BREAK_INTERVAL`, `BREAK_DURATION`, `BREAK_REPEAT` | Interval, lama, dan pengulangan pengingat 20-20-20 |

Ambang batas adalah perkiraan awal hasil uji coba tim dan perlu disesuaikan bila hasil pada perangkat lain kurang sesuai.

**Mencoba pengingat 20-20-20 tanpa menunggu.** Untuk demonstrasi, ubah `BREAK_INTERVAL = 20 * 60` menjadi nilai kecil, misalnya `30` (detik). Kembalikan ke `20 * 60` untuk penggunaan normal.

---

## 9. Keterbatasan yang Diketahui

- **Kamera depan hanya 2D.** Membungkuk ke depan sulit dibaca langsung, sehingga penilaian memakai perubahan posisi bahu, dagu, dan sudut kepala terhadap acuan kalibrasi.
- **Bergantung pada kalibrasi.** Semua penilaian dibandingkan dengan postur saat kalibrasi. Jika kamera atau laptop dipindah, atau pengguna kalibrasi dalam posisi yang sudah buruk, hasil menjadi tidak akurat. Kalibrasi ulang bila posisi berubah.
- **Ambang batas masih perkiraan.** Hasil dapat berbeda pada pengguna, kamera, dan laptop lain. Peringatan keliru atau terlewat masih mungkin terjadi.
- **Jarak ke layar bukan dalam sentimeter.** Aplikasi hanya membandingkan ukuran wajah dengan ukuran saat kalibrasi. Sudut kepala dihitung dengan parameter kamera perkiraan, bukan pengukuran anatomis.
- **Pengingat 20-20-20 bersifat perkiraan.** Aplikasi hanya mengetahui apakah pengguna berpaling atau menjauh dari layar. Aplikasi tidak dapat memastikan pengguna benar-benar melihat objek sejauh sekitar 6 meter.
- **Butuh kondisi pencahayaan dan tampilan yang baik.** Wajah dan kedua bahu harus terlihat. Jika bahu terpotong frame, hanya sebagian indikator yang dinilai (status Deteksi sebagian). Cahaya dari belakang (backlight) mengurangi akurasi.
- **Satu pengguna dan satu kamera.** Pose dan Face Mesh dikonfigurasi untuk satu orang. Jika ada lebih dari satu orang di frame, hasilnya tidak dijamin.
- **Kinerja bergantung laptop.** Pose dan Face Mesh berjalan bersamaan sehingga FPS bervariasi antar perangkat (rata-rata FPS tercatat di `session_log.csv`).
- **Tergantung versi MediaPipe.** Aplikasi memakai `mp.solutions` dan hanya diuji dengan MediaPipe 0.10.21.
- **Platform.** Dikembangkan dan dijalankan di Windows. Beep cadangan memakai `winsound` (khusus Windows). Pada sistem operasi lain, beep cadangan hanya berupa karakter bel terminal.
- **Bukan alat medis.** Aplikasi hanya membantu mengingatkan dan tidak mendiagnosis atau mencegah penyakit.

---

## 10. Pemecahan Masalah

| Gejala | Penyebab dan solusi |
|---|---|
| `Kamera tidak dapat dibuka` | Ubah `CAMERA_INDEX` di `config.py` (0, 1, atau 2). Tutup aplikasi lain yang memakai kamera |
| `AttributeError: module 'mediapipe' has no attribute 'solutions'` | Versi MediaPipe terlalu baru. Jalankan `python -m pip install mediapipe==0.10.21` |
| `ImportError: cannot import name 'runtime_version'` | TensorFlow dan MediaPipe bentrok di satu lingkungan. Pakai lingkungan virtual khusus |
| `Activate.ps1 cannot be loaded because running scripts is disabled` | Jalankan `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`, atau panggil `.\venv\Scripts\python.exe` langsung |
| Tidak ada suara atau hanya beep | Cek tombol **Suara: ON**, volume, nama dan lokasi file di `audio/`, dan bahwa `pygame` terpasang |
| Status selalu **Tidak terdeteksi** atau **Deteksi sebagian** | Perbaiki cahaya, mundur sedikit agar wajah dan kedua bahu masuk frame, lalu kalibrasi ulang |
| Kalibrasi terus ditolak | Duduk tegak dan diam, hadapkan wajah ke kamera, ratakan bahu |
| Eksekusi pertama sangat lambat atau gagal | Pastikan terhubung internet agar model MediaPipe dapat diunduh |

---

## 11. Atribusi dan Referensi

**Library dan data**

- MediaPipe (Google, Apache-2.0): Pose dan Face Mesh. Tujuh titik model wajah 3D yang dipakai untuk memperkirakan sudut kepala berasal dari model wajah kanonik MediaPipe (`canonical_face_model.obj`, Google, Apache-2.0).
- OpenCV (Apache-2.0) dan NumPy untuk pemrosesan citra dan perhitungan.
- pygame untuk pemutaran audio.

**Latar belakang masalah**

- Kasandra, Satriyo, P. A., Kahanjak, D. N., & Nugrahini, S. (2026). Hubungan posisi duduk dan durasi duduk saat belajar dengan keluhan nyeri punggung bawah pada mahasiswa Fakultas Kedokteran Universitas Palangka Raya. *Ibnu Sina: Jurnal Kedokteran dan Kesehatan, 25*(1), 30–40. https://doi.org/10.30743/ibnusina.v25i1.762
- Nurhikma, G., Setyowati, D. L., & Ramdan, I. M. (2022). Pengaruh pemberian metode 20-20-20 terhadap penurunan gejala Computer Vision Syndrome (CVS). *Faletehan Health Journal, 9*(3), 298–307.
- Iskandar, M. M., Quzwain, F., Gading, P. W., & Tarawifa, S. (2020). Penyuluhan posisi duduk yang benar untuk kesehatan punggung bagi masyarakat awam. *MEDIC, 3*(2), 121–125.