
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import date

st.set_page_config(
    page_title="SIKABI | Job Fit Intelligence",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================
# SIKABI — Sistem Intelijen Karier Bank Indonesia
# Streamlit prototype
# =========================================================

DEFAULT_CONFIG = {
    "quant_weights": {"NK": 0.35, "MDP": 0.25, "Pendidikan": 0.30, "Sertifikasi": 0.10},
    "qual_weights": {"Exposure": 0.25, "Potensi": 0.20, "K3": 0.55},
    "rank_weights": {
        "DD": {"Quantitative": 0.40, "Qualitative": 0.60},
        "AD": {"Quantitative": 0.45, "Qualitative": 0.55},
        "M": {"Quantitative": 0.55, "Qualitative": 0.45},
        "AM": {"Quantitative": 0.60, "Qualitative": 0.40},
        "S-A": {"Quantitative": 0.70, "Qualitative": 0.30},
    },
    "education_scores": {"S3": 100, "S2 A/PTB": 85, "S2 lainnya": 70, "S1 Officer": 55, "D3 Non-Officer": 40},
    "cert_scores": {"Tier 1": 40, "Tier 2": 25, "PMK": 15, "Kum Mengajar": 10, "ELP": 10},
    "mdg_threshold": 2.0,
    "min_nk": 3.0,
    "min_remaining_service": 0.5,
}

def init_state():
    if "config" not in st.session_state:
        st.session_state.config = DEFAULT_CONFIG.copy()
        st.session_state.config["quant_weights"] = DEFAULT_CONFIG["quant_weights"].copy()
        st.session_state.config["qual_weights"] = DEFAULT_CONFIG["qual_weights"].copy()
        st.session_state.config["rank_weights"] = {k: v.copy() for k, v in DEFAULT_CONFIG["rank_weights"].items()}
        st.session_state.config["education_scores"] = DEFAULT_CONFIG["education_scores"].copy()
        st.session_state.config["cert_scores"] = DEFAULT_CONFIG["cert_scores"].copy()
    if "employees" not in st.session_state:
        st.session_state.employees = make_demo_data()
    if "selected_nip" not in st.session_state:
        st.session_state.selected_nip = None
    if "notice" not in st.session_state:
        st.session_state.notice = ""

def make_demo_data():
    rng = np.random.default_rng(42)
    names = [
        "Andi Pratama","Bima Wijaya","Citra Lestari","Dimas Saputra","Eka Putri",
        "Farhan Akbar","Gita Maharani","Hana Salsabila","Irfan Ramadhan","Joko Santoso",
        "Kirana Ayu","Luthfi Hakim","Maya Anindita","Nadia Permata","Oscar Wijaya",
        "Putri Amelia","Raka Nugraha","Sinta Maharani","Taufik Hidayat","Vina Kartika"
    ]
    ranks = ["DD","AD","M","AM","S-A"]
    satkers = ["DMST","DSDMM","DKMP","DEIH","DMR"]
    education = ["S3","S2 A/PTB","S2 lainnya","S1 Officer","D3 Non-Officer"]
    certs = ["Tier 1","Tier 2","PMK","ELP","Kum Mengajar","None"]
    k3 = ["SB","B","CB","KB"]
    rows = []
    for i, name in enumerate(names, start=1):
        rank = ranks[(i-1) % len(ranks)]
        start = date(2020 + (i % 5), 1 + (i % 9), 1 + (i % 20))
        nk5 = np.clip(rng.normal(3.25, 0.35, 5), 2.2, 4.0)
        rows.append({
            "NIP": f"199{i:02d}{1000+i:04d}",
            "Nama": name,
            "Unit": "Direktorat " + satkers[(i-1) % len(satkers)],
            "Satker": satkers[(i-1) % len(satkers)],
            "Pangkat": rank,
            "Sublevel": "Senior" if i % 4 == 0 and rank != "S-A" else "Reguler",
            "Tanggal_Grade": pd.Timestamp(start),
            "NK_1": round(float(nk5[0]),2), "NK_2": round(float(nk5[1]),2),
            "NK_3": round(float(nk5[2]),2), "NK_4": round(float(nk5[3]),2),
            "NK_5": round(float(nk5[4]),2),
            "Pendidikan": education[(i-1) % len(education)],
            "Sertifikasi": certs[(i-1) % len(certs)],
            "Exposure": int(rng.integers(45, 96)),
            "Potensi": int(rng.integers(45, 96)),
            "K3": k3[(i-1) % len(k3)],
            "Status": "Aktif" if i != 17 else "Sanksi",
            "PTB_S2": False if i % 6 else True,
            "Promotion_Award": False if i % 7 else True,
            "Satker_Recommendation": "Direkomendasikan" if i % 5 != 0 else "Tidak Direkomendasikan",
            "Remaining_Service": round(float(rng.uniform(0.4, 8.0)),1),
            "MDP_Override": np.nan,
            "Readiness": ["Ready Now","Ready 1-2 Tahun","Belum Siap"][i % 3],
        })
    return pd.DataFrame(rows)

def education_score(row, cfg):
    return cfg["education_scores"].get(row["Pendidikan"], 0)

def cert_score(row, cfg):
    val = cfg["cert_scores"].get(row["Sertifikasi"], 0)
    return min(val, 100)

def calc_scores(df, cfg):
    out = df.copy()
    out["NK"] = out[[f"NK_{i}" for i in range(1,6)]].mean(axis=1)
    period = pd.Timestamp("2026-09-30")
    out["MDP"] = ((period - pd.to_datetime(out["Tanggal_Grade"])).dt.days / 365.25).clip(lower=0)
    out["MDG"] = out["MDP"]

    # Population statistics per rank
    nk_mean = out.groupby("Pangkat")["NK"].transform("mean")
    nk_std = out.groupby("Pangkat")["NK"].transform("std").fillna(0)
    mdp_mean = out.groupby("Pangkat")["MDP"].transform("mean")
    mdp_std = out.groupby("Pangkat")["MDP"].transform("std").fillna(0)

    out["NK_Mean_Rank"] = nk_mean
    out["NK_StDev_Rank"] = nk_std
    out["MDP_Mean_Rank"] = mdp_mean
    out["MDP_StDev_Rank"] = mdp_std

    out["NK_Score"] = np.select(
        [out["NK"] > nk_mean + nk_std, out["NK"] >= nk_mean - nk_std],
        [100, 60], default=20
    )
    out["MDP_Score"] = np.select(
        [out["MDP"] > mdp_mean + mdp_std, out["MDP"] >= mdp_mean - mdp_std],
        [100, 60], default=20
    )
    out["Pendidikan_Score"] = out.apply(lambda r: education_score(r,cfg), axis=1)
    out["Sertifikasi_Score"] = out.apply(lambda r: cert_score(r,cfg), axis=1)

    qw = cfg["quant_weights"]
    out["Quantitative"] = (
        out["NK_Score"] * qw["NK"] +
        out["MDP_Score"] * qw["MDP"] +
        out["Pendidikan_Score"] * qw["Pendidikan"] +
        out["Sertifikasi_Score"] * qw["Sertifikasi"]
    )

    k3_map = {"SB":100, "B":80, "CB":60, "KB":30}
    out["K3_Score"] = out["K3"].map(k3_map).fillna(0)
    lw = cfg["qual_weights"]
    out["Qualitative"] = (
        out["Exposure"] * lw["Exposure"] +
        out["Potensi"] * lw["Potensi"] +
        out["K3_Score"] * lw["K3"]
    )

    out["Quant_Weight"] = out["Pangkat"].map({k:v["Quantitative"] for k,v in cfg["rank_weights"].items()})
    out["Qual_Weight"] = out["Pangkat"].map({k:v["Qualitative"] for k,v in cfg["rank_weights"].items()})
    out["QScore"] = out["Quantitative"] * out["Quant_Weight"] + out["Qualitative"] * out["Qual_Weight"]

    # Gate 1 — 8 administrative checks
    out["G1_MDG"] = out["MDG"] >= cfg["mdg_threshold"]
    out["G1_Service"] = out["Remaining_Service"] > cfg["min_remaining_service"]
    out["G1_NK"] = out["NK"] >= cfg["min_nk"]
    out["G1_Education"] = out["Pendidikan"].isin(["S3","S2 A/PTB","S2 lainnya","S1 Officer","D3 Non-Officer"])
    out["G1_Recommendation"] = out["Satker_Recommendation"].eq("Direkomendasikan")
    out["G1_Status"] = out["Status"].eq("Aktif")
    out["G1_PTB"] = ~out["PTB_S2"]
    out["G1_Award"] = ~out["Promotion_Award"]
    g1_cols = ["G1_MDG","G1_Service","G1_NK","G1_Education","G1_Recommendation","G1_Status","G1_PTB","G1_Award"]
    out["Gate_1"] = out[g1_cols].all(axis=1)

    # Gate 2 — all four criteria assumed AND per draft requirement
    q_mean = out.groupby("Pangkat")["Quantitative"].transform("mean")
    l_mean = out.groupby("Pangkat")["Qualitative"].transform("mean")
    qs_mean = out.groupby("Pangkat")["QScore"].transform("mean")
    out["Passing_Quant"] = q_mean
    out["Passing_Qual"] = l_mean
    out["Passing_QScore"] = qs_mean
    out["G2_NK"] = out["NK"] >= cfg["min_nk"]
    out["G2_Quant"] = out["Quantitative"] >= q_mean
    out["G2_Qual"] = out["Qualitative"] >= l_mean
    out["G2_QScore"] = out["QScore"] >= qs_mean
    out["Gate_2"] = out[["G2_NK","G2_Quant","G2_Qual","G2_QScore"]].all(axis=1)

    out["Is_Senior"] = out["Sublevel"].eq("Senior") | out["Pangkat"].eq("S-A")
    out["Gate_3"] = np.where(out["Is_Senior"], True, out["MDG"] >= cfg["mdg_threshold"])
    out["KPP_Eligible"] = out["Gate_1"] & out["Gate_2"] & out["Gate_3"]

    # Quadrant among KPP population, per rank
    kpp_q_mean = out.groupby("Pangkat")["QScore"].transform("mean")
    kpp_m_mean = out.groupby("Pangkat")["MDP"].transform("mean")
    out["KPP_QMean"] = kpp_q_mean
    out["KPP_Mean_MDP"] = kpp_m_mean
    conditions = [
        out["KPP_Eligible"] & (out["QScore"] >= kpp_q_mean) & (out["MDP"] >= kpp_m_mean),
        out["KPP_Eligible"] & (out["QScore"] >= kpp_q_mean) & (out["MDP"] < kpp_m_mean),
        out["KPP_Eligible"] & (out["QScore"] < kpp_q_mean) & (out["MDP"] >= kpp_m_mean),
        out["KPP_Eligible"] & (out["QScore"] < kpp_q_mean) & (out["MDP"] < kpp_m_mean),
    ]
    out["Quadrant"] = np.select(conditions, ["I","II","III","IV"], default="-")

    def outcome(r):
        if r["KPP_Eligible"]:
            return "KPP / Promosi Pipeline"
        if not r["Gate_1"]:
            return "General Talent — Gate 1"
        if not r["Gate_2"]:
            return "General Talent — Gate 2"
        return "General Talent — Gate 3"
    out["Outcome"] = out.apply(outcome, axis=1)
    return out

def apply_css():
    st.markdown("""
    <style>
    .block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
    .brand {font-size: 1.35rem; font-weight: 750; letter-spacing: .2px;}
    .subtitle {color:#6b7280; font-size:.9rem; margin-top:-10px; margin-bottom:20px;}
    .metric-card {padding:14px 16px; border:1px solid #e5e7eb; border-radius:12px; background:#fff;}
    .small-note {font-size:.82rem; color:#6b7280;}
    </style>
    """, unsafe_allow_html=True)

def metric_row(df):
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Total Pegawai", len(df))
    c2.metric("Eligible Scoring", int((df["Gate_1"]).sum()))
    c3.metric("Lolos Gate 2", int((df["Gate_1"] & df["Gate_2"]).sum()))
    c4.metric("Masuk KPP", int(df["KPP_Eligible"].sum()))
    c5.metric("General Talent", int((~df["KPP_Eligible"]).sum()))

def dashboard(df):
    st.title("Dashboard")
    st.caption("SIKABI — Sistem Intelijen Karier Bank Indonesia | Periode Penilaian 2026")
    metric_row(df)

    st.divider()
    left, right = st.columns([1.6, 1])
    with left:
        st.subheader("Peta Kuadran Talent")
        qdf = df[df["KPP_Eligible"]].copy()
        if qdf.empty:
            st.info("Belum ada pegawai yang masuk KPP.")
        else:
            fig = px.scatter(
                qdf, x="MDP", y="QScore", color="Quadrant", text="Nama",
                hover_data=["NIP","Pangkat","Satker","Readiness"],
                labels={"MDP":"Masa Dinas Pangkat (tahun)","QScore":"QScore"},
                height=480
            )
            fig.update_traces(textposition="top center")
            st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader("Distribusi Outcome")
        counts = df["Outcome"].value_counts().reset_index()
        counts.columns = ["Outcome","Jumlah"]
        fig2 = px.bar(counts, x="Jumlah", y="Outcome", orientation="h", height=300)
        st.plotly_chart(fig2, use_container_width=True)
        st.subheader("Distribusi Quadrant")
        qcounts = df[df["KPP_Eligible"]]["Quadrant"].value_counts().reindex(["I","II","III","IV"], fill_value=0)
        st.dataframe(qcounts.rename("Jumlah").to_frame(), use_container_width=True)

def data_scoring(df, cfg):
    st.title("Data Pegawai & Scoring")
    st.caption("Data input, pembentukan score, decision gate, dan outcome ditampilkan dalam satu halaman.")

    c1,c2,c3 = st.columns(3)
    satker = c1.multiselect("Satker", sorted(df["Satker"].unique()), default=list(df["Satker"].unique()))
    rank = c2.multiselect("Pangkat", sorted(df["Pangkat"].unique()), default=list(df["Pangkat"].unique()))
    status = c3.selectbox("Status Outcome", ["Semua"] + sorted(df["Outcome"].unique()))
    view = df[df["Satker"].isin(satker) & df["Pangkat"].isin(rank)].copy()
    if status != "Semua":
        view = view[view["Outcome"] == status]

    st.subheader("Tabel Penilaian")
    display_cols = ["NIP","Nama","Satker","Pangkat","Sublevel","NK","MDP","Pendidikan","Sertifikasi",
                    "Quantitative","Qualitative","QScore","Gate_1","Gate_2","Gate_3","KPP_Eligible","Quadrant","Outcome"]
    table_df = view[display_cols].copy()
    for col in ["NK","MDP","Quantitative","Qualitative","QScore"]:
        table_df[col] = table_df[col].round(2)
    st.dataframe(table_df, use_container_width=True, hide_index=True)

    st.download_button(
        "⬇️ Export hasil scoring (CSV)",
        data=table_df.to_csv(index=False).encode("utf-8"),
        file_name="SIKABI_scoring_result.csv",
        mime="text/csv",
    )

    st.divider()
    st.subheader("Detail Pegawai")
    if len(view):
        selected = st.selectbox("Pilih pegawai", view["NIP"].tolist(),
                                format_func=lambda x: f"{x} — {view.loc[view['NIP'].eq(x),'Nama'].iloc[0]}")
        r = view[view["NIP"].eq(selected)].iloc[0]
        a,b,c = st.columns(3)
        a.metric("QScore", f"{r.QScore:.2f}")
        b.metric("Quantitative", f"{r.Quantitative:.2f}")
        c.metric("Qualitative", f"{r.Qualitative:.2f}")

        t1,t2,t3,t4 = st.tabs(["Score Breakdown","Gate 1","Gate 2 & MDG","KPP & Quadrant"])
        with t1:
            breakdown = pd.DataFrame({
                "Komponen":["NK","MDP","Pendidikan","Sertifikasi","Exposure","Potensi","K3"],
                "Nilai":[r.NK_Score,r.MDP_Score,r.Pendidikan_Score,r.Sertifikasi_Score,r.Exposure,r.Potensi,r.K3_Score],
                "Bobot":[cfg["quant_weights"]["NK"],cfg["quant_weights"]["MDP"],cfg["quant_weights"]["Pendidikan"],
                         cfg["quant_weights"]["Sertifikasi"],cfg["qual_weights"]["Exposure"],cfg["qual_weights"]["Potensi"],cfg["qual_weights"]["K3"]]
            })
            breakdown["Kontribusi"] = breakdown["Nilai"] * breakdown["Bobot"]
            st.dataframe(breakdown.round(2), use_container_width=True, hide_index=True)
            st.info(f"QScore = Quantitative ({r.Quantitative:.2f}) × {r.Quant_Weight:.0%} + Qualitative ({r.Qualitative:.2f}) × {r.Qual_Weight:.0%} = {r.QScore:.2f}")
        with t2:
            gate1 = [
                ("1. MDG memenuhi threshold", bool(r.G1_MDG), f"{r.MDG:.2f} thn ≥ {cfg['mdg_threshold']:.2f}"),
                ("2. Sisa masa dinas > 6 bulan", bool(r.G1_Service), f"{r.Remaining_Service:.1f} thn"),
                ("3. Rata-rata NK ≥ 3,00", bool(r.G1_NK), f"{r.NK:.2f}"),
                ("4. Pendidikan minimum", bool(r.G1_Education), r.Pendidikan),
                ("5. Rekomendasi Satker", bool(r.G1_Recommendation), r.Satker_Recommendation),
                ("6. Status aktif", bool(r.G1_Status), r.Status),
                ("7. Tidak sedang PTB S2", bool(r.G1_PTB), str(not bool(r.PTB_S2))),
                ("8. Tidak ada promotion award", bool(r.G1_Award), str(not bool(r.Promotion_Award))),
            ]
            st.dataframe(pd.DataFrame(gate1, columns=["Kriteria","Pass","Evidence"]), use_container_width=True, hide_index=True)
            st.success("Gate 1 PASS" if r.Gate_1 else "Gate 1 FAIL")
        with t3:
            gate2 = [
                ("NK ≥ 3,00", bool(r.G2_NK), f"{r.NK:.2f}"),
                ("Quantitative ≥ mean pangkat", bool(r.G2_Quant), f"{r.Quantitative:.2f} vs {r.Passing_Quant:.2f}"),
                ("Qualitative ≥ mean pangkat", bool(r.G2_Qual), f"{r.Qualitative:.2f} vs {r.Passing_Qual:.2f}"),
                ("QScore ≥ mean pangkat", bool(r.G2_QScore), f"{r.QScore:.2f} vs {r.Passing_QScore:.2f}"),
                ("MDG / routing", bool(r.Gate_3), "Senior" if r.Is_Senior else f"{r.MDG:.2f} thn"),
            ]
            st.dataframe(pd.DataFrame(gate2, columns=["Kriteria","Pass","Evidence"]), use_container_width=True, hide_index=True)
            st.warning("Gate 2 masih menggunakan asumsi AND dari draft requirement.") 
        with t4:
            st.write(f"**Readiness:** {r.Readiness}")
            st.write(f"**Quadrant:** {r.Quadrant}")
            st.write(f"**Outcome:** {r.Outcome}")
            if r.KPP_Eligible:
                st.success("Pegawai masuk pipeline KPP.")
            else:
                st.error("Pegawai belum masuk pipeline KPP.")

def gate_decision(df, cfg):
    st.title("Gate Decision")
    st.caption("Fokus halaman: menjelaskan mengapa pegawai lolos/tidak lolos setiap tahap.")

    tab1, tab2, tab3 = st.tabs(["Gate 1 — Administrasi","Gate 2 — Kriteria KPP","Gate 3 — MDG / Routing"])
    with tab1:
        rows = []
        for _,r in df.iterrows():
            failed = 8 - int(r[["G1_MDG","G1_Service","G1_NK","G1_Education","G1_Recommendation","G1_Status","G1_PTB","G1_Award"]].sum())
            rows.append([r.NIP,r.Nama,r.Satker,r.Pangkat,"PASS" if r.Gate_1 else "FAIL",failed])
        st.dataframe(pd.DataFrame(rows, columns=["NIP","Nama","Satker","Pangkat","Gate 1","Jumlah Fail"]),
                     use_container_width=True, hide_index=True)
    with tab2:
        rows = []
        for _,r in df.iterrows():
            rows.append([r.NIP,r.Nama,r.Pangkat,r.NK,r.Quantitative,r.Passing_Quant,r.Qualitative,r.Passing_Qual,
                         r.QScore,r.Passing_QScore,"PASS" if r.Gate_2 else "FAIL"])
        g = pd.DataFrame(rows, columns=["NIP","Nama","Pangkat","NK","Quant","PG Quant","Qual","PG Qual","QScore","PG QScore","Gate 2"])
        st.dataframe(g.round(2), use_container_width=True, hide_index=True)
    with tab3:
        g3 = df[["NIP","Nama","Pangkat","Sublevel","Is_Senior","MDG","Gate_3","KPP_Eligible","Outcome"]].copy()
        g3["MDG"] = g3["MDG"].round(2)
        st.dataframe(g3, use_container_width=True, hide_index=True)
    st.info("Catatan: Gate 2 AND, formula KPP, kategori readiness, dan beberapa parameter kebijakan masih berstatus open item dalam requirement draft.")

def master_data(df, cfg):
    st.title("Master Data & Configuration")
    st.caption("Parameter scoring dibuat editable agar tidak hardcoded di aplikasi.")

    tab1, tab2, tab3, tab4 = st.tabs(["Bobot Score","Mapping Nilai","Threshold","Data Pegawai Demo"])
    with tab1:
        st.subheader("Quantitative")
        cols = st.columns(4)
        keys = list(cfg["quant_weights"])
        for i,k in enumerate(keys):
            cfg["quant_weights"][k] = cols[i].number_input(k, 0.0, 1.0, float(cfg["quant_weights"][k]), 0.05, format="%.2f")
        st.write("Total:", f"{sum(cfg['quant_weights'].values()):.0%}")
        st.subheader("Qualitative")
        cols = st.columns(3)
        for i,k in enumerate(cfg["qual_weights"]):
            cfg["qual_weights"][k] = cols[i].number_input(k, 0.0, 1.0, float(cfg["qual_weights"][k]), 0.05, format="%.2f")
        st.write("Total:", f"{sum(cfg['qual_weights'].values()):.0%}")
        st.subheader("Bobot Quantitative vs Qualitative per Pangkat")
        rw = pd.DataFrame(cfg["rank_weights"]).T
        edited = st.data_editor(rw, use_container_width=True, num_rows="fixed", key="rank_weights_editor")
        if st.button("💾 Simpan bobot pangkat"):
            cfg["rank_weights"] = edited.to_dict(orient="index")
            st.session_state.notice = "Bobot pangkat berhasil disimpan."
            st.rerun()
    with tab2:
        st.subheader("Mapping Pendidikan")
        edu = pd.DataFrame({"Nilai": cfg["education_scores"]})
        edu_edit = st.data_editor(edu, use_container_width=True, key="edu_editor")
        if st.button("💾 Simpan mapping pendidikan"):
            cfg["education_scores"] = edu_edit["Nilai"].astype(float).to_dict()
            st.session_state.notice = "Mapping pendidikan berhasil disimpan."
            st.rerun()

        st.subheader("Mapping Sertifikasi")
        cert = pd.DataFrame({"Nilai": cfg["cert_scores"]})
        cert_edit = st.data_editor(cert, use_container_width=True, key="cert_editor")
        if st.button("💾 Simpan mapping sertifikasi"):
            cfg["cert_scores"] = cert_edit["Nilai"].astype(float).to_dict()
            st.session_state.notice = "Mapping sertifikasi berhasil disimpan."
            st.rerun()
    with tab3:
        c1,c2 = st.columns(2)
        cfg["mdg_threshold"] = c1.number_input("Threshold MDG (tahun)", 0.0, 20.0, float(cfg["mdg_threshold"]), 0.5)
        cfg["min_nk"] = c2.number_input("Minimum NK", 0.0, 4.0, float(cfg["min_nk"]), 0.05)
        st.info("Parameter pada halaman ini adalah konfigurasi prototype. Nilai final perlu dikonfirmasi pemilik proses bisnis.")
        if st.button("🔄 Recalculate seluruh scoring"):
            st.session_state.employees = calc_scores(st.session_state.employees, cfg).drop(
                columns=[c for c in st.session_state.employees.columns if c in []], errors="ignore"
            )
            st.session_state.notice = "Scoring dihitung ulang dengan konfigurasi terbaru."
            st.rerun()
    with tab4:
        st.write("Demo data dapat diedit untuk simulasi.")
        editable_cols = ["NIP","Nama","Satker","Pangkat","Sublevel","Pendidikan","Sertifikasi","Exposure","Potensi","K3",
                         "Status","PTB_S2","Promotion_Award","Satker_Recommendation","Remaining_Service","Readiness"]
        edited = st.data_editor(df[editable_cols], use_container_width=True, num_rows="fixed", key="employee_editor")
        if st.button("💾 Simpan perubahan data demo"):
            base = st.session_state.employees.copy()
            for col in editable_cols:
                base[col] = base[col].astype(st.session_state.employees[col].dtype, errors="ignore")
            for col in editable_cols:
                base[col] = edited[col].values
            st.session_state.employees = base
            st.session_state.notice = "Data demo berhasil diperbarui."
            st.rerun()

def main():
    init_state()
    apply_css()

    # Calculate on every rerun from raw employee data
    raw = st.session_state.employees.copy()
    df = calc_scores(raw, st.session_state.config)

    with st.sidebar:
        st.markdown('<div class="brand">🏦 SIKABI</div>', unsafe_allow_html=True)
        st.markdown('<div class="subtitle">Job Fit Intelligence</div>', unsafe_allow_html=True)
        page = st.radio("Navigasi", ["Dashboard","Data Pegawai & Scoring","Gate Decision","Master Data"], label_visibility="collapsed")
        st.divider()
        st.caption("Periode Penilaian")
        st.selectbox("Periode", ["2026"], index=0)
        st.caption("Prototype untuk demonstrasi alur & scoring.")
        if st.button("↻ Reset Demo Data"):
            st.session_state.employees = make_demo_data()
            st.session_state.notice = "Demo data di-reset."
            st.rerun()

    if st.session_state.notice:
        st.success(st.session_state.notice)
        st.session_state.notice = ""

    if page == "Dashboard":
        dashboard(df)
    elif page == "Data Pegawai & Scoring":
        data_scoring(df, st.session_state.config)
    elif page == "Gate Decision":
        gate_decision(df, st.session_state.config)
    elif page == "Master Data":
        master_data(df, st.session_state.config)

if __name__ == "__main__":
    main()
