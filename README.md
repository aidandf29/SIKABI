# SIKABI — Sistem Intelijen Karier Bank Indonesia

Prototipe aplikasi internal untuk staf DSDM mengolah data penilaian kelayakan
promosi pegawai (Quantitative/Qualitative Score → Gate Administrasi → Gate KPP
→ Grade Senior/MDG → Kuadran & Readiness Promosi).

## Struktur proyek

```
sikabi/
├── app.py              # Aplikasi Streamlit (entry point)
├── scoring.py          # Mesin perhitungan skor & gate keputusan (murni Python, testable)
├── data_gen.py         # Generator data dummy (2.500 pegawai + tabel referensi)
├── assets/
│   └── Sikabi.png      # Logo aplikasi (favicon + header sidebar)
├── data/
│   └── sikabi_data.xlsx  # Sumber data (Employees + 7 tabel master/referensi)
├── requirements.txt
└── README.md
```

## Menjalankan secara lokal

```bash
pip install -r requirements.txt
streamlit run app.py
```

Buka `http://localhost:8501` di browser.

> **Yang perlu Anda lakukan:** jalankan
> ```bash
> pip install -r requirements.txt --upgrade
> ```
> Ada 2 hal yang perlu versi baru: `Pillow` (untuk logo, kalau belum ada) dan
> **Streamlit minimal versi 1.36** (dipakai untuk ikon Material Design native
> di tombol navigasi — kalau versi Streamlit Anda lebih lama, tombolnya akan
> error karena parameter `icon` belum dikenal).

## Membuat ulang data dummy

Kalau ingin regenerasi 2.500 data pegawai dari awal (misalnya untuk reset demo):

```bash
python data_gen.py
```

Ini akan menimpa `data/sikabi_data.xlsx`.

## Struktur data (`data/sikabi_data.xlsx`)

| Sheet | Isi |
|---|---|
| `Employees` | Data mentah pegawai: NIP, Nama, Unit, Satker, Pangkat (DD/AD/M/AM), Sublevel (Reguler/Senior), **Tanggal_Mulai_Pangkat, Tanggal_Mulai_Senior** (basis hitung MDG/MDGS), NK_1..NK_5, Pendidikan, Sertifikasi, Exposure, Potensi (kategorikal), K3, Status, PTB_S2, Promotion_Award, Satker_Recommendation, Remaining_Service |
| `Quant_Weights` | Bobot komponen Quantitative Score (NK, MDP, Pendidikan, Sertifikasi) |
| `Qual_Weights` | Bobot komponen Qualitative Score (Exposure, Potensi, K3) |
| `Rank_Weights` | Bobot Quantitative vs Qualitative per pangkat (DD, AD, M, AM) |
| `Education_Score` | Konversi kategori pendidikan → skor numerik |
| `Certification_Score` | Konversi kategori sertifikasi → skor numerik |
| `K3_Score` | Konversi kategori K3 (SB/B/CB/KB) → skor numerik — **sheet tambahan**, dibuat supaya K3 bisa dihitung transparan sebagai bagian Qualitative Score |
| `Potensi_Score` | Konversi kategori Potensi (**Future Leader** > **High Impact Performer** > **Core Employee**, dari yang terbaik) → skor numerik — **sheet tambahan** |
| `Thresholds` | Ambang batas: minimum NK, minimum sisa dinas, **MDG Threshold Promosi Grade**, **MDGS Threshold Promosi Pangkat** |

Catatan: kolom `Readiness` **tidak disimpan sebagai data mentah** — selalu
dihitung otomatis oleh `scoring.py` dari MDG/MDGS tiap pegawai (lihat bagian
"Alur bisnis" di bawah).

Semua tabel di atas (kecuali `Employees`) bisa dikelola penuh (Create, Read,
Update, Delete) lewat halaman **Master Data**:

- **Update** — ubah nilai langsung di tabel, lalu klik "Simpan perubahan nilai". Kolom kunci (`Parameter`/`Kategori`/`Pangkat`) dikunci saat edit supaya tidak sampai mismatch dengan nilai yang dipakai di data pegawai.
- **Create** — isi form "➕ Tambah baris" di bawah tabel.
- **Delete** — pilih baris di "🗑️ Hapus baris", lalu klik "Hapus baris terpilih".

`Employees` **sengaja tidak bisa diedit dari aplikasi ini** — datanya
diperlakukan sebagai sumber tetap (fixed) yang ditarik dari sistem lain
(mis. SIM SDM/HRIS), bukan dikelola manual di SIKABI.

## Alur bisnis (penting — pernah salah di versi sebelumnya, sudah diperbaiki)

```
Seleksi Administrasi → Seleksi Kriteria KPP → Cek Grade (Reguler / Senior)
                                                   │
                        ┌──────────────────────────┴───────────────────────────┐
                        │ Reguler                                    Senior     │
                        ▼                                                ▼
                 Jalur Promosi Grade                          Readiness KPP + Kuadran
             (MDG >= threshold → "Ready                    (MDGS >= threshold → "Ready
              Promosi Grade", kalau                          Now"; kalau belum →
              belum → "Belum Siap                            "Ready Next")
              Promosi Grade")
             TIDAK masuk Kuadran                             MASUK Kuadran Prioritisasi
```

Definisi:
- **MDG** (Masa Dinas Grade) — lama waktu pegawai berstatus **Reguler** di pangkat saat ini. Syarat naik ke Senior: **MDG ≥ 3 tahun** (berlaku sama untuk semua pangkat).
- **MDGS** (Masa Dinas Grade Senior) — lama waktu pegawai sudah berstatus **Senior** di pangkat saat ini (0 kalau masih Reguler). Syarat "siap promosi pangkat": **MDGS ≥ 2 tahun** (berlaku sama untuk semua pangkat).
- **MDP** (Masa Dinas Pangkat) = **MDG + MDGS** — dipakai sebagai salah satu sumbu Kuadran.
- **Kuadran Prioritisasi hanya berisi pegawai Grade Senior** yang lolos Kriteria KPP. Pegawai Reguler, meskipun lolos Kriteria KPP, tidak pernah masuk Kuadran — mereka ada di jalur Promosi Grade sendiri.
- **Readiness** punya 5 kemungkinan nilai: `Ready Now`, `Ready Next` (keduanya khusus populasi Senior/Proses KPP), `Ready Promosi Grade`, `Belum Siap Promosi Grade` (keduanya khusus populasi Reguler), dan `Tidak Eligible` (tidak lolos Administrasi/KPP).
- Kedua threshold (MDG & MDGS) disimpan sebagai baris di sheet `Thresholds`, jadi bisa diubah lewat Master Data tanpa sentuh kode.

## Perubahan pada update ini

1. **Desain & navbar** — navbar sidebar sempat dicoba pakai library
   `streamlit-option-menu`, tapi ternyata library itu merender dirinya di
   dalam `iframe` terpisah sehingga CSS tema aplikasi tidak bisa menembus ke
   dalamnya — muncul sebagai kotak putih aneh di sidebar. **Sudah diganti ke
   tombol native Streamlit** (`st.button` dengan `type="primary"` untuk menu
   yang sedang aktif), yang otomatis ikut tema teal karena dirender langsung
   di DOM utama, tanpa iframe. Palet warna keseluruhan diganti dari merah
   default Streamlit ke navy/teal (lihat token warna di bagian atas
   `app.py`: `BRAND`, `TEAL`, dst) — termasuk warna chip pada semua filter
   multiselect. Kartu metrik di Dashboard diganti dari `st.metric` bawaan
   menjadi kartu custom (`metric_card()`) yang lebih rapi.

2. **Ringkasan kuadran** — tiap kuadran sekarang punya penjelasan singkat
   (`KUADRAN_DESC` di `scoring.py`), dan tombol **"Lihat N nama di Kuadran X"**
   yang membuka daftar nama pegawai (mengikuti filter pangkat/satker yang aktif
   di dashboard) lengkap dengan tombol unduh Excel per kuadran.

3. **Bug visualisasi kuadran — sudah diperbaiki.** Datanya **memang benar-benar
   dikalkulasi**, bukan dummy — Mean & perbandingan kuadran dihitung per pangkat
   di `scoring.py` (`compute_all()`, bagian "Kuadran"), persis rumus yang Anda
   berikan. Yang salah adalah **visualisasinya**: chart lama menggambar satu
   garis rata-rata tunggal dari subset pegawai yang sedang difilter, padahal
   tiap titik sebenarnya diklasifikasikan memakai rata-rata **pangkatnya
   masing-masing** — jadi kalau beberapa pangkat ditampilkan bersamaan, garis
   itu tidak nyambung dengan warna titiknya. Diperbaiki dengan mem-plot
   **selisih (delta) tiap pegawai terhadap mean pangkatnya sendiri**
   (`Delta_QScore`, `Delta_MDP` — kolom baru di `scoring.py`), sehingga garis
   0,0 akan selalu konsisten dengan kuadran manapun kombinasi filternya.

4. **MDP & Readiness** — MDP (Masa Dinas Pangkat) dihitung dari kolom
   `Tanggal_Grade` (lihat catatan asumsi di bawah). Readiness **sekarang
   dihitung**, bukan lagi kolom acak di Excel: pegawai yang sudah masuk Proses
   KPP = "Ready Now"; yang lolos KPP tapi masih menunggu MDG tercukupi
   diklasifikasikan "Ready 1 Tahun Lagi" / "Ready 2 Tahun Lagi" / "Ready >2
   Tahun Lagi" berdasarkan selisih MDG terhadap threshold; sisanya "Belum
   Siap". Ditampilkan sebagai bar chart di Dashboard.

5. **Filter Data Pegawai** — pangkat, satuan kerja, dan status akhir sekarang
   multiselect.

6. **Tab Gate Keputusan** — label tab dirapikan tanpa penomoran ("Syarat
   Administrasi", "Kriteria KPP", "Grade Senior / MDG").

7. **Tombol dead** "🔄 Sinkronisasi data dengan HRIS & KATALIS" ditambahkan di
   sidebar, di bawah tombol unduh data — non-aktif (`disabled=True`) sebagai
   placeholder untuk integrasi masa depan.

8. **Populasi data** — pangkat **S-A dihapus**, sisa DD/AD/M/AM saja. Jumlah
   data dummy dinaikkan ke **2.500 pegawai** (`data_gen.py`).

9. **Logo** — logo yang Anda upload disimpan di `assets/Sikabi.png`, dipakai
   sebagai favicon (page icon) dan header sidebar. **Kalau Anda sudah punya URL
   final di GitHub**, tinggal ganti baris `LOGO_PATH` di `app.py` jadi URL
   tersebut, atau paling gampang: timpa saja file `assets/Sikabi.png` dengan
   versi final Anda — tidak perlu ubah kode lain.

## Catatan penting soal penyimpanan data

Tombol **Simpan Perubahan** di halaman Master Data menulis ulang file
`data/sikabi_data.xlsx` di server tempat aplikasi berjalan. Ini bekerja normal
saat dijalankan **lokal**. Kalau di-deploy ke **Streamlit Community Cloud**,
penyimpanan filesystem bersifat sementara (ephemeral) — perubahan bisa hilang
saat aplikasi restart/redeploy. Untuk pemakaian produksi jangka panjang,
sebaiknya ganti sumber data dari file Excel lokal ke database (mis. Google
Sheets API, PostgreSQL, atau Supabase) — struktur `scoring.py` sudah dipisah
dari logika baca/tulis data sehingga penggantian ini tidak perlu mengubah
rumus perhitungan.

Tombol **Unduh data (.xlsx)** di sidebar selalu tersedia sebagai cara aman
untuk mengambil salinan data terbaru kapan saja.

## Deploy ke Streamlit Community Cloud

1. Push folder ini ke repository GitHub (termasuk folder `assets/` dan `data/`).
2. Buka [share.streamlit.io](https://share.streamlit.io), sambungkan ke repo tersebut.
3. Set **Main file path** ke `app.py`.
4. Deploy.

## Asumsi & catatan implementasi

- **MDG dan MDGS** dihitung dari 2 kolom tanggal: `Tanggal_Mulai_Pangkat` (mulai
  jadi Reguler) dan `Tanggal_Mulai_Senior` (mulai jadi Senior, kosong kalau
  masih Reguler). Ini data dummy — kalau sumber data asli BI punya struktur
  tanggal yang beda, sesuaikan pembacaan tanggal di `compute_all()`.
- **Threshold promosi** (MDG ≥ 3 th untuk naik grade, MDGS ≥ 2 th untuk naik
  pangkat) saat ini seragam untuk semua pangkat sesuai instruksi terakhir.
  Kalau ternyata harus beda per pangkat (mis. DD beda dengan AM), tinggal ganti
  baris `Thresholds` jadi per-pangkat dan sesuaikan lookup di `scoring.py`.
- **Mean & Standar Deviasi** untuk skor NK dan MDP (komponen Quantitative
  Score) dihitung dari seluruh populasi pegawai (BI Wide), bukan per pangkat —
  beda dengan Mean untuk **Kuadran** yang memang sudah per pangkat. Sesuaikan
  fungsi `compute_all()` di `scoring.py` kalau NK/MDP juga perlu per pangkat.
- **Passing Grade** Gate KPP dihitung sebagai rata-rata QScore/Quantitative/
  Qualitative dari pegawai yang sudah lolos Gate Administrasi, dikelompokkan
  per pangkat.
- **Potensi** sekarang kategorikal (Future Leader / High Impact Performer /
  Core Employee), dikonversi ke skor lewat sheet `Potensi_Score` — bisa
  diedit di Master Data seperti tabel skor kategorikal lainnya.

