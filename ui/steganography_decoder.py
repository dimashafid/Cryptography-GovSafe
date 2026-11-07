"""Decoder visual untuk demonstrasi ekstraksi metadata LSB GOVSAFE."""
from __future__ import annotations

import json
from io import BytesIO

import streamlit as st
from PIL import Image

from crypto.steganography import decode_message_trace
from ui.styles import render_page_heading


def _status_icon(status: str) -> str:
    return "✓" if status == "success" else "✕"


def render_steganography_decoder(user: dict) -> None:
    if user.get("role") != "petugas":
        st.error("Halaman decoder hanya dapat diakses oleh Petugas.")
        return

    render_page_heading(
        "ANALISIS STEGANOGRAFI",
        "GOVSAFE Metadata Decoder",
        "Demonstrasi ekstraksi metadata JSON dari citra PNG menggunakan Least Significant Bit (LSB).",
    )
    st.info(
        "Decoder ini membaca format LSB GOVSAFE versi 1: kanal RGB berurutan, "
        "satu bit paling rendah per kanal, urutan bit MSB-first, header UGLS, "
        "panjang payload, dan verifikasi SHA-256."
    )

    uploaded = st.file_uploader(
        "Unggah gambar PNG hasil steganografi",
        type=["png"],
        key="govsafe_stego_decoder_upload",
        help="Unggah file PNG asli hasil penyisipan metadata LSB GOVSAFE.",
    )
    if uploaded is None:
        st.markdown(
            '<div class="ug-card"><div class="ug-mono">INPUT REQUIRED</div>'
            '<h3>Menunggu citra steganografi</h3>'
            '<p>Setelah gambar diunggah, decoder akan menampilkan urutan bit LSB, '
            'byte hasil ekstraksi, teks UTF-8, pemeriksaan JSON, dan metadata.</p></div>',
            unsafe_allow_html=True,
        )
        return

    image_bytes = uploaded.getvalue()
    try:
        with Image.open(BytesIO(image_bytes)) as preview:
            width, height = preview.size
            fmt = preview.format
            st.image(preview, caption=f"{uploaded.name} · {width} × {height} · {fmt}", use_container_width=True)
    except Exception as exc:
        st.error(f"File gambar tidak dapat dibuka: {exc}")
        return

    if fmt != "PNG":
        st.error("Format file harus PNG.")
        return

    with st.spinner("Mengekstrak bit LSB dan memvalidasi metadata..."):
        try:
            trace = decode_message_trace(image_bytes)
        except Exception as exc:
            st.error(f"Ekstraksi gagal: {exc}")
            return

    info = trace["image"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Lebar", f"{info['width']} px")
    c2.metric("Tinggi", f"{info['height']} px")
    c3.metric("Kanal", info["channels"])
    c4.metric("Kapasitas bit", f"{info['pixel_channel_count']:,}")

    st.markdown("### Tahapan proses ekstraksi")
    for index, stage in enumerate(trace["stages"], start=1):
        status = stage["status"]
        with st.expander(f"{index}. {_status_icon(status)} {stage['name']}", expanded=True):
            st.write(stage["detail"])

    if trace["header"]:
        st.markdown("### 1. Urutan bit LSB")
        st.caption(
            "Setiap angka adalah bit paling rendah dari satu nilai kanal. "
            "Urutan kanal: R → G → B, lalu berlanjut ke piksel berikutnya."
        )
        st.code(trace["header"]["bits"], language=None)
        st.caption(f"Total header: {trace['header']['bit_count']} bit = {len(trace['header']['bytes_hex'].split())} byte.")
        st.markdown("### 2. Byte hasil pembacaan header")
        st.code(trace["header"]["bytes_hex"], language="text")
        h1, h2, h3 = st.columns(3)
        h1.metric("Magic", trace["header"]["magic_text"])
        h2.metric("Versi", trace["header"]["version"])
        h3.metric("Panjang payload", f"{trace['header']['payload_length']:,} byte")

    payload = trace.get("payload", {})
    if payload:
        st.markdown("### 3. Rekonstruksi byte payload")
        st.caption("Representasi heksadesimal dari byte metadata hasil ekstraksi.")
        st.code(payload["bytes_hex"] or "(payload kosong)", language="text")
        if payload.get("bytes_preview_truncated"):
            st.caption(f"Pratinjau dibatasi hingga {payload['bytes_preview_limit']} byte dari total {payload['byte_count']} byte.")
        st.markdown("### 4. Konversi teks UTF-8")
        if payload.get("utf8_valid"):
            st.code(payload["utf8_text"], language="text")
        else:
            st.error("Payload tidak dapat dikonversi menjadi UTF-8.")

        st.markdown("### 5. Validasi JSON")
        if payload.get("json_valid"):
            st.success("JSON valid: payload dapat diparsing menjadi struktur data.")
        else:
            st.error("JSON tidak valid atau tidak dapat diparsing.")
        checksum_ok = payload.get("checksum_valid", False)
        st.write("SHA-256:", "Cocok" if checksum_ok else "Tidak cocok")
        with st.expander("Detail hash SHA-256"):
            st.caption("Hash yang tersimpan di header")
            st.code(trace["header"]["sha256_expected"], language=None)
            st.caption("Hash yang dihitung ulang dari payload")
            st.code(payload["sha256_actual"], language=None)

    st.markdown("### 6. Metadata akhir")
    if trace["success"]:
        st.success("Ekstraksi berhasil. Checksum SHA-256 dan struktur JSON valid.")
        st.json(trace["metadata"], expanded=True)
        json_output = json.dumps(trace["metadata"], ensure_ascii=False, indent=2).encode("utf-8")
        st.download_button(
            "UNDUH HASIL JSON",
            data=json_output,
            file_name="govsafe_metadata_decoded.json",
            mime="application/json",
            use_container_width=True,
        )
    elif trace["metadata"] is not None:
        st.warning("Struktur JSON terbaca, tetapi validasi integritas gagal. Metadata ditampilkan untuk keperluan analisis, bukan dinyatakan valid.")
        st.json(trace["metadata"], expanded=True)
    else:
        st.error(trace["error"] or "Metadata tidak berhasil dipulihkan.")

    with st.expander("Parameter teknis decoder"):
        st.write({
            "metode": "Least Significant Bit (LSB)",
            "format_citra": "PNG RGB 8-bit",
            "urutan_kanal": "RGB",
            "pola_pembacaan": "Sequential / row-major",
            "bit_per_kanal": 1,
            "urutan_bit_byte": "MSB-first",
            "header": "UGLS + version + payload length + SHA-256",
            "encoding": "UTF-8",
            "serialisasi": "JSON",
        })
