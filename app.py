"""
SIKABI — Sistem Intelijen Karier Bank Indonesia
Transformasi Digital Manajemen Karier Pegawai Bank Indonesia

Jalankan lokal:
    streamlit run app.py
"""

import io
import os
import base64

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from PIL import Image

from scoring import (
    ADMIN_CHECK_LABELS,
    KPP_CHECK_LABELS,
    KUADRAN_DESC,
    READINESS_COLOR,
    READINESS_ORDER,
    compute_all,
)

BASE_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE_DIR, "data", "sikabi_data.xlsx")
SIDEBAR_LOGO_PATH = os.path.join(BASE_DIR, "assets", "Sikabi.png")
HERO_LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo header.png")
HERO_BG_PATH = os.path.join(BASE_DIR, "assets", "background.png")

REF_SHEETS = [
    "Quant_Weights", "Qual_Weights", "Rank_Weights",
    "Education_Score", "Certification_Score", "K3_Score", "Potensi_Score", "Thresholds",
]

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
INK = "#1B2733"
INK_SOFT = "#63707C"
LINE = "#E6E8EA"
SURFACE = "#FFFFFF"
CANVAS = "#F5F6F4"
BRAND = "#1E3A52"
BRAND_DEEP = "#E6F0F3"
BRAND_DEEP_TEXT = "#173449"
TEAL = "#2F7A6F"
AMBER = "#B9821F"
RED = "#B0574A"

KUADRAN_COLOR = {"I": "#2F7A6F", "II": "#6E9750", "III": "#B9821F", "IV": "#B0574A"}
KUADRAN_BG = {"I": "#EEF7F5", "II": "#F1F6EC", "III": "#FBF5E9", "IV": "#FAEFEC"}

logo_img = Image.open(SIDEBAR_LOGO_PATH) if os.path.exists(SIDEBAR_LOGO_PATH) else None

st.set_page_config(
    page_title="SIKABI",
    page_icon=logo_img if logo_img else "🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Global styling
# ---------------------------------------------------------------------------
st.markdown(
    f"""
    <style>
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header[data-testid="stHeader"] {{background: transparent;}}

    .stApp {{ background: {CANVAS}; }}
    html, body, [class*="css"] {{ font-family: -apple-system, "Segoe UI", Roboto, sans-serif; }}

    h1, h2, h3, h4 {{ color: {INK}; font-weight: 600; }}
    p, span, label, div {{ color: {INK}; }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background: {BRAND_DEEP};
        border-right: none;
    }}
    section[data-testid="stSidebar"] * {{ color: {BRAND_DEEP_TEXT} !important; }}
    section[data-testid="stSidebar"] hr {{ border-color: rgba(15,33,48,0.14); }}

    /* Buttons */
    .stButton > button, .stDownloadButton > button {{
        border-radius: 8px;
        border: 1px solid {LINE};
        background: {SURFACE};
        color: {INK};
        font-weight: 500;
        padding: 0.45rem 1rem;
    }}
    .stButton > button:hover, .stDownloadButton > button:hover {{
        border-color: {TEAL};
        color: {TEAL};
    }}
    section[data-testid="stSidebar"] .stButton > button,
    section[data-testid="stSidebar"] .stDownloadButton > button {{
        background: rgba(255,255,255,0.55) !important;
        border: 1px solid rgba(15,33,48,0.16) !important;
        color: #173449 !important;
        width: 100%;
        text-align: left;
        justify-content: flex-start;
    }}
    section[data-testid="stSidebar"] .stButton > button:hover,
    section[data-testid="stSidebar"] .stDownloadButton > button:hover {{
        background: rgba(255,255,255,0.85) !important;
        border-color: rgba(15,33,48,0.28) !important;
        color: #173449 !important;
    }}
    section[data-testid="stSidebar"] .stButton > button:disabled {{
        opacity: 0.45 !important;
        color: #FFFFFF !important;
    }}
    section[data-testid="stSidebar"] button[kind="primary"],
    section[data-testid="stSidebar"] button[kind="primary"]:hover {{
        background: {TEAL} !important;
        border: 1px solid {TEAL} !important;
        color: #FFFFFF !important;
        font-weight: 600;
    }}

    /* Primary-styled buttons (kind=primary) */
    button[kind="primary"] {{
        background: {TEAL} !important;
        border-color: {TEAL} !important;
        color: #FFFFFF !important;
    }}

    /* Multiselect / select tags: replace default red accent with brand teal */
    span[data-baseweb="tag"] {{
        background-color: {TEAL} !important;
        color: #FFFFFF !important;
        border-radius: 6px !important;
    }}
    span[data-baseweb="tag"] svg {{ fill: #FFFFFF !important; }}
    ul[data-baseweb="menu"] li:hover {{ background-color: rgba(47,122,111,0.12) !important; }}
    div[data-baseweb="select"] > div {{
        border-radius: 8px !important;
        border-color: {LINE} !important;
    }}
    div[data-baseweb="select"]:hover > div {{ border-color: {TEAL} !important; }}

    /* Tabs */
    button[data-baseweb="tab"] {{ font-weight: 500; color: {INK_SOFT}; }}
    button[data-baseweb="tab"][aria-selected="true"] {{ color: {BRAND}; }}
    div[data-baseweb="tab-highlight"] {{ background-color: {TEAL} !important; }}

    /* Dataframe container */
    div[data-testid="stDataFrame"] {{
        border: 1px solid {LINE};
        border-radius: 10px;
        overflow: hidden;
    }}

    /* Custom card */
    .sikabi-card {{
        background: {SURFACE};
        border: 1px solid {LINE};
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 1px 2px rgba(16,24,32,0.04);
    }}
    .sikabi-metric-label {{
        color: {INK_SOFT}; font-size: 12.5px; font-weight: 500;
        text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 6px;
    }}
    .sikabi-metric-value {{ font-size: 30px; font-weight: 700; line-height: 1.1; color: {INK}; }}
    .sikabi-metric-sub {{ color: {INK_SOFT}; font-size: 12.5px; margin-top: 6px; }}

    .sikabi-quad-row {{
        display: flex; justify-content: space-between; align-items: center;
        padding: 12px 14px; border: 1px solid {LINE}; border-radius: 10px;
        margin-bottom: 8px; background: {SURFACE};
        transition: border-color 0.15s ease, background 0.15s ease;
    }}
    .sikabi-quad-row.quad-I {{ background: #EEF7F5; border-color: #B7D9D3; }}
    .sikabi-quad-row.quad-II {{ background: #F1F6EC; border-color: #C9DDBB; }}
    .sikabi-quad-row.quad-III {{ background: #FBF5E9; border-color: #E5C98E; }}
    .sikabi-quad-row.quad-IV {{ background: #FAEFEC; border-color: #DFB8AF; }}
    .sikabi-dot {{ display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:8px; }}

    /* Rajawali-inspired dashboard hero */
    /* Use the available main canvas more fully */
    .block-container {{
        max-width: 100% !important;
        padding-left: 1.25rem !important;
        padding-right: 1.25rem !important;
        padding-top: 0 !important;
    }}
    .sikabi-hero {{
        width: calc(100% + 2.5rem);
        min-height: 385px;
        margin: -2.2rem -1.25rem 1.25rem -1.25rem;
        background-size: cover;
        background-position: center 45%;
        border-radius: 0 0 14px 14px;
        overflow: hidden;
        box-shadow: 0 8px 24px rgba(15,33,48,0.14);
        color: #FFFFFF !important;
    }}
    .sikabi-hero-inner {{
        padding: 34px 40px 30px 40px;
    }}
    .sikabi-brand-row {{
        display: flex;
        align-items: center;
        gap: 4px;
        max-width: 1180px;
    }}
    .sikabi-hero-logo {{
        flex: 0 0 185px;
        min-width: 0;
        display: flex;
        align-items: center;
        justify-content: flex-start;
        filter: drop-shadow(0 2px 4px rgba(0,0,0,0.28));
    }}
    .sikabi-hero-title {{
        font-size: 3.15rem;
        line-height: 1.05;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: #FFFFFF !important;
        text-shadow: 1px 2px 5px rgba(0,0,0,0.42);
    }}
    .sikabi-hero-subtitle {{
        margin-top: 5px;
        font-size: 1.35rem;
        font-weight: 700;
        color: #D8F0EC !important;
        text-shadow: 1px 1px 4px rgba(0,0,0,0.4);
    }}
    .sikabi-hero-description {{
        margin-top: 10px;
        max-width: 900px;
        font-size: 1rem;
        line-height: 1.55;
        color: rgba(255,255,255,0.92) !important;
        text-shadow: 1px 1px 4px rgba(0,0,0,0.55);
    }}
    .sikabi-hero-panel {{
        margin-top: 24px;
        padding: 20px 24px 18px 24px;
        border-radius: 14px;
        background: rgba(8,18,25,0.58);
        border: 1px solid rgba(255,255,255,0.17);
        box-shadow: 0 10px 25px rgba(0,0,0,0.18);
        backdrop-filter: blur(9px);
    }}
    .sikabi-hero-panel-title {{
        font-size: 1.35rem;
        font-weight: 750;
        color: #FFFFFF !important;
        margin-bottom: 20px;
    }}
    .sikabi-hero-metrics {{
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 26px;
    }}
    .hero-label {{
        font-size: 0.82rem;
        color: rgba(255,255,255,0.72) !important;
        margin-bottom: 5px;
    }}
    .hero-value {{
        font-size: 1.75rem;
        line-height: 1.05;
        font-weight: 800;
        color: #FFFFFF !important;
    }}
    .hero-teal {{ color: #6FC5B8 !important; }}
    .hero-red {{ color: #E78C7E !important; }}
    .hero-sub {{
        margin-top: 5px;
        font-size: 0.78rem;
        color: rgba(255,255,255,0.62) !important;
    }}
    @media (max-width: 900px) {{
        .block-container {{
            padding-left: 0.75rem !important;
            padding-right: 0.75rem !important;
        }}
        .sikabi-hero {{
            width: calc(100% + 1.5rem);
            margin-left: -0.75rem;
            margin-right: -0.75rem;
        }}
        .sikabi-hero-inner {{ padding: 28px 24px 24px 24px; }}
        .sikabi-brand-row {{ align-items: flex-start; }}
        .sikabi-hero-title {{ font-size: 2.4rem; }}
        .sikabi-hero-subtitle {{ font-size: 1.05rem; }}
        .sikabi-hero-metrics {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


def _img_b64(path, crop_transparent=False):
    if not os.path.exists(path):
        return None
    if crop_transparent:
        try:
            img = Image.open(path).convert("RGBA")
            alpha = img.getchannel("A")
            bbox = alpha.getbbox()
            if bbox:
                img = img.crop(bbox)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception:
            pass
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


LOGO_B64 = _img_b64(HERO_LOGO_PATH, crop_transparent=True)
HERO_BG_B64 = _img_b64(HERO_BG_PATH)


def page_header(title):
    """Render a clean page title without a duplicate logo above it."""
    st.markdown(f"## {title}")


def dashboard_hero(df):
    """Rajawali-inspired hero banner using the local SIKABI background asset."""
    total = len(df)
    admin = int(df["Lolos_Administrasi"].sum())
    kpp = int(df["Lolos_KPP"].sum())
    gt = int((df["Status_Akhir"] == "General Talent").sum())

    bg = f"data:image/png;base64,{HERO_BG_B64}" if HERO_BG_B64 else ""
    logo = f"data:image/png;base64,{LOGO_B64}" if LOGO_B64 else ""

    logo_html = (
        f'<img src="{logo}" style="width:280px; max-width:none; max-height:145px; transform:translateX(-2px); object-fit:contain; object-position:left center;">'
        if logo else ""
    )

    hero_html = f"""
    <div class="sikabi-hero" style="background-image:linear-gradient(90deg, rgba(7,24,36,0.82) 0%, rgba(7,24,36,0.66) 45%, rgba(7,24,36,0.58) 100%), url('{bg}');">
        <div class="sikabi-hero-inner">
            <div class="sikabi-brand-row">
                <div class="sikabi-hero-logo">{logo_html}</div>
                <div>
                    <div class="sikabi-hero-title">SIKABI</div>
                    <div class="sikabi-hero-subtitle">Sistem Intelijen Karier Bank Indonesia</div>
                    <div class="sikabi-hero-description">Dashboard intelijen karier untuk mendukung analisis potensi, kesiapan promosi, dan prioritisasi kandidat KPP secara terintegrasi.</div>
                </div>
            </div>

            <div class="sikabi-hero-panel">
                <div class="sikabi-hero-panel-title">Dashboard Kuadran &amp; Laporan</div>
                <div class="sikabi-hero-metrics">
                    <div><div class="hero-label">Total Populasi</div><div class="hero-value">{total:,}</div><div class="hero-sub">Periode 2026 semester II</div></div>
                    <div><div class="hero-label">Lolos Administrasi</div><div class="hero-value">{admin:,}</div><div class="hero-sub">{df['Lolos_Administrasi'].mean()*100:.0f}% dari populasi</div></div>
                    <div><div class="hero-label">Lolos Kriteria KPP</div><div class="hero-value hero-teal">{kpp:,}</div><div class="hero-sub">Kandidat lolos kriteria</div></div>
                    <div><div class="hero-label">General Talent</div><div class="hero-value hero-red">{gt:,}</div><div class="hero-sub">Talent pool</div></div>
                </div>
            </div>
        </div>
    </div>
    """
    # st.html renders the hero as real HTML instead of allowing Markdown to escape
    # nested divs (which caused the panel markup to appear as literal text).
    if hasattr(st, "html"):
        st.html(hero_html)
    else:
        st.markdown(hero_html, unsafe_allow_html=True)


def metric_card(label, value, sub=None, accent=None):
    color = accent or INK
    sub_html = f'<div class="sikabi-metric-sub">{sub}</div>' if sub else ""
    st.markdown(
        f"""
        <div class="sikabi-card">
            <div class="sikabi-metric-label">{label}</div>
            <div class="sikabi-metric-value" style="color:{color}">{value}</div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# State & data loading
# ---------------------------------------------------------------------------
def load_workbook(path):
    return pd.read_excel(path, sheet_name=None)


def init_state():
    if "data_loaded" not in st.session_state:
        sheets = load_workbook(DATA_PATH)
        st.session_state.employees = sheets["Employees"]
        for name in REF_SHEETS:
            st.session_state[f"ref_{name}"] = sheets[name]
        st.session_state.data_loaded = True


def get_refs():
    return {name: st.session_state[f"ref_{name}"] for name in REF_SHEETS}


def recompute():
    return compute_all(st.session_state.employees, get_refs())


def save_to_disk():
    with pd.ExcelWriter(DATA_PATH, engine="openpyxl") as writer:
        st.session_state.employees.to_excel(writer, sheet_name="Employees", index=False)
        for name in REF_SHEETS:
            st.session_state[f"ref_{name}"].to_excel(writer, sheet_name=name, index=False)


def workbook_bytes():
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        st.session_state.employees.to_excel(writer, sheet_name="Employees", index=False)
        for name in REF_SHEETS:
            st.session_state[f"ref_{name}"].to_excel(writer, sheet_name=name, index=False)
    return buf.getvalue()


def df_to_xlsx_bytes(dframe):
    buf = io.BytesIO()
    dframe.to_excel(buf, index=False)
    return buf.getvalue()


def format_boolean_table(dframe):
    """Make boolean/check columns visually clearer in Streamlit tables."""
    styled = dframe.copy()
    bool_cols = styled.select_dtypes(include=["bool"]).columns.tolist()

    # Replace Streamlit's default grey checkbox renderer with readable symbols.
    for col in bool_cols:
        styled[col] = styled[col].map({True: "✓", False: "—"})

    if bool_cols:
        def _style_boolean(value):
            if value == "✓":
                return "color: #2F7A6F; font-weight: 700; font-size: 16px; text-align: center;"
            if value == "—":
                return "color: #9AA5AD; font-weight: 600; font-size: 15px; text-align: center;"
            return ""

        styled = styled.style.map(_style_boolean, subset=bool_cols)

    return styled


init_state()
df = recompute()

PANGKAT_OPTS = sorted(df["Pangkat"].dropna().unique().tolist())
SATKER_OPTS = sorted(df["Satker"].dropna().unique().tolist())
STATUS_OPTS = ["Proses KPP", "Ready Promosi Grade", "Belum Siap Promosi Grade", "General Talent"]


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
with st.sidebar:
    if logo_img:
        st.image(logo_img, use_container_width=True)
    else:
        st.markdown("### 🏦 SIKABI")

    st.markdown(
        "<div style='text-align:center;font-size:12px;color:rgba(255,255,255,0.55);"
        "margin-top:-6px;margin-bottom:14px;'>DSDM · Bank Indonesia</div>",
        unsafe_allow_html=True,
    )

    NAV_ITEMS = [
        ("Dashboard", "dashboard"),
        ("Data Pegawai", "group"),
        ("Penentuan Kandidat KPP", "verified_user"),
        ("Pengaturan", "database"),
    ]

    if "nav_page" not in st.session_state:
        st.session_state.nav_page = "Dashboard"

    for label, icon_name in NAV_ITEMS:
        is_active = st.session_state.nav_page == label
        if st.button(
            label,
            icon=f":material/{icon_name}:",
            key=f"nav_{label}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state.nav_page = label
            st.rerun()

    page = st.session_state.nav_page

    st.divider()
    st.caption(f"Total pegawai ·  **{len(df):,}**".replace(",", "."))
    st.caption(f"Lolos administrasi ·  **{int(df['Lolos_Administrasi'].sum()):,}**".replace(",", "."))
    st.caption(f"Proses KPP ·  **{int(df['Masuk_Proses_KPP'].sum()):,}**".replace(",", "."))
    st.divider()

    st.download_button(
        "Unduh data (.xlsx)",
        icon=":material/download:",
        data=workbook_bytes(),
        file_name="sikabi_data.xlsx",
        use_container_width=True,
    )
    st.button(
        "Sinkronisasi data dengan HRIS & KATALIS",
        icon=":material/sync:",
        use_container_width=True,
        disabled=True,
        help="Integrasi belum tersedia — memerlukan koneksi API HRIS dan KATALIS BI.",
    )


# ---------------------------------------------------------------------------
# Page: Dashboard
# ---------------------------------------------------------------------------
def page_dashboard(df):
    dashboard_hero(df)

    st.write("")
    with st.container(border=True):
        fcol1, fcol2, fcol3 = st.columns([1, 1, 1.4])
        f_pangkat = fcol1.multiselect("Pangkat", PANGKAT_OPTS, default=PANGKAT_OPTS)
        f_satker = fcol2.multiselect("Satuan kerja", SATKER_OPTS, default=SATKER_OPTS)
        f_kuadran = fcol3.multiselect("Kuadran", ["I", "II", "III", "IV"], default=["I", "II", "III", "IV"])

    kpp_pop = df[df["Masuk_Proses_KPP"]]
    scoped = kpp_pop[kpp_pop["Pangkat"].isin(f_pangkat) & kpp_pop["Satker"].isin(f_satker)]
    visible = scoped[scoped["Kuadran"].isin(f_kuadran)]

    st.write("")
    left, right = st.columns([3, 2])

    with left:
        with st.container(border=True):
            st.markdown(f"**Peta Kuadran** &nbsp;·&nbsp; {len(visible)} dari {len(kpp_pop)} pegawai Proses KPP")
            # st.caption(
            #     "Hanya pegawai **Grade Senior** yang lolos Kriteria KPP yang masuk di sini "
            #     "(Grade Reguler mengikuti jalur Promosi Grade tersendiri, lihat tab Penentuan Kandidat KPP). "
            #     "Sumbu = selisih QScore dan Masa Dinas Pangkat (MDP = MDG + MDGS) terhadap **rata-rata "
            #     "pangkatnya masing-masing** — bukan rata-rata gabungan semua pangkat. Titik di kanan-atas "
            #     "dari garis 0,0 = Kuadran I, dan seterusnya searah jarum jam."
            # )
            if len(visible) > 0:
                fig = go.Figure()
                for k in ["I", "II", "III", "IV"]:
                    sub = visible[visible["Kuadran"] == k]
                    fig.add_trace(go.Scatter(
                        x=sub["Delta_MDP"], y=sub["Delta_QScore"],
                        mode="markers", name=f"Kuadran {k}",
                        marker=dict(color=KUADRAN_COLOR[k], size=8, opacity=0.8),
                        customdata=sub[["Nama", "Satker", "Pangkat", "Sublevel"]],
                        hovertemplate=(
                            "<b>%{customdata[0]}</b><br>%{customdata[2]} (%{customdata[3]}) · %{customdata[1]}"
                            "<br>Δ QScore: %{y:.1f} · Δ MDP: %{x:.2f} th<extra></extra>"
                        ),
                    ))
                fig.add_hline(y=0, line_dash="dash", line_color="#BFC5CA")
                fig.add_vline(x=0, line_dash="dash", line_color="#BFC5CA")
                fig.update_layout(
                    height=330, margin=dict(l=10, r=10, t=10, b=10),
                    plot_bgcolor=SURFACE, paper_bgcolor=SURFACE,
                    xaxis_title="Δ MDP vs mean pangkat (tahun)",
                    yaxis_title="Δ QScore vs mean pangkat",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
                    font=dict(color=INK, size=12),
                )
                fig.update_xaxes(gridcolor=LINE, zeroline=False)
                fig.update_yaxes(gridcolor=LINE, zeroline=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Tidak ada data pada kombinasi filter ini.")

        st.write("")
        with st.container(border=True):
            st.markdown("**Distribusi Readiness Promosi**")
            scoped_admin = df[df["Pangkat"].isin(f_pangkat) & df["Satker"].isin(f_satker)]
            counts = scoped_admin["Readiness"].value_counts().reindex(READINESS_ORDER).fillna(0)
            fig2 = go.Figure(go.Bar(
                x=counts.index, y=counts.values,
                marker_color=[READINESS_COLOR[r] for r in counts.index],
                text=counts.values.astype(int), textposition="outside",
            ))
            fig2.update_layout(
                height=190, margin=dict(l=8, r=8, t=6, b=8),
                plot_bgcolor=SURFACE, paper_bgcolor=SURFACE,
                yaxis_title="Jumlah", font=dict(color=INK, size=11),
                showlegend=False,
            )
            fig2.update_xaxes(gridcolor=LINE)
            fig2.update_yaxes(gridcolor=LINE)
            st.plotly_chart(fig2, use_container_width=True)

    with right:
        with st.container(border=True):
            st.markdown("**Ringkasan per kuadran**")
            for k in ["I", "II", "III", "IV"]:
                members = scoped[scoped["Kuadran"] == k]
                count = len(members)
                dim = "" if k in f_kuadran else "opacity:0.4;"
                st.markdown(
                    f"<div class='sikabi-quad-row quad-{k}' style='{dim}'>"
                    f"<div><span class='sikabi-dot' style='background:{KUADRAN_COLOR[k]}'></span>"
                    f"<b>Kuadran {k}</b><br><span style='font-size:11.5px;color:{INK_SOFT};margin-left:17px;"
                    f"display:inline-block;max-width:230px'>{KUADRAN_DESC[k]}</span></div>"
                    f"<div style='font-size:20px;font-weight:700;color:{KUADRAN_COLOR[k]}'>{count}</div></div>",
                    unsafe_allow_html=True,
                )
                with st.popover(f"Lihat {count} nama di Kuadran {k}", use_container_width=True, disabled=count == 0):
                    if count > 0:
                        names_df = members[["Nama", "Satker", "Pangkat", "QScore"]].sort_values("QScore", ascending=False)
                        st.dataframe(names_df, use_container_width=True, hide_index=True, height=220)
                        st.download_button(
                            f"⬇️ Unduh daftar Kuadran {k} (.xlsx)",
                            data=df_to_xlsx_bytes(names_df),
                            file_name=f"kuadran_{k}.xlsx",
                            key=f"dl_kuadran_{k}",
                        )

    st.write("")
    with st.container(border=True):
        st.markdown(f"**Daftar prioritas promosi** ({len(visible)} pegawai)")
        show_cols = ["Nama", "Satker", "Pangkat", "Sublevel", "QScore", "MDP_Tahun", "Kuadran", "Readiness"]
        sorted_visible = visible[show_cols].sort_values("QScore", ascending=False)
        st.dataframe(sorted_visible, use_container_width=True, hide_index=True, height=320)
        st.download_button(
            "⬇️ Export laporan (.xlsx)", data=df_to_xlsx_bytes(sorted_visible), file_name="laporan_kuadran.xlsx"
        )


# ---------------------------------------------------------------------------
# Page: Data Pegawai
# ---------------------------------------------------------------------------
def page_pegawai(df):
    page_header("Data Pegawai & Rincian Penilaian")
    # st.caption("Data pegawai bersifat tetap (ditarik dari sumber lain) — setiap skor bisa ditelusuri ke kolom mentahnya di sebelah kanan.")

    with st.container(border=True):
        fcol1, fcol2, fcol3, fcol4 = st.columns([2, 1.3, 1.3, 1.3])
        q = fcol1.text_input("Cari NIP / nama")
        f_pangkat = fcol2.multiselect("Pangkat", PANGKAT_OPTS, default=PANGKAT_OPTS)
        f_satker = fcol3.multiselect("Satuan kerja", SATKER_OPTS, default=SATKER_OPTS)
        f_status = fcol4.multiselect("Status akhir", STATUS_OPTS, default=STATUS_OPTS)

    view = df.copy()
    if q:
        view = view[view["Nama"].str.contains(q, case=False) | view["NIP"].astype(str).str.contains(q)]
    view = view[view["Pangkat"].isin(f_pangkat) & view["Satker"].isin(f_satker) & view["Status_Akhir"].isin(f_status)]

    tab_ringkas, tab_lengkap = st.tabs(["Tampilan ringkas", "Tampilan lengkap"])

    ringkas_cols = [
        "NIP", "Nama", "Satker", "Pangkat", "Sublevel",
        "Quantitative_Score", "Qualitative_Score", "QScore", "Status_Akhir", "Readiness", "Kuadran",
    ]
    lengkap_cols = ringkas_cols[:5] + [
        "NK_1", "NK_2", "NK_3", "NK_4", "NK_5", "NK_Mean", "Skor_NK",
        "MDG_Tahun", "MDGS_Tahun", "MDP_Tahun", "Skor_MDP",
        "Pendidikan", "Skor_Pendidikan",
        "Sertifikasi", "Skor_Sertifikasi",
        "Quantitative_Score",
        "Exposure", "Potensi", "Skor_Potensi", "K3", "Skor_K3",
        "Qualitative_Score", "QScore", "Status_Akhir", "Readiness", "Kuadran",
    ]

    with tab_ringkas:
        st.dataframe(view[ringkas_cols].sort_values("QScore", ascending=False),
                     use_container_width=True, hide_index=True, height=420)
    with tab_lengkap:
        st.dataframe(view[lengkap_cols].sort_values("QScore", ascending=False),
                     use_container_width=True, hide_index=True, height=420)

    st.caption(f"Menampilkan {len(view)} dari {len(df)} pegawai")

    st.write("")
    with st.container(border=True):
        st.markdown("#### Detail & breakdown skor per pegawai")
        view2 = view.copy()
        view2["_label"] = view2["NIP"].astype(str) + " — " + view2["Nama"]
        label_pilihan = st.selectbox("Pilih pegawai", view2["_label"].tolist() if len(view2) else [])
        if label_pilihan:
            row = view2[view2["_label"] == label_pilihan].iloc[0]
            d1, d2, d3 = st.columns(3)
            with d1:
                st.markdown("**Data dasar**")
                st.write(f"NIP: {row['NIP']}")
                st.write(f"Satker: {row['Satker']}")
                st.write(f"Pangkat: {row['Pangkat']} ({row['Sublevel']})")
                st.write(f"MDG (masa dinas grade): {row['MDG_Tahun']} tahun")
                st.write(f"MDGS (masa dinas grade senior): {row['MDGS_Tahun']} tahun")
                st.write(f"Sisa masa dinas: {row['Remaining_Service']} tahun")
            with d2:
                st.markdown("**Komponen Quantitative**")
                st.write(f"NK rata-rata 5 th: {row['NK_Mean']} → skor {row['Skor_NK']}")
                st.write(f"MDP (MDG+MDGS): {row['MDP_Tahun']} th → skor {row['Skor_MDP']}")
                st.write(f"Pendidikan: {row['Pendidikan']} → skor {row['Skor_Pendidikan']}")
                st.write(f"Sertifikasi: {row['Sertifikasi']} → skor {row['Skor_Sertifikasi']}")
                st.write(f"**Quantitative Score: {row['Quantitative_Score']}**")
            with d3:
                st.markdown("**Komponen Qualitative**")
                st.write(f"Exposure: {row['Exposure']}")
                st.write(f"Potensi: {row['Potensi']} → skor {row['Skor_Potensi']}")
                st.write(f"K3: {row['K3']} → skor {row['Skor_K3']}")
                st.write(f"**Qualitative Score: {row['Qualitative_Score']}**")
                st.write(f"**QScore final: {row['QScore']}**")

            badge_admin = "✅ Lolos" if row["Lolos_Administrasi"] else "❌ Tidak lolos"
            badge_kpp = "✅ Lolos" if row["Lolos_KPP"] else "❌ Tidak lolos"
            st.info(
                f"Gate Administrasi: {badge_admin} · Gate KPP: {badge_kpp} · Status akhir: **{row['Status_Akhir']}** · "
                f"Readiness: **{row['Readiness']}**" + (f" · Kuadran **{row['Kuadran']}**" if row["Kuadran"] else "")
            )


# ---------------------------------------------------------------------------
# Page: Gate Keputusan
# ---------------------------------------------------------------------------
def page_gate(df):
    page_header("Penentuan Kandidat KPP BI Wide")
    # st.caption(
    #     "Alur: Syarat Administrasi → Kriteria KPP → cek Grade. Pegawai **Reguler** yang lolos "
    #     "diarahkan ke jalur Promosi Grade; pegawai **Senior** yang lolos masuk ke Readiness KPP "
    #     "dan Prioritisasi Kuadran."
    # )

    tab1, tab2, tab3 = st.tabs(["Syarat Administrasi", "Kriteria KPP", "Grade Senior / MDG"])

    with st.container(border=True):
        fcol1, fcol2 = st.columns(2)
        f_pangkat = fcol1.multiselect("Filter pangkat", PANGKAT_OPTS, default=PANGKAT_OPTS, key="gate_pangkat")
        f_status = fcol2.multiselect("Filter status akhir", STATUS_OPTS, default=STATUS_OPTS, key="gate_status")

    view = df[df["Pangkat"].isin(f_pangkat) & df["Status_Akhir"].isin(f_status)]

    with tab1:
        total = len(df[df["Pangkat"].isin(f_pangkat)])
        lolos = int(df[df["Pangkat"].isin(f_pangkat)]["Lolos_Administrasi"].sum())
        m1, m2 = st.columns(2)
        m1.metric("Lolos Administrasi", f"{lolos:,}".replace(",", "."))
        m2.metric("Tidak Lolos", f"{total - lolos:,}".replace(",", "."))
        cols = ["Nama", "Pangkat"] + list(ADMIN_CHECK_LABELS.keys()) + ["Lolos_Administrasi"]
        show = view[cols].rename(columns={**ADMIN_CHECK_LABELS, "Lolos_Administrasi": "LOLOS ADMINISTRASI"})
        st.dataframe(format_boolean_table(show), use_container_width=True, hide_index=True, height=420)

    with tab2:
        admin_pop = df[df["Pangkat"].isin(f_pangkat) & df["Lolos_Administrasi"]]
        lolos_kpp = int(admin_pop["Lolos_KPP"].sum())
        m1, m2 = st.columns(2)
        m1.metric("Lolos Kriteria KPP", f"{lolos_kpp:,}".replace(",", "."))
        m2.metric("Dari yang lolos administrasi", f"{len(admin_pop):,}".replace(",", "."))
        cols = ["Nama", "Pangkat", "Passing_Grade_QScore", "QScore"] + list(KPP_CHECK_LABELS.keys()) + ["Lolos_KPP"]
        show = view[cols].rename(columns={**KPP_CHECK_LABELS, "Lolos_KPP": "LOLOS KPP"})
        st.dataframe(format_boolean_table(show), use_container_width=True, hide_index=True, height=420)

    with tab3:
        kpp_pop = df[df["Pangkat"].isin(f_pangkat) & df["Lolos_KPP"]]
        n_senior = int((kpp_pop["Status_Akhir"] == "Proses KPP").sum())
        n_ready_grade = int((kpp_pop["Status_Akhir"] == "Ready Promosi Grade").sum())
        n_belum_grade = int((kpp_pop["Status_Akhir"] == "Belum Siap Promosi Grade").sum())
        m1, m2, m3 = st.columns(3)
        m1.metric("Senior → Proses KPP", f"{n_senior:,}".replace(",", "."))
        m2.metric("Reguler siap naik Grade", f"{n_ready_grade:,}".replace(",", "."))
        m3.metric("Reguler belum siap", f"{n_belum_grade:,}".replace(",", "."))
        cols = [
            "Nama", "Pangkat", "Sublevel", "Is_Senior",
            "MDG_Tahun", "Chk_Ready_Promosi_Grade",
            "MDGS_Tahun", "Chk_Ready_Promosi_Pangkat",
            "Readiness", "Status_Akhir",
        ]
        show = view[cols].rename(columns={
            "Is_Senior": "Grade Senior?",
            "Chk_Ready_Promosi_Grade": "MDG >= threshold?",
            "Chk_Ready_Promosi_Pangkat": "MDGS >= threshold?",
        })
        st.dataframe(format_boolean_table(show), use_container_width=True, hide_index=True, height=420)


# ---------------------------------------------------------------------------
# Page: Pengaturan (CRUD)
# ---------------------------------------------------------------------------
def crud_section(sheet, key_col, value_cols, value_step=0.01, value_format="%.4f"):
    df_ref = st.session_state[f"ref_{sheet}"]

    st.markdown("**Data saat ini** — ubah nilainya langsung, lalu klik Simpan")
    edited = st.data_editor(
        df_ref, num_rows="fixed", disabled=[key_col],
        use_container_width=True, hide_index=True, key=f"editor_{sheet}",
    )
    if st.button("💾 Simpan perubahan nilai", key=f"save_{sheet}"):
        st.session_state[f"ref_{sheet}"] = edited
        save_to_disk()
        st.success(f"Nilai pada {sheet} disimpan.")
        st.rerun()

    add_col, del_col = st.columns(2)
    with add_col:
        st.markdown("**➕ Tambah baris**")
        with st.form(f"add_{sheet}", clear_on_submit=True):
            new_key = st.text_input(key_col, key=f"newkey_{sheet}")
            new_values = {}
            for vc in value_cols:
                new_values[vc] = st.number_input(vc, step=value_step, format=value_format, key=f"newval_{sheet}_{vc}")
            submitted = st.form_submit_button("Tambah baris")
            if submitted:
                if not new_key.strip():
                    st.error(f"{key_col} tidak boleh kosong.")
                elif new_key in df_ref[key_col].astype(str).values:
                    st.error(f"'{new_key}' sudah ada di {key_col}.")
                else:
                    new_row = {key_col: new_key, **new_values}
                    st.session_state[f"ref_{sheet}"] = pd.concat([df_ref, pd.DataFrame([new_row])], ignore_index=True)
                    save_to_disk()
                    st.success(f"Baris '{new_key}' ditambahkan.")
                    st.rerun()

    with del_col:
        st.markdown("**🗑️ Hapus baris**")
        to_delete = st.multiselect(f"Pilih {key_col} yang mau dihapus", df_ref[key_col].astype(str).tolist(), key=f"del_{sheet}")
        if st.button("Hapus baris terpilih", key=f"delbtn_{sheet}", disabled=len(to_delete) == 0):
            st.session_state[f"ref_{sheet}"] = df_ref[~df_ref[key_col].astype(str).isin(to_delete)].reset_index(drop=True)
            save_to_disk()
            st.success(f"{len(to_delete)} baris dihapus.")
            st.rerun()


def page_master():
    page_header("Pengaturan")
    st.caption(
        "Tabel referensi yang menentukan bobot & konversi skor. "
        "Data pegawai TIDAK dikelola di sini — dianggap sumber tetap dari sistem lain."
    )

    tabs = st.tabs([
        "Bobot Quantitative", "Bobot Qualitative", "Bobot per Pangkat",
        "Skor Pendidikan", "Skor Sertifikasi", "Skor K3", "Skor Potensi", "Threshold Administrasi",
    ])
    with tabs[0]:
        crud_section("Quant_Weights", key_col="Parameter", value_cols=["Value"])
    with tabs[1]:
        crud_section("Qual_Weights", key_col="Parameter", value_cols=["Value"])
    with tabs[2]:
        crud_section("Rank_Weights", key_col="Pangkat", value_cols=["Quantitative", "Qualitative"])
    with tabs[3]:
        crud_section("Education_Score", key_col="Kategori", value_cols=["Nilai"], value_step=1.0, value_format="%.0f")
    with tabs[4]:
        crud_section("Certification_Score", key_col="Kategori", value_cols=["Nilai"], value_step=1.0, value_format="%.0f")
    with tabs[5]:
        crud_section("K3_Score", key_col="Kategori", value_cols=["Nilai"], value_step=1.0, value_format="%.0f")
    with tabs[6]:
        st.caption("Diurutkan dari kategori terbaik ke paling dasar: Future Leader → High Impact Performer → Core Employee.")
        crud_section("Potensi_Score", key_col="Kategori", value_cols=["Nilai"], value_step=1.0, value_format="%.0f")
    with tabs[7]:
        crud_section("Thresholds", key_col="Parameter", value_cols=["Value"])


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
if page == "Dashboard":
    page_dashboard(df)
elif page == "Data Pegawai":
    page_pegawai(df)
elif page == "Penentuan Kandidat KPP":
    page_gate(df)
elif page == "Pengaturan":
    page_master()
