
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import io
import plotly.express as px

st.set_page_config(page_title="SIKABI | Job Fit Intelligence", page_icon="🏦", layout="wide")
DATA_FILE = Path(__file__).parent / "sikabi_data.xlsx"

SHEETS = [
    "Employees", "Quant_Weights", "Qual_Weights", "Rank_Weights",
    "Education_Score", "Certification_Score", "Thresholds"
]

@st.cache_data(show_spinner=False)
def read_excel_bytes(data_bytes):
    return pd.read_excel(io.BytesIO(data_bytes), sheet_name=None)

def read_source():
    if not DATA_FILE.exists():
        st.error("File sikabi_data.xlsx tidak ditemukan. Letakkan file tersebut satu folder dengan app.py.")
        st.stop()
    return pd.read_excel(DATA_FILE, sheet_name=None)

def load_data():
    # Upload in sidebar overrides bundled Excel for the current session.
    uploaded = st.session_state.get("uploaded_excel")
    if uploaded:
        return read_excel_bytes(uploaded)
    return read_source()

def write_workbook(sheets):
    # Local/demo persistence: writes back to the Excel source.
    with pd.ExcelWriter(DATA_FILE, engine="openpyxl") as writer:
        for name in SHEETS:
            df = sheets.get(name, pd.DataFrame())
            df.to_excel(writer, sheet_name=name, index=False)
            ws = writer.book[name]
            ws.freeze_panes = "A2"
            for cell in ws[1]:
                cell.font = __import__("openpyxl").styles.Font(bold=True)

def sheets_to_bytes(sheets):
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        for name in SHEETS:
            sheets.get(name, pd.DataFrame()).to_excel(writer, sheet_name=name, index=False)
    return bio.getvalue()

def cfg_from_sheets(s):
    qw = dict(zip(s["Quant_Weights"]["Parameter"], s["Quant_Weights"]["Value"]))
    lw = dict(zip(s["Qual_Weights"]["Parameter"], s["Qual_Weights"]["Value"]))
    rw = {}
    for _, r in s["Rank_Weights"].iterrows():
        rw[str(r["Pangkat"])] = {"Quantitative": float(r["Quantitative"]), "Qualitative": float(r["Qualitative"])}
    edu = dict(zip(s["Education_Score"]["Kategori"], s["Education_Score"]["Nilai"]))
    cert = dict(zip(s["Certification_Score"]["Kategori"], s["Certification_Score"]["Nilai"]))
    th = dict(zip(s["Thresholds"]["Parameter"], s["Thresholds"]["Value"]))
    return {
        "quant_weights": {k: float(v) for k,v in qw.items()},
        "qual_weights": {k: float(v) for k,v in lw.items()},
        "rank_weights": rw,
        "education_scores": {k: float(v) for k,v in edu.items()},
        "cert_scores": {k: float(v) for k,v in cert.items()},
        "mdg_threshold": float(th.get("MDG Threshold (tahun)",2.0)),
        "min_nk": float(th.get("Minimum NK",3.0)),
        "min_remaining_service": float(th.get("Minimum Remaining Service (tahun)",0.5)),
    }

def calc_scores(df, cfg):
    out = df.copy()
    out["Tanggal_Grade"] = pd.to_datetime(out["Tanggal_Grade"], errors="coerce")
    out["NK"] = out[[f"NK_{i}" for i in range(1,6)]].apply(pd.to_numeric, errors="coerce").mean(axis=1)
    period = pd.Timestamp("2026-09-30")
    out["MDP"] = ((period - out["Tanggal_Grade"]).dt.days / 365.25).clip(lower=0)
    out["MDG"] = out["MDP"]

    nk_mean = out.groupby("Pangkat")["NK"].transform("mean")
    nk_std = out.groupby("Pangkat")["NK"].transform("std").fillna(0)
    mdp_mean = out.groupby("Pangkat")["MDP"].transform("mean")
    mdp_std = out.groupby("Pangkat")["MDP"].transform("std").fillna(0)

    out["NK_Score"] = np.select([out["NK"] > nk_mean + nk_std, out["NK"] >= nk_mean - nk_std], [100,60], default=20)
    out["MDP_Score"] = np.select([out["MDP"] > mdp_mean + mdp_std, out["MDP"] >= mdp_mean - mdp_std], [100,60], default=20)
    out["Pendidikan_Score"] = out["Pendidikan"].map(cfg["education_scores"]).fillna(0)
    out["Sertifikasi_Score"] = out["Sertifikasi"].map(cfg["cert_scores"]).fillna(0).clip(upper=100)

    qw = cfg["quant_weights"]
    out["Quantitative"] = (
        out["NK_Score"]*qw["NK"] + out["MDP_Score"]*qw["MDP"] +
        out["Pendidikan_Score"]*qw["Pendidikan"] + out["Sertifikasi_Score"]*qw["Sertifikasi"]
    )
    k3map = {"SB":100,"B":80,"CB":60,"KB":30}
    out["K3_Score"] = out["K3"].map(k3map).fillna(0)
    lw = cfg["qual_weights"]
    out["Qualitative"] = out["Exposure"]*lw["Exposure"] + out["Potensi"]*lw["Potensi"] + out["K3_Score"]*lw["K3"]

    out["Quant_Weight"] = out["Pangkat"].map({k:v["Quantitative"] for k,v in cfg["rank_weights"].items()})
    out["Qual_Weight"] = out["Pangkat"].map({k:v["Qualitative"] for k,v in cfg["rank_weights"].items()})
    out["QScore"] = out["Quantitative"]*out["Quant_Weight"] + out["Qualitative"]*out["Qual_Weight"]

    out["G1_MDG"] = out["MDG"] >= cfg["mdg_threshold"]
    out["G1_Service"] = out["Remaining_Service"] > cfg["min_remaining_service"]
    out["G1_NK"] = out["NK"] >= cfg["min_nk"]
    out["G1_Education"] = out["Pendidikan"].notna()
    out["G1_Recommendation"] = out["Satker_Recommendation"].eq("Direkomendasikan")
    out["G1_Status"] = out["Status"].eq("Aktif")
    out["G1_PTB"] = ~out["PTB_S2"].astype(bool)
    out["G1_Award"] = ~out["Promotion_Award"].astype(bool)
    g1 = ["G1_MDG","G1_Service","G1_NK","G1_Education","G1_Recommendation","G1_Status","G1_PTB","G1_Award"]
    out["Gate_1"] = out[g1].all(axis=1)

    qmean = out.groupby("Pangkat")["Quantitative"].transform("mean")
    lmean = out.groupby("Pangkat")["Qualitative"].transform("mean")
    qsmean = out.groupby("Pangkat")["QScore"].transform("mean")
    out["Passing_Quant"], out["Passing_Qual"], out["Passing_QScore"] = qmean,lmean,qsmean
    out["G2_NK"] = out["NK"] >= cfg["min_nk"]
    out["G2_Quant"] = out["Quantitative"] >= qmean
    out["G2_Qual"] = out["Qualitative"] >= lmean
    out["G2_QScore"] = out["QScore"] >= qsmean
    out["Gate_2"] = out[["G2_NK","G2_Quant","G2_Qual","G2_QScore"]].all(axis=1)

    out["Is_Senior"] = out["Sublevel"].eq("Senior") | out["Pangkat"].eq("S-A")
    out["Gate_3"] = np.where(out["Is_Senior"], True, out["MDG"] >= cfg["mdg_threshold"])
    out["KPP_Eligible"] = out["Gate_1"] & out["Gate_2"] & out["Gate_3"]

    kq = out.groupby("Pangkat")["QScore"].transform("mean")
    km = out.groupby("Pangkat")["MDP"].transform("mean")
    out["KPP_QMean"], out["KPP_Mean_MDP"] = kq, km
    cond = [
        out["KPP_Eligible"]&(out["QScore"]>=kq)&(out["MDP"]>=km),
        out["KPP_Eligible"]&(out["QScore"]>=kq)&(out["MDP"]<km),
        out["KPP_Eligible"]&(out["QScore"]<kq)&(out["MDP"]>=km),
        out["KPP_Eligible"]&(out["QScore"]<kq)&(out["MDP"]<km)]
    out["Quadrant"] = np.select(cond,["I","II","III","IV"],default="-")
    def outcome(r):
        if r["KPP_Eligible"]: return "KPP / Promosi Pipeline"
        if not r["Gate_1"]: return "General Talent — Gate 1"
        if not r["Gate_2"]: return "General Talent — Gate 2"
        return "General Talent — Gate 3"
    out["Outcome"] = out.apply(outcome, axis=1)
    return out

def save_uploaded_to_state(uploaded_file):
    st.session_state.uploaded_excel = uploaded_file.getvalue()
    st.cache_data.clear()
    st.rerun()

def master_crud(sheets):
    st.title("Master Data")
    st.caption("Satu-satunya halaman untuk CRUD. Perubahan parameter/data menjadi sumber perhitungan halaman lain.")

    tabs = st.tabs(["👥 Pegawai","⚖️ Bobot","🎓 Mapping Nilai","🎯 Threshold"])

    with tabs[0]:
        st.subheader("CRUD Data Pegawai")
        df = sheets["Employees"].copy()
        action = st.radio("Operasi", ["Read","Create","Update","Delete"], horizontal=True, key="emp_action")
        if action == "Read":
            st.dataframe(df, use_container_width=True, hide_index=True)
        elif action == "Create":
            with st.form("create_employee"):
                c1,c2,c3 = st.columns(3)
                nip=c1.text_input("NIP *"); nama=c2.text_input("Nama *"); satker=c3.text_input("Satker *")
                unit=c1.text_input("Unit"); pangkat=c2.selectbox("Pangkat",["DD","AD","M","AM","S-A"])
                sub=c3.selectbox("Sublevel",["Reguler","Senior"])
                tanggal=c1.date_input("Tanggal Grade", value=pd.Timestamp("2022-01-01"))
                pendidikan=c2.selectbox("Pendidikan", list(sheets["Education_Score"]["Kategori"]))
                sert=c3.selectbox("Sertifikasi", list(sheets["Certification_Score"]["Kategori"]))
                c1,c2,c3=st.columns(3)
                nk1=c1.number_input("NK 1",2.0,4.0,3.2); nk2=c2.number_input("NK 2",2.0,4.0,3.2); nk3=c3.number_input("NK 3",2.0,4.0,3.2)
                c1,c2,c3=st.columns(3)
                nk4=c1.number_input("NK 4",2.0,4.0,3.2); nk5=c2.number_input("NK 5",2.0,4.0,3.2)
                exposure=c3.number_input("Exposure",0,100,70); potensi=c1.number_input("Potensi",0,100,70); k3=c2.selectbox("K3",["SB","B","CB","KB"])
                status=c3.selectbox("Status",["Aktif","Cuti","Sanksi","CLTB","Pemberhentian Sementara"])
                rec=c1.selectbox("Rekomendasi Satker",["Direkomendasikan","Tidak Direkomendasikan"])
                remain=c2.number_input("Sisa Masa Dinas (tahun)",0.0,20.0,3.0,0.1)
                ptb=c3.checkbox("PTB S2"); award=c1.checkbox("Promotion Award")
                readiness=c2.selectbox("Readiness",["Ready Now","Ready 1-2 Tahun","Belum Siap"])
                submit=st.form_submit_button("➕ Tambah Pegawai")
            if submit:
                if not nip or not nama or not satker: st.error("NIP, Nama, dan Satker wajib diisi.")
                elif nip in df["NIP"].astype(str).values: st.error("NIP sudah ada.")
                else:
                    new = {"NIP":nip,"Nama":nama,"Unit":unit,"Satker":satker,"Pangkat":pangkat,"Sublevel":sub,
                           "Tanggal_Grade":pd.Timestamp(tanggal),"NK_1":nk1,"NK_2":nk2,"NK_3":nk3,"NK_4":nk4,"NK_5":nk5,
                           "Pendidikan":pendidikan,"Sertifikasi":sert,"Exposure":exposure,"Potensi":potensi,"K3":k3,
                           "Status":status,"PTB_S2":ptb,"Promotion_Award":award,"Satker_Recommendation":rec,
                           "Remaining_Service":remain,"Readiness":readiness}
                    sheets["Employees"]=pd.concat([df,pd.DataFrame([new])],ignore_index=True)
                    write_workbook(sheets)
                    st.success("Pegawai berhasil ditambahkan.")
                    st.rerun()
        elif action == "Update":
            nip=st.selectbox("Pilih NIP", df["NIP"].astype(str).tolist())
            row=df[df["NIP"].astype(str)==nip].iloc[0]
            editable=["Nama","Unit","Satker","Pangkat","Sublevel","Pendidikan","Sertifikasi","Exposure","Potensi","K3","Status","Satker_Recommendation","Remaining_Service","Readiness"]
            with st.form("update_employee"):
                vals={}
                for col in editable:
                    default=row[col]
                    if col in ["Pendidikan"]: vals[col]=st.selectbox(col,list(sheets["Education_Score"]["Kategori"]),index=list(sheets["Education_Score"]["Kategori"]).index(default) if default in list(sheets["Education_Score"]["Kategori"]) else 0)
                    elif col=="Sertifikasi": vals[col]=st.selectbox(col,list(sheets["Certification_Score"]["Kategori"]),index=list(sheets["Certification_Score"]["Kategori"]).index(default) if default in list(sheets["Certification_Score"]["Kategori"]) else 0)
                    elif col=="Pangkat": vals[col]=st.selectbox(col,["DD","AD","M","AM","S-A"],index=["DD","AD","M","AM","S-A"].index(default))
                    elif col=="Sublevel": vals[col]=st.selectbox(col,["Reguler","Senior"],index=["Reguler","Senior"].index(default))
                    elif col=="K3": vals[col]=st.selectbox(col,["SB","B","CB","KB"],index=["SB","B","CB","KB"].index(default))
                    elif col=="Status": vals[col]=st.selectbox(col,["Aktif","Cuti","Sanksi","CLTB","Pemberhentian Sementara"],index=["Aktif","Cuti","Sanksi","CLTB","Pemberhentian Sementara"].index(default))
                    elif col=="Satker_Recommendation": vals[col]=st.selectbox(col,["Direkomendasikan","Tidak Direkomendasikan"],index=0 if default=="Direkomendasikan" else 1)
                    elif col=="Readiness": vals[col]=st.selectbox(col,["Ready Now","Ready 1-2 Tahun","Belum Siap"],index=["Ready Now","Ready 1-2 Tahun","Belum Siap"].index(default))
                    elif col in ["Exposure","Potensi"]: vals[col]=st.number_input(col,0,100,int(default))
                    elif col=="Remaining_Service": vals[col]=st.number_input(col,0.0,20.0,float(default),0.1)
                    else: vals[col]=st.text_input(col,str(default))
                if st.form_submit_button("💾 Simpan Update"):
                    idx=df.index[df["NIP"].astype(str)==nip][0]
                    for col,v in vals.items(): df.loc[idx,col]=v
                    sheets["Employees"]=df
                    write_workbook(sheets)
                    st.success("Data pegawai berhasil diperbarui.")
                    st.rerun()
        else:
            nip=st.selectbox("Pilih NIP yang akan dihapus", df["NIP"].astype(str).tolist())
            st.warning("Delete akan menghapus record pegawai dari Excel.")
            if st.button("🗑️ Hapus Pegawai", type="primary"):
                sheets["Employees"]=df[df["NIP"].astype(str)!=nip].reset_index(drop=True)
                write_workbook(sheets)
                st.success("Pegawai berhasil dihapus.")
                st.rerun()

    with tabs[1]:
        st.subheader("CRUD Bobot")
        st.info("Edit tabel lalu klik Save. Total bobot idealnya 100%.")
        q = st.data_editor(sheets["Quant_Weights"], use_container_width=True, num_rows="dynamic", key="qedit")
        l = st.data_editor(sheets["Qual_Weights"], use_container_width=True, num_rows="dynamic", key="ledit")
        r = st.data_editor(sheets["Rank_Weights"], use_container_width=True, num_rows="dynamic", key="redit")
        if st.button("💾 Simpan semua bobot"):
            sheets["Quant_Weights"]=q; sheets["Qual_Weights"]=l; sheets["Rank_Weights"]=r
            write_workbook(sheets); st.success("Bobot berhasil disimpan."); st.rerun()

    with tabs[2]:
        st.subheader("CRUD Mapping Nilai")
        e=st.data_editor(sheets["Education_Score"],use_container_width=True,num_rows="dynamic",key="eedit")
        c=st.data_editor(sheets["Certification_Score"],use_container_width=True,num_rows="dynamic",key="cedit")
        if st.button("💾 Simpan mapping"):
            sheets["Education_Score"]=e; sheets["Certification_Score"]=c
            write_workbook(sheets); st.success("Mapping berhasil disimpan."); st.rerun()

    with tabs[3]:
        st.subheader("CRUD Threshold")
        t=st.data_editor(sheets["Thresholds"],use_container_width=True,num_rows="fixed",key="tedit")
        if st.button("💾 Simpan threshold"):
            sheets["Thresholds"]=t; write_workbook(sheets); st.success("Threshold berhasil disimpan."); st.rerun()

        st.divider()
        st.subheader("Import / Export Excel")
        st.download_button("⬇️ Download Excel terbaru", data=sheets_to_bytes(sheets),
                           file_name="sikabi_data_updated.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        upload=st.file_uploader("Upload Excel untuk menjadi sumber data sesi ini", type=["xlsx"])
        if upload and st.button("📥 Gunakan Excel ini"):
            save_uploaded_to_state(upload)

def dashboard(df):
    st.title("Dashboard")
    st.caption("Seluruh informasi dashboard ditarik dari data Excel + hasil perhitungan scoring.")
    c=st.columns(5)
    c[0].metric("Total Pegawai",len(df)); c[1].metric("Gate 1 PASS",int(df.Gate_1.sum()))
    c[2].metric("Gate 2 PASS",int((df.Gate_1&df.Gate_2).sum()))
    c[3].metric("Masuk KPP",int(df.KPP_Eligible.sum())); c[4].metric("General Talent",int((~df.KPP_Eligible).sum()))
    st.divider()
    q=df[df.KPP_Eligible]
    left,right=st.columns([1.6,1])
    with left:
        st.subheader("Quadrant")
        if len(q):
            fig=px.scatter(q,x="MDP",y="QScore",color="Quadrant",text="Nama",hover_data=["NIP","Pangkat","Satker","Readiness"],height=480)
            fig.update_traces(textposition="top center"); st.plotly_chart(fig,use_container_width=True)
        else: st.info("Belum ada pegawai masuk KPP.")
    with right:
        st.subheader("Outcome")
        oc=df["Outcome"].value_counts().reset_index(); oc.columns=["Outcome","Jumlah"]
        st.plotly_chart(px.bar(oc,x="Jumlah",y="Outcome",orientation="h",height=330),use_container_width=True)
        st.subheader("Quadrant Recap")
        st.dataframe(q["Quadrant"].value_counts().reindex(["I","II","III","IV"],fill_value=0).rename("Jumlah"),use_container_width=True)

def scoring(df,cfg):
    st.title("Data Pegawai & Scoring")
    filters=st.columns(3)
    sat=filters[0].multiselect("Satker",sorted(df.Satker.unique()),default=sorted(df.Satker.unique()))
    rank=filters[1].multiselect("Pangkat",sorted(df.Pangkat.unique()),default=sorted(df.Pangkat.unique()))
    outcome=filters[2].selectbox("Outcome",["Semua"]+sorted(df.Outcome.unique()))
    v=df[df.Satker.isin(sat)&df.Pangkat.isin(rank)].copy()
    if outcome!="Semua": v=v[v.Outcome==outcome]
    cols=["NIP","Nama","Satker","Pangkat","Sublevel","NK","MDP","Pendidikan","Sertifikasi","Quantitative","Qualitative","QScore","Gate_1","Gate_2","Gate_3","KPP_Eligible","Quadrant","Outcome"]
    st.dataframe(v[cols].round(2),use_container_width=True,hide_index=True)
    st.download_button("⬇️ Export CSV",v[cols].to_csv(index=False).encode(), "sikabi_scoring.csv","text/csv")
    if len(v):
        nip=st.selectbox("Detail pegawai",v.NIP.tolist(),format_func=lambda x:f"{x} — {v.loc[v.NIP==x,'Nama'].iloc[0]}")
        r=v[v.NIP==nip].iloc[0]
        a,b,c=st.columns(3); a.metric("QScore",f"{r.QScore:.2f}"); b.metric("Quantitative",f"{r.Quantitative:.2f}"); c.metric("Qualitative",f"{r.Qualitative:.2f}")
        t1,t2,t3=st.tabs(["Score Breakdown","Gate Detail","Outcome"])
        with t1:
            bd=pd.DataFrame({"Komponen":["NK","MDP","Pendidikan","Sertifikasi","Exposure","Potensi","K3"],
                "Nilai":[r.NK_Score,r.MDP_Score,r.Pendidikan_Score,r.Sertifikasi_Score,r.Exposure,r.Potensi,r.K3_Score],
                "Bobot":[cfg["quant_weights"]["NK"],cfg["quant_weights"]["MDP"],cfg["quant_weights"]["Pendidikan"],cfg["quant_weights"]["Sertifikasi"],cfg["qual_weights"]["Exposure"],cfg["qual_weights"]["Potensi"],cfg["qual_weights"]["K3"]]})
            bd["Kontribusi"]=bd["Nilai"]*bd["Bobot"]; st.dataframe(bd.round(2),use_container_width=True,hide_index=True)
            st.info(f"QScore = {r.Quantitative:.2f} × {r.Quant_Weight:.0%} + {r.Qualitative:.2f} × {r.Qual_Weight:.0%} = {r.QScore:.2f}")
        with t2:
            g1=[("MDG",r.G1_MDG,f"{r.MDG:.2f}"),("Sisa masa dinas",r.G1_Service,f"{r.Remaining_Service:.1f} thn"),("NK",r.G1_NK,f"{r.NK:.2f}"),("Pendidikan",r.G1_Education,r.Pendidikan),("Rekomendasi",r.G1_Recommendation,r.Satker_Recommendation),("Status",r.G1_Status,r.Status),("PTB S2",r.G1_PTB,str(not r.PTB_S2)),("Promotion Award",r.G1_Award,str(not r.Promotion_Award))]
            st.dataframe(pd.DataFrame(g1,columns=["Kriteria","Pass","Evidence"]),use_container_width=True,hide_index=True)
            g2=[("NK ≥ minimum",r.G2_NK,f"{r.NK:.2f}"),("Quant ≥ mean",r.G2_Quant,f"{r.Quantitative:.2f} vs {r.Passing_Quant:.2f}"),("Qual ≥ mean",r.G2_Qual,f"{r.Qualitative:.2f} vs {r.Passing_Qual:.2f}"),("QScore ≥ mean",r.G2_QScore,f"{r.QScore:.2f} vs {r.Passing_QScore:.2f}"),("MDG / Senior",r.Gate_3,"Senior" if r.Is_Senior else f"{r.MDG:.2f} thn")]
            st.dataframe(pd.DataFrame(g2,columns=["Kriteria","Pass","Evidence"]),use_container_width=True,hide_index=True)
        with t3:
            st.write("**Readiness:**",r.Readiness); st.write("**Quadrant:**",r.Quadrant); st.write("**Outcome:**",r.Outcome)

def gates(df):
    st.title("Gate Decision")
    a,b,c=st.tabs(["Gate 1","Gate 2","Gate 3 / MDG"])
    with a: st.dataframe(df[["NIP","Nama","Satker","Pangkat","Gate_1","G1_MDG","G1_Service","G1_NK","G1_Education","G1_Recommendation","G1_Status","G1_PTB","G1_Award"]],use_container_width=True,hide_index=True)
    with b: st.dataframe(df[["NIP","Nama","Pangkat","NK","Quantitative","Passing_Quant","Qualitative","Passing_Qual","QScore","Passing_QScore","Gate_2"]].round(2),use_container_width=True,hide_index=True)
    with c: st.dataframe(df[["NIP","Nama","Pangkat","Sublevel","Is_Senior","MDG","Gate_3","KPP_Eligible","Outcome"]].round(2),use_container_width=True,hide_index=True)
    st.info("Gate 2 menggunakan asumsi AND sesuai draft requirement. Rule yang belum final tetap perlu konfirmasi bisnis.")

def main():
    st.markdown("""
    <style>
    .block-container{padding-top:1.2rem}
    .brand{font-size:1.35rem;font-weight:750}
    </style>
    """,unsafe_allow_html=True)
    sheets=load_data()
    cfg=cfg_from_sheets(sheets)
    df=calc_scores(sheets["Employees"],cfg)

    with st.sidebar:
        st.markdown('<div class="brand">🏦 SIKABI</div>',unsafe_allow_html=True)
        st.caption("Job Fit Intelligence")
        page=st.radio("Navigasi",["Dashboard","Data Pegawai & Scoring","Gate Decision","Master Data"])
        st.divider()
        st.caption("Sumber data")
        st.code("sikabi_data.xlsx",language="text")
        if st.session_state.get("uploaded_excel"):
            st.success("Excel upload aktif untuk sesi ini.")
        st.caption("CRUD hanya pada Master Data. Halaman lain bersifat read/calculation.")
    if page=="Dashboard": dashboard(df)
    elif page=="Data Pegawai & Scoring": scoring(df,cfg)
    elif page=="Gate Decision": gates(df)
    else: master_crud(sheets)

if __name__=="__main__":
    main()
