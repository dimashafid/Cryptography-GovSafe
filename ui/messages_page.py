"""Secure messaging Buyer; isi disimpan dalam bentuk ciphertext super encryption."""
import streamlit as st
from services.message_service import send_message, get_buyer_messages
from ui.styles import render_page_heading


def render_messages(buyer_id: int) -> None:
    render_page_heading("ENCRYPTED COMMUNICATION", "Secure messages", "Pesan dienkripsi dengan Vigenère lalu AES-256-CBC dan dilindungi HMAC-SHA256.")
    with st.form("send_secure_message"):
        recipient = st.text_input("Recipient", value="Admin/Pengelola")
        message = st.text_area("Message", height=130, placeholder="Write a private message...")
        submitted = st.form_submit_button("ENCRYPT & SEND")
    if submitted:
        try:
            message_id = send_message(buyer_id, message, recipient)
            st.success(f"Pesan terenkripsi dan disimpan. Message ID: {message_id}")
        except (ValueError, RuntimeError) as exc:
            st.error(str(exc))
    st.markdown("### Conversation history")
    rows = get_buyer_messages(buyer_id)
    if not rows:
        st.info("Belum ada pesan.")
    for item in rows:
        st.markdown('<div class="ug-card">', unsafe_allow_html=True)
        st.markdown(f"**To:** {item['recipient']} · **{item['message_status'].upper()}**")
        st.caption(item["created_at"])
        st.markdown("Ciphertext")
        st.code(item["encrypted_message"][:180] + ("…" if len(item["encrypted_message"]) > 180 else ""), language=None)
        st.markdown('</div>', unsafe_allow_html=True)
    st.caption("Pengelola mengekspor dan mendekripsi pesan melalui scripts/export_messages.py di luar aplikasi.")
