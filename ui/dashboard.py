"""Dashboard GOVSAFE dengan gerbang edukasi Caesar untuk katalog Pemohon."""
from pathlib import Path
from html import escape
import streamlit as st
from database import db_manager
from blockchain.blockchain import validate_chain
from services.govsafe_service import get_dashboard_stats
from ui.styles import render_page_heading
from ui.components import stat_card

CAESAR_CIPHERTEXT = "DVHWLQIRUPDVL"
CAESAR_SHIFT = 3
CATALOG_CODE = "GOVSAFE-ASSET-2026"
GUIDE_PATH = Path(__file__).resolve().parent.parent / "data" / "panduan_rahasia.txt"


def caesar_decrypt(text: str, shift: int) -> str:
    result = []
    for char in text:
        if "A" <= char <= "Z":
            result.append(chr((ord(char) - ord("A") - shift) % 26 + ord("A")))
        elif "a" <= char <= "z":
            result.append(chr((ord(char) - ord("a") - shift) % 26 + ord("a")))
        else:
            result.append(char)
    return "".join(result)


def render_dashboard(user: dict, *, show_catalog_gate: bool = False) -> None:
    role = user.get("role", "pemohon")
    label = "PETUGAS" if role == "petugas" else "PEMOHON"
    display_name = escape(str(user.get("display_name") or user.get("username", "Pengguna")))
    render_page_heading(f"GOVSAFE · {label}", f"Selamat datang, {display_name}", "Ringkasan pengelolaan aset negara, permohonan informasi, dan komunikasi aman.")
    stats = get_dashboard_stats(int(user["id"]), role)
    blocks = db_manager.get_blocks()
    logs = db_manager.list_buyer_logs(int(user["id"]))
    c1, c2, c3 = st.columns(3)
    with c1: stat_card("Aset aktif", str(stats["assets"]), "Data aset dalam katalog GOVSAFE")
    with c2: stat_card("Total permohonan", str(stats["requests"]), "Permohonan yang terkait dengan akun")
    with c3: stat_card("Perlu perhatian", str(stats["pending"]), "Permohonan menunggu / diproses")

    st.markdown("### Status keamanan sistem")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="ug-card"><div class="ug-kpi">Autentikasi identitas</div><h4>SESSION VERIFIED</h4><p style="color:#a2afc0;font-size:13px">Argon2id · Vigenère Challenge · USB Dongle · Face Recognition</p><div class="ug-mono">AKUN TERAUTENTIKASI</div></div>', unsafe_allow_html=True)
    with col2:
        valid = validate_chain(blocks)
        latest_hash = blocks[-1]["current_hash"][:24] if blocks else "NO BLOCKS"
        status = "VALID" if valid else "INVALID"
        st.markdown(f'<div class="ug-card"><div class="ug-kpi">Integritas audit ledger</div><h4>{status}</h4><p style="color:#a2afc0;font-size:13px">Linked hash SHA-256 · pencatatan aktivitas</p><div class="ug-mono">{latest_hash}...</div></div>', unsafe_allow_html=True)

    if show_catalog_gate:
        st.divider()
        st.markdown("### 01 · Tantangan akses katalog aset")
        st.write("Selesaikan latihan Caesar Cipher sebagai langkah demonstrasi sebelum membuka katalog aset.")
        st.caption("Dekripsikan ciphertext berikut. Kunci pergeseran: 3.")
        st.code(CAESAR_CIPHERTEXT)
        answer = st.text_input("JAWABAN CAESAR CIPHER", placeholder="Masukkan plaintext hasil dekripsi", key="govsafe_caesar_answer")
        if st.button("VERIFIKASI JAWABAN", key="govsafe_verify_caesar"):
            if answer.strip().upper() == caesar_decrypt(CAESAR_CIPHERTEXT, CAESAR_SHIFT):
                st.session_state["govsafe_guide_unlocked"] = True
                st.success("Jawaban benar. Panduan akses dapat diunduh.")
            else:
                st.session_state["govsafe_guide_unlocked"] = False
                st.error("Jawaban belum tepat. Silakan coba kembali.")

        if st.session_state.get("govsafe_guide_unlocked", False):
            try:
                content = GUIDE_PATH.read_text(encoding="utf-8")
                st.download_button("UNDUH PANDUAN AKSES GOVSAFE", content.encode("utf-8"), file_name="panduan_govsafe.txt", mime="text/plain", use_container_width=True)
            except OSError as exc:
                st.error(f"Panduan tidak dapat dibaca: {exc}")
            code = st.text_input("KODE AKSES KATALOG", type="password", placeholder="Masukkan kode dari panduan", key="govsafe_catalog_code")
            if st.button("VERIFIKASI KODE KATALOG", key="govsafe_verify_catalog"):
                st.session_state["govsafe_catalog_unlocked"] = code.strip() == CATALOG_CODE
                if st.session_state["govsafe_catalog_unlocked"]:
                    st.success("Verifikasi demonstrasi berhasil.")
                else:
                    st.error("Kode tidak sesuai.")
            if st.session_state.get("govsafe_catalog_unlocked"):
                if st.button("BUKA KATALOG ASET", type="primary", use_container_width=True):
                    st.session_state["govsafe_go_catalog"] = True
                    st.rerun()
        else:
            st.info("Selesaikan tantangan untuk menampilkan panduan dan kode akses demo.")

    st.divider()
    st.markdown("### Aktivitas akun terbaru")
    if not logs:
        st.info("Belum ada aktivitas yang tercatat untuk akun ini.")
    else:
        for item in logs[:6]:
            st.markdown(f'<div class="ug-card"><b>{escape(str(item["event_type"]))}</b><div style="color:#a2afc0;font-size:12px">{escape(str(item["created_at"]))}</div><div class="ug-mono">{escape(str(item.get("details", {})))}</div></div>', unsafe_allow_html=True)
