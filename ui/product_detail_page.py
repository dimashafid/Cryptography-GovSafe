"""Detail produk yang didekripsi hanya untuk Buyer terautentikasi."""
import streamlit as st
from services.catalog_service import get_product_detail
from services.purchase_service import create_purchase_intent, request_information


def render_product_detail(buyer_id: int, product_id: int) -> None:
    product = get_product_detail(product_id)
    if not product:
        st.error("Produk tidak ditemukan.")
        return
    if st.button("← Back to catalog"):
        st.session_state.pop("selected_product_id", None)
        st.rerun()
    st.markdown(f"## {product['title']}")
    st.caption(f"SKU {product['sku']} · {product['category']} · {product['status']}")
    col1, col2 = st.columns([1, 1])
    with col1:
        st.image(product["image_bytes"], use_container_width=True)
    with col2:
        st.markdown(f"### {product['price_display']}")
        st.write(product["description"])
        st.markdown("**Specifications**")
        st.write(product["specifications"] or "Not provided")
        st.markdown("**Simulated seller contact**")
        st.code(product["seller_contact"] or "Not provided", language=None)
        b1, b2 = st.columns(2)
        with b1:
            if st.button("Request Information", use_container_width=True):
                request_information(buyer_id, product_id)
                st.success("Request tercatat pada blockchain simulasi.")
        with b2:
            if st.button("Create Purchase Intent", use_container_width=True):
                create_purchase_intent(buyer_id, product_id)
                st.success("Purchase intent simulasi tercatat. Tidak ada pembayaran aktual.")
    st.markdown("### Hidden metadata · LSB extraction")
    st.json(product["secret_metadata"])
    st.caption("LSB menyembunyikan metadata; kerahasiaan file diberikan oleh ChaCha20-Poly1305.")
