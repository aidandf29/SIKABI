# SIKABI — Streamlit + Excel

Prototype SIKABI dengan **Excel sebagai sumber data**.

## Struktur
- `app.py` — aplikasi Streamlit
- `sikabi_data.xlsx` — sumber data dan master configuration
- `requirements.txt` — dependency

## Jalankan
```bash
pip install -r requirements.txt
streamlit run app.py
```

## CRUD
CRUD hanya tersedia di **Master Data**:
- Create / Read / Update / Delete pegawai
- Edit bobot quantitative & qualitative
- Edit bobot per pangkat
- Edit mapping pendidikan & sertifikasi
- Edit threshold
- Download Excel terbaru
- Upload Excel baru untuk sesi aktif

Dashboard, Data Pegawai & Scoring, dan Gate Decision membaca data dari Excel lalu menghitung hasil scoring.

## Catatan deployment
Untuk lokal, perubahan CRUD dapat menulis kembali `sikabi_data.xlsx`.

Pada Streamlit Community Cloud, filesystem aplikasi bersifat ephemeral. Artinya perubahan yang ditulis ke file Excel saat runtime **tidak boleh dianggap sebagai penyimpanan permanen**. Untuk demo, gunakan tombol Download Excel terbaru lalu simpan/push kembali file tersebut. Untuk production, Excel sebaiknya ditempatkan di storage persisten seperti SharePoint/OneDrive/Google Drive atau diganti database.
