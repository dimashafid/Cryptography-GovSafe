"""Halaman demonstrasi tahapan algoritma kriptografi GOVSAFE."""
from __future__ import annotations

import streamlit as st

from auth.password_auth import hash_password
from crypto.db_crypto import encrypt_column_trace
from crypto.key_manager import get_key
from crypto.vigenere_aes import encrypt_message_trace
from ui.styles import render_page_heading


def _show_stages(stages: list[dict]) -> None:
    for index, stage in enumerate(stages, start=1):
        with st.expander(f"{index}. {stage['name']}", expanded=True):
            st.write(stage["detail"])
            st.code(stage["value"], language=None)


def render_crypto_trace() -> None:
    render_page_heading(
        "LABORATORIUM KRIPTOGRAFI",
        "Jejak Proses Kriptografi",
        "Demonstrasi tahapan transformasi, parameter publik, ciphertext, dan autentikasi. Nilai kunci rahasia tidak pernah ditampilkan.",
    )
    tabs = st.tabs([
        "Pesan · Vigenère + AES-CBC + HMAC",
        "Database · AES-GCM",
        "Password · Argon2id",
    ])

    with tabs[0]:
        st.write("Rantai enkripsi pesan yang digunakan pada percakapan permohonan GOVSAFE.")
        message = st.text_area("Plaintext pesan", key="trace_message_plaintext", height=110)
        if st.button("JALANKAN ENKRIPSI PESAN", key="trace_message_run", use_container_width=True):
            try:
                st.session_state["trace_message_result"] = encrypt_message_trace(message)
            except Exception as exc:
                st.error(f"Enkripsi pesan gagal: {exc}")
        result = st.session_state.get("trace_message_result")
        if result:
            _show_stages(result["stages"])
            st.download_button(
                "UNDUH TOKEN CIPHERTEXT",
                data=result["ciphertext"].encode("ascii"),
                file_name="govsafe_message_ciphertext.txt",
                mime="text/plain",
                use_container_width=True,
            )

    with tabs[1]:
        st.write("AES-256-GCM dipakai untuk melindungi metadata kolom database. AAD mengikat ciphertext ke tabel, kolom, dan ID record.")
        db_value = st.text_area("Nilai metadata contoh", key="trace_db_plaintext", height=90)
        aad = st.text_input("AAD contoh", value="govsafe_assets:encrypted_description:1", key="trace_db_aad")
        if st.button("JALANKAN AES-256-GCM", key="trace_db_run", use_container_width=True):
            try:
                result = encrypt_column_trace(db_value, get_key("UNDERGRID_DB_KEY"), aad)
                st.session_state["trace_db_result"] = {
                    "stages": result["stages"],
                    "blob_hex": result["blob"].hex(),
                }
            except Exception as exc:
                st.error(f"Enkripsi database gagal: {exc}")
        result = st.session_state.get("trace_db_result")
        if result:
            _show_stages(result["stages"])
            st.download_button(
                "UNDUH CIPHERTEXT DATABASE (HEX)",
                data=result["blob_hex"].encode("ascii"),
                file_name="govsafe_db_ciphertext.hex",
                mime="text/plain",
                use_container_width=True,
            )

    with tabs[2]:
        st.write("Argon2id adalah fungsi hash password satu arah, bukan algoritma enkripsi. GOVSAFE menggunakan time_cost=3, memory_cost=65536 KiB, parallelism=2.")
        password = st.text_input("Password contoh (minimal 10 karakter)", type="password", key="trace_argon_password")
        if st.button("JALANKAN ARGON2ID", key="trace_argon_run", use_container_width=True):
            try:
                st.session_state["trace_argon_result"] = hash_password(password)
            except Exception as exc:
                st.error(f"Hashing password gagal: {exc}")
        encoded_hash = st.session_state.get("trace_argon_result")
        if encoded_hash:
            st.success("Hash berhasil dibuat. Password asli tidak disimpan.")
            st.code(encoded_hash, language=None)
            st.caption("String hash memuat parameter, salt acak, dan hasil hash. Verifikasi dilakukan dengan membandingkan hash melalui API Argon2, bukan dengan mendekripsinya.")
