"""Tema administratif GOVSAFE untuk Streamlit."""
import streamlit as st


def apply_styles() -> None:
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
    :root { --ug-bg:#0d1521; --ug-panel:#172334; --ug-border:#2a3b50; --ug-green:#69c6a0; --ug-muted:#a2afc0; --ug-gold:#d9b66e; }
    html, body, [class*="css"] { font-family:'Manrope',sans-serif; }
    .stApp { background:radial-gradient(circle at 80% 0%,#1b3042 0%,#0d1521 48%); color:#eaf0f7; }
    [data-testid="stSidebar"] { background:#09111b; border-right:1px solid var(--ug-border); }
    [data-testid="stSidebar"] * { color:#dce6f0; }
    .ug-brand {
      display:flex; align-items:center; gap:12px; padding:7px 0 24px;
      border-bottom:1px solid rgba(105,198,160,.18); margin-bottom:17px;
    }
    .ug-brand-mark { width:54px; height:54px; flex:0 0 54px; }
    .ug-brand-mark svg { width:100%; height:100%; display:block; }
    .ug-brand-copy { min-width:0; }
    .ug-brand-kicker {
      color:#91a6b8; font:500 8px 'DM Mono',monospace; letter-spacing:.11em;
      white-space:nowrap;
    }
    .ug-brand-name {
      color:#f4f7fb; font-size:27px; line-height:1.12; font-weight:800;
      letter-spacing:-1.35px;
    }
    .ug-brand-name span { color:#69c6a0; }
    .ug-brand-tagline { color:#9baabd; font-size:10px; margin-top:3px; letter-spacing:.02em; }
    /* Navigasi sidebar minimalis tanpa radio-dot. */
    [data-testid="stSidebar"] [data-testid="stRadio"] > label { display:none; }
    [data-testid="stSidebar"] div[role="radiogroup"] { gap:6px; }
    [data-testid="stSidebar"] div[role="radiogroup"] label {
      background:transparent; border:1px solid transparent; border-radius:10px;
      padding:9px 12px; margin:0; transition:background .15s ease,border-color .15s ease;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child { display:none !important; }
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
      background:rgba(105,198,160,.12); border-color:rgba(105,198,160,.3);
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
      background:rgba(255,255,255,.055); border-color:var(--ug-border);
    }
    h1,h2,h3 { letter-spacing:-.035em; }
    .ug-eyebrow { color:var(--ug-green); font:500 11px 'DM Mono',monospace; letter-spacing:.17em; text-transform:uppercase; }
    .ug-title { color:#f2f6fb; font-size:34px; font-weight:800; letter-spacing:-.05em; margin:3px 0 5px; }
    .ug-subtitle { color:var(--ug-muted); font-size:14px; margin-bottom:24px; }
    .ug-card { background:linear-gradient(145deg,rgba(27,43,62,.97),rgba(18,30,45,.97)); border:1px solid var(--ug-border); border-radius:16px; padding:18px 20px; margin-bottom:14px; }
    .ug-kpi { color:var(--ug-muted); font-size:12px; text-transform:uppercase; letter-spacing:.09em; }
    .ug-kpi-value { color:#f2f6fb; font-size:27px; font-weight:800; margin-top:8px; }
    .ug-mono { font-family:'DM Mono',monospace; color:#9ce1c3; font-size:12px; overflow-wrap:anywhere; }
    .stButton>button { border-radius:10px; border:1px solid #468b75; background:#18543f; color:#f1fff8; font-weight:700; }
    .stButton>button:hover { border-color:#83d9b7; background:#226a50; color:white; }
    .stTextInput input,.stTextArea textarea,.stSelectbox div[data-baseweb="select"] { background:#101c2b; border-color:#344960; color:#edf3f9; }
    [data-testid="stMetric"] { background:#172638; border:1px solid var(--ug-border); padding:14px; border-radius:14px; }
    hr { border-color:#2a3b50; }
    </style>
    """, unsafe_allow_html=True)


def render_page_heading(eyebrow: str, title: str, subtitle: str = "") -> None:
    st.markdown(f'<div class="ug-eyebrow">{eyebrow}</div><div class="ug-title">{title}</div><div class="ug-subtitle">{subtitle}</div>', unsafe_allow_html=True)
