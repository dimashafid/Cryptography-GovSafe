"""Product catalog Buyer."""
import streamlit as st
from services.catalog_service import get_catalog, get_product_detail
from ui.styles import render_page_heading
from ui.product_detail_page import render_product_detail


def render_catalog(buyer_id: int) -> None:
    selected = st.session_state.get("selected_product_id")
    if selected:
        render_product_detail(buyer_id, int(selected))
        return
    render_page_heading("PRIVATE INVENTORY", "Product catalog", "Katalog barang legal dan data simulasi yang diimpor oleh pengelola.")
    products = get_catalog()
    if not products:
        st.info("Katalog masih kosong. Admin dapat mengimpor CSV melalui scripts/import_catalog.py.")
        return
    cols = st.columns(2)
    for index, product in enumerate(products):
        with cols[index % 2]:
            st.markdown('<div class="ug-card">', unsafe_allow_html=True)
            try:
                preview = get_product_detail(int(product["id"]))
                st.image(preview["image_bytes"], use_container_width=True)
            except Exception as exc:
                st.caption(f"Image preview unavailable: {type(exc).__name__}")
            st.markdown(f"#### {product['title']}")
            st.caption(f"{product['category']} · SKU {product['sku']}")
            st.markdown(f"**{product['price_display']}**")
            st.write(product['description'][:150] + ("…" if len(product['description']) > 150 else ""))
            if st.button("VIEW DETAILS", key=f"product_{product['id']}", use_container_width=True):
                st.session_state.selected_product_id = int(product["id"])
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
