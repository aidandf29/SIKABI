"""
SIKABI - Data Generator
Membuat file data/sikabi_data.xlsx berisi 2.500 data dummy pegawai
(pangkat DD, AD, M, AM) beserta seluruh tabel referensi (master data)
yang dipakai mesin skoring.

Jalankan: python data_gen.py
"""

import random
from datetime import datetime, timedelta

import pandas as pd

random.seed(42)

N_EMPLOYEES = 2500

FIRST_NAMES = [
    "Andi", "Bima", "Citra", "Dimas", "Eka", "Farhan", "Gita", "Hana", "Irfan", "Joko",
    "Kirana", "Luthfi", "Maya", "Nadia", "Oscar", "Putri", "Raka", "Sinta", "Taufik", "Vina",
    "Wulan", "Yusuf", "Zahra", "Bagas", "Cahyo", "Dewi", "Erlangga", "Fitri", "Galih", "Hesti",
    "Ilham", "Julia", "Krisna", "Lestari", "Miko", "Nurul", "Omar", "Prita", "Rian", "Sari",
]
LAST_NAMES = [
    "Pratama", "Wijaya", "Lestari", "Saputra", "Putri", "Akbar", "Maharani", "Salsabila",
    "Ramadhan", "Santoso", "Ayu", "Hakim", "Anindita", "Permata", "Amelia", "Nugraha",
    "Kartika", "Hidayat", "Firmansyah", "Utami", "Gunawan", "Rahayu", "Handayani", "Setiawan",
]

SATKER_UNIT = {
    "DMST": "Direktorat DMST",
    "DSDMM": "Direktorat DSDMM",
    "DKMP": "Direktorat DKMP",
    "DEIH": "Direktorat DEIH",
    "DMR": "Direktorat DMR",
    "DKEM": "Direktorat DKEM",
    "DPSP": "Direktorat DPSP",
    "DKOM": "Direktorat DKOM",
}
SATKERS = list(SATKER_UNIT.keys())

PANGKAT_ORDER = ["DD", "AD", "M", "AM"]

PENDIDIKAN_OPTS = ["S3", "S2 A/PTB", "S2 lainnya", "S1 Officer", "D3 Non-Officer"]
PENDIDIKAN_WEIGHTS = [0.08, 0.16, 0.18, 0.40, 0.18]

SERTIFIKASI_OPTS = ["Tier 1", "Tier 2", "PMK", "Kum Mengajar", "ELP", "None"]
SERTIFIKASI_WEIGHTS = [0.14, 0.18, 0.14, 0.12, 0.12, 0.30]

K3_OPTS = ["SB", "B", "CB", "KB"]
K3_WEIGHTS = [0.28, 0.36, 0.24, 0.12]

# Diurutkan dari yang terbaik ke yang paling dasar
POTENSI_OPTS = ["Future Leader", "High Impact Performer", "Core Employee"]
POTENSI_WEIGHTS = [0.15, 0.35, 0.50]

TODAY = datetime(2026, 9, 14)


def gen_grade_dates(pangkat, sublevel):
    """
    Menghasilkan tanggal mulai pangkat (sebagai Reguler) dan, jika berlaku,
    tanggal mulai menjadi Senior pada pangkat yang sama.

    MDG  (Masa Dinas Grade)        = lama waktu sebagai Reguler
    MDGS (Masa Dinas Grade Senior) = lama waktu sebagai Senior (0 jika masih Reguler)
    MDP  (Masa Dinas Pangkat)      = MDG + MDGS
    """
    if sublevel == "Senior":
        mdg_saat_naik_senior = random.uniform(2.5, 4.5)   # lama sebagai Reguler sebelum naik jadi Senior
        mdgs_saat_ini = random.uniform(0, 4)               # lama sudah menjadi Senior sampai sekarang
        tanggal_mulai_senior = TODAY - timedelta(days=mdgs_saat_ini * 365)
        tanggal_mulai_pangkat = tanggal_mulai_senior - timedelta(days=mdg_saat_naik_senior * 365)
        return tanggal_mulai_pangkat, tanggal_mulai_senior
    else:
        mdg_saat_ini = random.uniform(0.1, 4.5)
        tanggal_mulai_pangkat = TODAY - timedelta(days=mdg_saat_ini * 365)
        return tanggal_mulai_pangkat, pd.NaT


def gen_employee(i):
    pangkat = PANGKAT_ORDER[i % len(PANGKAT_ORDER)]
    sublevel = "Reguler"
    if random.random() < 0.28:
        sublevel = "Senior"

    satker = random.choice(SATKERS)
    nama = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
    nip = f"19{80 + i % 20}{(i % 12) + 1:02d}{(i % 28) + 1:02d}{1000 + i}"

    nk_values = [round(random.uniform(2.5, 4.0), 2) for _ in range(5)]

    pendidikan = random.choices(PENDIDIKAN_OPTS, weights=PENDIDIKAN_WEIGHTS)[0]
    sertifikasi = random.choices(SERTIFIKASI_OPTS, weights=SERTIFIKASI_WEIGHTS)[0]
    exposure = random.randint(35, 100)
    potensi = random.choices(POTENSI_OPTS, weights=POTENSI_WEIGHTS)[0]
    k3 = random.choices(K3_OPTS, weights=K3_WEIGHTS)[0]

    status = random.choices(
        ["Aktif", "Cuti Sakit", "Sanksi", "CLTB", "Pemberhentian Sementara"],
        weights=[0.90, 0.03, 0.03, 0.02, 0.02],
    )[0]
    ptb_s2 = random.random() < 0.05
    promotion_award = random.random() < 0.08
    satker_rec = random.choices(["Direkomendasikan", "Tidak Direkomendasikan"], weights=[0.85, 0.15])[0]
    remaining_service = round(random.uniform(0.2, 20), 1)

    tanggal_mulai_pangkat, tanggal_mulai_senior = gen_grade_dates(pangkat, sublevel)

    return {
        "NIP": nip,
        "Nama": nama,
        "Unit": SATKER_UNIT[satker],
        "Satker": satker,
        "Pangkat": pangkat,
        "Sublevel": sublevel,
        "Tanggal_Mulai_Pangkat": tanggal_mulai_pangkat,
        "Tanggal_Mulai_Senior": tanggal_mulai_senior,
        "NK_1": nk_values[0],
        "NK_2": nk_values[1],
        "NK_3": nk_values[2],
        "NK_4": nk_values[3],
        "NK_5": nk_values[4],
        "Pendidikan": pendidikan,
        "Sertifikasi": sertifikasi,
        "Exposure": exposure,
        "Potensi": potensi,
        "K3": k3,
        "Status": status,
        "PTB_S2": ptb_s2,
        "Promotion_Award": promotion_award,
        "Satker_Recommendation": satker_rec,
        "Remaining_Service": remaining_service,
    }


def build_workbook(path):
    employees = pd.DataFrame([gen_employee(i) for i in range(N_EMPLOYEES)])

    quant_weights = pd.DataFrame(
        {"Parameter": ["NK", "MDP", "Pendidikan", "Sertifikasi"], "Value": [0.35, 0.25, 0.30, 0.10]}
    )
    qual_weights = pd.DataFrame(
        {"Parameter": ["Exposure", "Potensi", "K3"], "Value": [0.25, 0.20, 0.55]}
    )
    rank_weights = pd.DataFrame(
        {
            "Pangkat": PANGKAT_ORDER,
            "Quantitative": [0.40, 0.45, 0.55, 0.60],
            "Qualitative": [0.60, 0.55, 0.45, 0.40],
        }
    )
    education_score = pd.DataFrame(
        {"Kategori": PENDIDIKAN_OPTS, "Nilai": [100, 85, 70, 55, 40]}
    )
    certification_score = pd.DataFrame(
        {"Kategori": SERTIFIKASI_OPTS, "Nilai": [40, 25, 15, 10, 10, 0]}
    )
    # Tabel tambahan: konversi kategori K3 ke skor numerik (tidak ada di file asli,
    # ditambahkan supaya K3 bisa masuk hitungan Qualitative Score secara transparan)
    k3_score = pd.DataFrame({"Kategori": K3_OPTS, "Nilai": [100, 75, 50, 25]})
    # Tabel tambahan: konversi kategori Potensi (Future Leader / High Impact
    # Performer / Core Employee, dari yang terbaik ke yang paling dasar) ke skor numerik
    potensi_score = pd.DataFrame({"Kategori": POTENSI_OPTS, "Nilai": [100, 70, 45]})
    thresholds = pd.DataFrame(
        {
            "Parameter": [
                "MDG Threshold Promosi Grade (tahun)",
                "MDGS Threshold Promosi Pangkat (tahun)",
                "Minimum NK",
                "Minimum Remaining Service (tahun)",
            ],
            "Value": [3, 2, 3, 0.5],
        }
    )

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        employees.to_excel(writer, sheet_name="Employees", index=False)
        quant_weights.to_excel(writer, sheet_name="Quant_Weights", index=False)
        qual_weights.to_excel(writer, sheet_name="Qual_Weights", index=False)
        rank_weights.to_excel(writer, sheet_name="Rank_Weights", index=False)
        education_score.to_excel(writer, sheet_name="Education_Score", index=False)
        certification_score.to_excel(writer, sheet_name="Certification_Score", index=False)
        k3_score.to_excel(writer, sheet_name="K3_Score", index=False)
        potensi_score.to_excel(writer, sheet_name="Potensi_Score", index=False)
        thresholds.to_excel(writer, sheet_name="Thresholds", index=False)

    print(f"OK: {path} dibuat dengan {len(employees)} pegawai.")


if __name__ == "__main__":
    build_workbook("data/sikabi_data.xlsx")
