"""Entry point GOVSAFE dengan peran Pemohon dan Petugas."""
from __future__ import annotations
import streamlit as st

from config import APP_NAME
from database.db_manager import init_db, get_buyer_by_id, add_log
from database.govsafe_schema import ensure_govsafe_schema
from blockchain.blockchain import create_genesis_block
from services.govsafe_service import get_user
from ui.styles import apply_styles
from ui.login_page import render_login
from ui.components import render_brand
from ui.dashboard import render_dashboard
from ui.govsafe_pages import render_asset_catalog, render_asset_management, render_request_center, render_ledger
from ui.steganography_decoder import render_steganography_decoder
from ui.crypto_trace import render_crypto_trace

st.set_page_config(page_title=APP_NAME, page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")
apply_styles()

try:
    init_db()
    ensure_govsafe_schema()
    create_genesis_block()
except Exception as exc:
    st.error(f"Database GOVSAFE belum siap: {exc}")
    st.info("Jalankan scripts/generate_keys.py, kemudian scripts/init_db.py.")
    st.stop()


def logout() -> None:
    user_id = st.session_state.get("buyer_id")
    if user_id:
        try:
            add_log(int(user_id), "LOGOUT", {"application": "GOVSAFE", "session": "closed"})
        except Exception:
            pass
    st.session_state.clear()


if not st.session_state.get("buyer_id"):
    render_login()
    st.stop()

try:
    user_id = int(st.session_state.get("buyer_id"))
    raw_user = get_buyer_by_id(user_id)
    user = get_user(user_id) if raw_user else None
except (ValueError, TypeError, LookupError):
    user = None

if not user or user.get("account_status") != "active":
    st.session_state.clear()
    st.rerun()

role = user.get("role", "pemohon")
role_label = "Petugas" if role == "petugas" else "Pemohon"

if role == "petugas":
    pages = ["Dashboard", "Kelola Aset", "Decoder Steganografi", "Lab Kriptografi", "Permohonan & Pesan Aman", "Ledger Audit"]
else:
    pages = ["Ringkasan", "Katalog Aset", "Permohonan & Pesan Aman", "Ledger Audit"]

if st.session_state.pop("govsafe_go_catalog", False):
    st.session_state["govsafe_nav"] = "Katalog Aset"

if st.session_state.get("govsafe_nav") not in pages:
    st.session_state.pop("govsafe_nav", None)

with st.sidebar:
    render_brand()
    st.caption(f"Akun: **{user.get('display_name') or user['username']}**")
    st.caption(f"Peran: **{role_label}**")
    st.divider()
    page = st.radio("NAVIGASI GOVSAFE", pages, key="govsafe_nav", label_visibility="collapsed")
    st.divider()
    st.caption("SESI KEAMANAN LOKAL")
    st.markdown('<div class="ug-mono">ARGON2ID · FACE · USB · VIGENERE</div>', unsafe_allow_html=True)
    st.button("KELUAR", use_container_width=True, on_click=logout)

if page in ("Ringkasan", "Dashboard"):
    render_dashboard(user, show_catalog_gate=(role == "pemohon"))
elif page == "Katalog Aset" and role == "pemohon":
    if not st.session_state.get("govsafe_catalog_unlocked", False):
        st.warning("Katalog belum dibuka. Selesaikan tantangan dan verifikasi kode pada halaman Ringkasan.")
        render_dashboard(user, show_catalog_gate=True)
    else:
        render_asset_catalog(user)
elif page == "Kelola Aset" and role == "petugas":
    render_asset_management(user)
elif page == "Decoder Steganografi" and role == "petugas":
    render_steganography_decoder(user)
elif page == "Lab Kriptografi" and role == "petugas":
    render_crypto_trace()
elif page == "Permohonan & Pesan Aman":
    render_request_center(user)
elif page == "Ledger Audit":
    render_ledger()
