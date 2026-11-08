"""Komponen UI reusable GOVSAFE."""
from pathlib import Path

import streamlit as st


def render_brand() -> None:
    """Render emblem dan wordmark GOVSAFE pada sisi kiri header/sidebar."""
    logo_path = Path(__file__).resolve().parents[1] / "assets" / "govsafe-mark.svg"
    logo_svg = logo_path.read_text(encoding="utf-8")
    st.markdown(
        f"""
        <div class="ug-brand">
          <div class="ug-brand-mark">{logo_svg}</div>
          <div class="ug-brand-copy">
            <div class="ug-brand-kicker">GOVERNMENT ASSET SECURITY</div>
            <div class="ug-brand-name">GOV<span>SAFE</span></div>
            <div class="ug-brand-tagline">Secure · Verify · Preserve</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def stat_card(label: str, value: str, detail: str = "") -> None:
    st.markdown(
        f'<div class="ug-card"><div class="ug-kpi">{label}</div><div class="ug-kpi-value">{value}</div><div style="font-size:11px;color:#a2afc0;margin-top:5px">{detail}</div></div>',
        unsafe_allow_html=True,
    )
