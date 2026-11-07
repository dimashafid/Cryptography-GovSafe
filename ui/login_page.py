
"""Login Buyer bertahap: USB -> Face Recognition -> Password + Vigenere."""
from __future__ import annotations

import json
import threading
import time

import streamlit as st

try:
    from streamlit_webrtc import webrtc_streamer
except ImportError:
    webrtc_streamer = None

from auth.cryptographic_challenge import (
    generate_challenge,
    consume_challenge,
)
from auth.password_auth import authenticate_buyer
from auth.auth_dongle import (
    verify_dongle,
    detect_removable_drives,
    find_dongle_file,
)
from auth.biometric_auth import load_encrypted_face_template
from config import FACE_THRESHOLD
from database import db_manager
from ui.components import render_brand


# ---------------------------------------------------------
# STATE FACE RECOGNITION
# ---------------------------------------------------------

class FaceState:
    """Status bersama antara callback video dan tampilan Streamlit."""

    def __init__(self):
        self.lock = threading.Lock()
        self.last_check = 0.0
        self.match_streak = 0
        self.matched = False
        self.message = "Menunggu kamera aktif..."


def _get_challenge():
    if "ug_challenge" not in st.session_state:
        st.session_state["ug_challenge"] = generate_challenge()

    return st.session_state["ug_challenge"]


def _show_result(key: str) -> None:
    result = st.session_state.get(key)

    if not result:
        return

    if result["ok"]:
        st.success("✓ " + result["message"])
    else:
        st.error("✗ " + result["message"])


# ---------------------------------------------------------
# TAHAP 1: USB DONGLE
# ---------------------------------------------------------

def _find_buyer_from_usb():
    """Mencari dan memvalidasi USB dongle terhadap database."""

    drives = detect_removable_drives()

    if not drives:
        return None, "USB dongle tidak terdeteksi."

    key_files = find_dongle_file(drives)

    if not key_files:
        return None, (
            "USB terdeteksi, tetapi file dongle GOVSAFE tidak ditemukan."
        )

    for key_file in key_files:
        try:
            data = json.loads(key_file.read_text(encoding="utf-8"))
            username = str(data.get("username", "")).strip().lower()

            if not username:
                continue

            buyer = db_manager.get_buyer_by_username(username)

            if not buyer:
                continue

            if not verify_dongle(
                buyer,
                drives=[str(key_file.parent)]
            ):
                continue

            if buyer["account_status"] != "active":
                return None, "USB valid, tetapi akun Akun tidak aktif."

            return buyer, "USB dongle berhasil diverifikasi."

        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            continue

    return None, "Token USB tidak valid atau tidak cocok dengan database."


def _render_usb_stage():
    """Memindai USB secara otomatis setiap satu detik."""

    render_brand()

    st.markdown("## 01 — USB Dongle Verification")
    st.caption(
        "Sistem sedang memindai perangkat USB yang terdaftar secara otomatis."
    )

    @st.fragment(run_every="1s")
    def usb_scanner():
        buyer, message = _find_buyer_from_usb()

        if buyer:
            st.session_state["ug_usb_buyer_id"] = buyer["id"]
            st.session_state["ug_usb_username"] = buyer["username"]
            st.session_state["ug_usb_verified"] = True
            st.session_state["ug_face_verified"] = False
            st.session_state["ug_face_state"] = FaceState()
            st.session_state["ug_stage"] = "biometric"

            st.success("USB Dongle berhasil diverifikasi.")
            st.caption("Mengalihkan ke tahap pengenalan wajah...")

            st.rerun()

        st.session_state["ug_usb_verified"] = False
        st.session_state["ug_usb_error"] = message

        st.info("Memindai USB dongle...")
        st.warning(message)
        st.caption(
            "Pasang USB yang telah terdaftar. "
            "Sistem akan memeriksa kembali secara otomatis."
        )

    usb_scanner()


# ---------------------------------------------------------
# TAHAP 2: FACE RECOGNITION REALTIME
# ---------------------------------------------------------

def _build_face_callback(known_encoding, state):
    """Memproses maksimal sekitar tiga frame setiap detik."""

    import face_recognition

    def video_frame_callback(frame):
        now = time.monotonic()

        # Batasi pemrosesan menjadi maksimal sekitar 3 sampel/detik.
        with state.lock:
            if state.matched:
                return frame

            if now - state.last_check < (1 / 3):
                return frame

            state.last_check = now

        try:
            image = frame.to_ndarray(format="rgb24")

            locations = face_recognition.face_locations(
                image,
                model="hog"
            )

            if len(locations) == 0:
                message = "Wajah belum terdeteksi. Arahkan wajah ke kamera."
                matched_now = False

            elif len(locations) > 1:
                message = (
                    "Terdeteksi lebih dari satu wajah. "
                    "Gunakan satu wajah saja."
                )
                matched_now = False

            else:
                encodings = face_recognition.face_encodings(
                    image,
                    known_face_locations=locations
                )

                if len(encodings) != 1:
                    message = "Encoding wajah gagal diproses."
                    matched_now = False

                else:
                    distance = float(
                        face_recognition.face_distance(
                            [known_encoding],
                            encodings[0]
                        )[0]
                    )

                    with state.lock:
                        current_streak = state.match_streak

                    if distance <= FACE_THRESHOLD:
                        new_streak = current_streak + 1
                        matched_now = new_streak >= 3

                        if matched_now:
                            message = "Wajah berhasil diverifikasi."
                        else:
                            message = (
                                f"Wajah cocok. "
                                f"Konfirmasi {new_streak}/3."
                            )

                    else:
                        new_streak = 0
                        matched_now = False
                        message = "Wajah tidak cocok dengan data Buyer."

                    with state.lock:
                        state.match_streak = new_streak

            if len(locations) != 1:
                with state.lock:
                    state.match_streak = 0

            with state.lock:
                state.message = message

                if matched_now:
                    state.matched = True

        except Exception:
            with state.lock:
                state.match_streak = 0
                state.matched = False
                state.message = (
                    "Terjadi kesalahan saat memproses video wajah."
                )

        return frame

    return video_frame_callback


def _render_live_face(known_encoding, buyer_id):
    """Menjalankan kamera dan memantau hasil Face Recognition."""

    if webrtc_streamer is None:
        st.error(
            "Komponen kamera belum terpasang. Jalankan perintah:"
        )
        st.code("python -m pip install streamlit-webrtc")
        return

    if not hasattr(st, "fragment"):
        st.error(
            "Versi Streamlit belum mendukung fragment. "
            "Perbarui Streamlit terlebih dahulu."
        )
        return

    state = st.session_state["ug_face_state"]

    try:
        callback = _build_face_callback(known_encoding, state)
    except Exception as error:
        st.error(
            "Face Recognition tidak dapat dijalankan. "
            "Periksa instalasi face_recognition dan dlib."
        )
        st.caption(str(error))
        return

    @st.fragment(run_every="1s")
    def live_face_status():

        # Pastikan USB yang digunakan masih sama dan masih valid.
        current_buyer, usb_message = _find_buyer_from_usb()

        if (
            not current_buyer
            or current_buyer["id"] != buyer_id
        ):
            with state.lock:
                state.match_streak = 0
                state.matched = False
                state.message = "USB dongle terputus."

            st.session_state["ug_usb_verified"] = False
            st.session_state["ug_face_verified"] = False
            st.session_state["ug_stage"] = "usb"
            st.session_state["ug_usb_error"] = (
                "USB dilepas atau tidak lagi valid. "
                "Silakan pasang kembali USB dongle."
            )

            st.warning("USB dongle tidak terdeteksi.")
            st.rerun()

        ctx = webrtc_streamer(
            key=f"ug-face-{buyer_id}",
            video_frame_callback=callback,
            media_stream_constraints={
                "video": True,
                "audio": False,
            },
            media_toggle_controls=False,
            desired_playing_state=True,
        )

        with state.lock:
            matched = state.matched
            message = state.message

        if matched and ctx.state.playing:
            st.session_state["ug_face_verified"] = True
            st.session_state["ug_stage"] = "login"

            st.success("Face Recognition berhasil.")
            st.rerun()

        elif not ctx.state.playing:
            with state.lock:
                state.match_streak = 0
                state.matched = False

            st.info(
                "Menunggu izin kamera dari browser. "
                "Izinkan akses kamera apabila muncul permintaan izin."
            )

        else:
            if (
                "tidak cocok" in message.lower()
                or "lebih dari satu" in message.lower()
                or "gagal" in message.lower()
                or "kesalahan" in message.lower()
            ):
                st.error("Biometric: " + message)
            else:
                st.info("Biometric: " + message)

    live_face_status()


def _render_biometric_stage():
    buyer_id = st.session_state.get("ug_usb_buyer_id")
    username = st.session_state.get("ug_usb_username")

    buyer = db_manager.get_buyer_by_username(username or "")

    if not buyer or buyer["id"] != buyer_id:
        st.error("Identitas Akun dari USB tidak dapat divalidasi.")
        st.session_state["ug_stage"] = "usb"
        st.rerun()

    render_brand()

    st.markdown("## 02 — Biometric Verification")

    st.success("USB Dongle: berhasil diverifikasi.")
    st.caption("Pengguna terdeteksi: " + username)

    if not buyer.get("face_encoding_enc"):
        st.error("Template wajah Pengguna belum terdaftar.")
        st.stop()

    try:
        reference = load_encrypted_face_template(
            buyer["face_encoding_enc"],
            buyer["id"]
        )
    except Exception:
        st.error("Template wajah gagal dibuka atau tidak valid.")
        st.stop()

    if "ug_face_state" not in st.session_state:
        st.session_state["ug_face_state"] = FaceState()

    st.caption(
        "Kamera akan diaktifkan secara otomatis setelah browser "
        "memberikan izin. Sistem akan memproses wajah secara berkala."
    )

    _render_live_face(reference, buyer_id)

    st.warning(
        "Pengenalan wajah ini belum memiliki liveness detection. "
        "Kecocokan wajah saja belum menjamin bahwa wajah berasal "
        "dari orang hidup di depan kamera."
    )


# ---------------------------------------------------------
# TAHAP 3: PASSWORD + VIGENERE
# ---------------------------------------------------------

def _regenerate_challenge():
    current = st.session_state.get("ug_challenge")

    if current:
        current["used"] = True

    st.session_state["ug_challenge"] = generate_challenge()
    st.session_state["ug_token"] = ""
    st.session_state["ug_vigenere_result"] = None


def _submit_login():
    """Memvalidasi USB, Face Recognition, password, dan Vigenere."""

    username = st.session_state.get("ug_usb_username", "")
    buyer_id = st.session_state.get("ug_usb_buyer_id")
    password = st.session_state.get("ug_password", "")

    # Pastikan seluruh tahap sebelumnya sudah berhasil.
    if not st.session_state.get("ug_usb_verified"):
        st.session_state["ug_password_result"] = {
            "ok": False,
            "message": "USB dongle belum diverifikasi."
        }
        return

    if not st.session_state.get("ug_face_verified"):
        st.session_state["ug_password_result"] = {
            "ok": False,
            "message": "Face Recognition belum berhasil."
        }
        return

    # Validasi ulang USB saat tombol login ditekan.
    current_buyer, usb_message = _find_buyer_from_usb()

    if not current_buyer or current_buyer["id"] != buyer_id:
        st.session_state["ug_password_result"] = {
            "ok": False,
            "message": "USB dongle tidak valid atau telah dilepas."
        }
        st.session_state["ug_usb_verified"] = False
        st.session_state["ug_face_verified"] = False
        st.session_state["ug_stage"] = "usb"
        return

    buyer = db_manager.get_buyer_by_username(username)

    password_record = None

    if buyer and buyer["id"] == buyer_id:
        password_record = authenticate_buyer(username, password)

    password_ok = bool(
        password_record
        and password_record["id"] == buyer_id
    )

    st.session_state["ug_password_result"] = {
        "ok": password_ok,
        "message": (
            "Password benar."
            if password_ok
            else "Password salah atau akun tidak aktif."
        ),
    }

    challenge = st.session_state.get("ug_challenge")
    token = st.session_state.get("ug_token", "")

    challenge_ok = consume_challenge(challenge, token)

    st.session_state["ug_vigenere_result"] = {
        "ok": challenge_ok,
        "message": (
            "Jawaban Vigenere benar."
            if challenge_ok
            else "Token Vigenere salah atau sudah digunakan."
        ),
    }

    # Challenge hanya dapat digunakan sekali.
    st.session_state["ug_challenge"] = generate_challenge()

    st.session_state["ug_password"] = ""
    st.session_state["ug_token"] = ""

    if password_ok and challenge_ok:
        st.session_state["buyer_id"] = buyer["id"]
        st.session_state["buyer_username"] = buyer["username"]

        db_manager.add_log(
            buyer["id"],
            "LOGIN_SUCCESS",
            {
                "method": "usb+face+argon2id+vigenere"
            }
        )


def _render_login_stage():
    username = st.session_state.get("ug_usb_username", "")

    render_brand()

    st.markdown("## 03 — Login GOVSAFE")

    if st.session_state.get("ug_usb_verified"):
        st.success("USB Dongle: berhasil diverifikasi.")

    if st.session_state.get("ug_face_verified"):
        st.success("Biometric: wajah berhasil diverifikasi.")

    login_col, challenge_col = st.columns(
        [1, 1],
        gap="large"
    )

    with login_col:
        st.markdown("### Login")

        st.text_input(
            "USERNAME",
            value=username,
            disabled=True
        )

        st.text_input(
            "PASSWORD",
            type="password",
            placeholder="Masukkan password Buyer",
            key="ug_password"
        )

        _show_result("ug_password_result")

    with challenge_col:
        challenge = _get_challenge()

        st.markdown("### Vigenere Challenge")

        st.caption(
            "Dekripsikan ciphertext menggunakan kunci yang disediakan."
        )

        st.markdown("**Ciphertext**")
        st.code(challenge["ciphertext"], language=None)

        st.markdown("**Decryption key**")
        st.code(challenge["key"], language=None)

        st.text_input(
            "DECRYPTED TOKEN",
            key="ug_token",
            placeholder="Masukkan plaintext A-Z"
        )

        _show_result("ug_vigenere_result")

        st.button(
            "REGENERATE CHALLENGE",
            on_click=_regenerate_challenge,
            use_container_width=True
        )

    st.button(
        "LOGIN",
        on_click=_submit_login,
        use_container_width=True
    )


# ---------------------------------------------------------
# ROUTING TAHAP AUTENTIKASI
# ---------------------------------------------------------

def render_login():
    """Mengatur perpindahan antartahap autentikasi."""

    if st.session_state.get("buyer_id"):
        return

    if "ug_stage" not in st.session_state:
        st.session_state["ug_stage"] = "usb"

    stage = st.session_state["ug_stage"]

    if stage == "usb":
        _render_usb_stage()

    elif stage == "biometric":
        _render_biometric_stage()

    elif stage == "login":
        _render_login_stage()

    else:
        st.error("Tahap autentikasi tidak dikenal.")
