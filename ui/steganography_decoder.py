"""Antarmuka dashboard untuk mengekstrak metadata LSB dari PNG GOVSAFE."""
import json

import streamlit as st

from crypto.steganography import decode_message
from ui.styles import render_page_heading


def render_steganography_decoder() -> None:
    render_page_heading(
        "UTILITAS FORENSIK GAMBAR",
        "Decoder Steganografi",
        "Unggah PNG hasil GOVSAFE untuk mengekstrak metadata JSON yang disisipkan menggunakan LSB.",
    )
    st.info(
        "Decoder ini menerima PNG steganografi yang belum dienkripsi. "
        "File gambar aset yang baru disimpan GOVSAFE dapat langsung diunggah."
    )
    uploaded = st.file_uploader(
        "Pilih gambar PNG",
        type=["png"],
        accept_multiple_files=False,
        key="govsafe_lsb_decoder_upload",
    )
    if uploaded is None:
        st.caption("Pilih file PNG untuk memulai ekstraksi.")
        return

    image_bytes = uploaded.getvalue()
    st.image(image_bytes, caption=uploaded.name, use_container_width=True)

    if st.button("EKSTRAK DATA LSB", type="primary", use_container_width=True):
        try:
            metadata = decode_message(image_bytes)
        except ValueError as exc:
            st.error(f"Ekstraksi gagal: {exc}")
            st.caption(
                "Pastikan file merupakan PNG asli hasil proses LSB GOVSAFE, "
                "bukan JPEG, tangkapan layar, atau file terenkripsi."
            )
            return
        except Exception as exc:
            st.error(f"Terjadi kesalahan saat membaca gambar: {exc}")
            return

        st.success("Pesan tersembunyi berhasil diekstrak dan checksum valid.")
        st.markdown("### Metadata tersembunyi")
        st.json(metadata, expanded=True)
        st.download_button(
            "UNDUH HASIL JSON",
            data=json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name="govsafe_metadata.json",
            mime="application/json",
            use_container_width=True,
        )
