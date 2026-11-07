"""Komponen UI reusable GOVSAFE."""
import streamlit as st


def render_brand() -> None:
    st.markdown("""
    <div style="padding:10px 0 25px">
      <div class="ug-eyebrow">GOVERNMENT ASSET INFORMATION SYSTEM</div>
      <div style="font-size:27px;font-weight:800;letter-spacing:-1.4px;color:#f4f7fb">GOV<span style="color:#69c6a0">SAFE</span></div>
      <div style="font-size:11px;color:#9baabd">Secure Asset Records · Verified Communication</div>
    </div>
    """, unsafe_allow_html=True)


def stat_card(label: str, value: str, detail: str = "") -> None:
    st.markdown(
        f'<div class="ug-card"><div class="ug-kpi">{label}</div><div class="ug-kpi-value">{value}</div><div style="font-size:11px;color:#a2afc0;margin-top:5px">{detail}</div></div>',
        unsafe_allow_html=True,
    )
