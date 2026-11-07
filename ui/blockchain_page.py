"""Tampilan audit ledger GOVSAFE dan validasi linked hash."""
import json
import streamlit as st
from blockchain.blockchain import get_all_blocks, validate_chain
from ui.styles import render_page_heading


def render_blockchain() -> None:
    render_page_heading("GOVSAFE AUDIT TRAIL", "Ledger Audit", "Pencatatan aktivitas aset dan permohonan menggunakan linked hash SHA-256.")
    blocks = get_all_blocks()
    valid = validate_chain(blocks)
    st.metric("Validasi integritas ledger", "VALID" if valid else "INVALID", delta="Pemeriksaan hash")
    if st.button("VERIFIKASI LEDGER"):
        st.success("Seluruh blok valid." if validate_chain() else "Validasi gagal: ditemukan inkonsistensi.")
    for block in reversed(blocks):
        with st.expander(f"Block #{block['index']} · {block['event_type']} · {block['timestamp']}"):
            st.write("**Metadata event**")
            st.json(json.loads(block["payload_json"]))
            st.write("**Previous hash**")
            st.code(block["previous_hash"], language=None)
            st.write("**Current hash**")
            st.code(block["current_hash"], language=None)
    st.caption("Ledger ini merupakan catatan lokal yang bersifat tamper-evident, bukan blockchain terdistribusi. Isi pesan, kata sandi, dan data pribadi tidak disimpan pada payload ledger.")
