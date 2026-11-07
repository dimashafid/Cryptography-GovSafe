
"""Login Buyer bertahap: USB -> Face Recognition -> Password + Vigenere."""
from __future__ import annotations

import hashlib
import json
import os

import streamlit as st

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
from auth.biometric_auth import load_encrypted_face_template, verify_face
from config import FACE_THRESHOLD
from database import db_manager
from ui.components import render_brand


def _test_login_enabled() -> bool:
    """Bypass USB/Face hanya untuk development lokal; password + Vigenere tetap wajib."""
    enabled = os.environ.get("GOVSAFE_TEST_LOGIN_BYPASS", "").strip() == "1"
    development = os.environ.get("GOVSAFE_ENV", "").strip().lower() == "development"
    bind_address = os.environ.get("STREAMLIT_SERVER_ADDRESS", "localhost").strip().lower()
    return enabled and development and bind_address in {"localhost", "127.0.0.1", "::1"}


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
            st.session_state.pop("ug_face_snapshot", None)
            st.session_state.pop("ug_face_processed_digest", None)
            st.session_state.pop("ug_face_result", None)
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
# TAHAP 2: SNAPSHOT FACE RECOGNITION
# ---------------------------------------------------------

def _render_biometric_stage():
    """Ambil satu snapshot dan proses verifikasi wajah satu kali per foto."""
    buyer_id = st.session_state.get("ug_usb_buyer_id")
    username = st.session_state.get("ug_usb_username")

    # Validasi ulang dongle ketika halaman biometrik dibuka/diperbarui.
    current_buyer, usb_message = _find_buyer_from_usb()
    if not current_buyer or current_buyer["id"] != buyer_id:
        st.session_state["ug_usb_verified"] = False
        st.session_state["ug_face_verified"] = False
        st.session_state["ug_stage"] = "usb"
        st.session_state["ug_usb_error"] = (
            "USB dongle dilepas atau tidak lagi valid. Silakan pasang kembali."
        )
        st.error(st.session_state["ug_usb_error"])
        st.rerun()

    buyer = db_manager.get_buyer_by_username(username or "")
    if not buyer or buyer["id"] != buyer_id:
        st.error("Identitas akun dari USB tidak dapat divalidasi.")
        st.session_state["ug_stage"] = "usb"
        st.rerun()

    render_brand()
    st.markdown("## 02 — Biometric Verification")
    st.success("USB Dongle: berhasil diverifikasi.")
    st.caption("Pengguna terdeteksi: " + username)

    if not buyer.get("face_encoding_enc"):
        st.error("Template wajah pengguna belum terdaftar.")
        st.stop()

    try:
        reference = load_encrypted_face_template(
            buyer["face_encoding_enc"],
            buyer["id"]
        )
    except Exception:
        st.error("Template wajah gagal dibuka atau tidak valid.")
        st.stop()

    st.caption(
        "Posisikan wajah di tengah pratinjau kamera, lalu tekan tombol "
        "Ambil Foto. Sistem hanya memproses foto setelah diambil."
    )
    snapshot = st.camera_input("Ambil Foto", key="ug_face_snapshot")

    if snapshot is not None:
        image_bytes = snapshot.getvalue()
        digest = hashlib.sha256(image_bytes).hexdigest()

        # Streamlit dapat melakukan rerun; foto yang sama tidak diproses ulang.
        if st.session_state.get("ug_face_processed_digest") != digest:
            try:
                matched = verify_face(
                    image_bytes,
                    reference,
                    threshold=FACE_THRESHOLD
                )
                result = {
                    "ok": matched,
                    "message": (
                        "Wajah berhasil diverifikasi."
                        if matched
                        else "Wajah tidak cocok dengan template akun."
                    ),
                }
            except Exception as error:
                result = {
                    "ok": False,
                    "message": str(error) or "Foto wajah gagal diproses.",
                }

            st.session_state["ug_face_processed_digest"] = digest
            st.session_state["ug_face_result"] = result

        result = st.session_state.get("ug_face_result", {})
        if result.get("ok"):
            st.session_state["ug_face_verified"] = True
            st.session_state["ug_stage"] = "login"
            st.success("Face Recognition berhasil.")
            st.rerun()
        else:
            st.session_state["ug_face_verified"] = False
            st.error(result.get("message", "Verifikasi wajah gagal."))
            st.info("Silakan ambil foto ulang dengan posisi wajah yang jelas.")

    st.warning(
        "Verifikasi ini belum memiliki liveness detection. Foto yang cocok "
        "belum membuktikan bahwa wajah berasal dari orang hidup di depan kamera."
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

    test_bypass = _test_login_enabled()
    username = (st.session_state.get("ug_test_username", "").strip().lower()
                if test_bypass else st.session_state.get("ug_usb_username", ""))
    buyer_id = st.session_state.get("ug_usb_buyer_id")
    password = st.session_state.get("ug_password", "")

    # Dalam mode testing, identitas tetap harus cocok dengan akun di database.
    test_buyer = db_manager.get_buyer_by_username(username) if test_bypass and username else None
    if test_bypass:
        buyer_id = test_buyer["id"] if test_buyer else None

    # Pastikan tahap USB dan wajah lolos pada mode normal.
    if not test_bypass and not st.session_state.get("ug_usb_verified"):
        st.session_state["ug_password_result"] = {
            "ok": False,
            "message": "USB dongle belum diverifikasi."
        }
        return

    if not test_bypass and not st.session_state.get("ug_face_verified"):
        st.session_state["ug_password_result"] = {
            "ok": False,
            "message": "Face Recognition belum berhasil."
        }
        return

    # Validasi ulang USB saat login normal; dilewati hanya dalam mode test lokal.
    current_buyer = test_buyer
    if not test_bypass:
        current_buyer, usb_message = _find_buyer_from_usb()

    if not test_bypass and (not current_buyer or current_buyer["id"] != buyer_id):
        st.session_state["ug_password_result"] = {
            "ok": False,
            "message": "USB dongle tidak valid atau telah dilepas."
        }
        st.session_state["ug_usb_verified"] = False
        st.session_state["ug_face_verified"] = False
        st.session_state["ug_stage"] = "usb"
        return

    buyer = db_manager.get_buyer_by_username(username)

    # Full bypass hanya untuk akun aktif pada mode development localhost.
    if test_bypass:
        if not buyer or buyer.get("account_status") != "active":
            st.session_state["ug_password_result"] = {
                "ok": False,
                "message": "Username tidak ditemukan atau akun tidak aktif."
            }
            return

        st.session_state["buyer_id"] = buyer["id"]
        st.session_state["buyer_username"] = buyer["username"]
        db_manager.add_log(
            buyer["id"],
            "LOGIN_SUCCESS",
            {"method": "local-test-full-bypass"}
        )
        return

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
                "method": ("test-bypass+argon2id+vigenere" if test_bypass else "usb+face+argon2id+vigenere")
            }
        )


def _render_login_stage():
    username = st.session_state.get("ug_usb_username", "")

    render_brand()

    st.markdown("## 03 — Login GOVSAFE")

    test_bypass = _test_login_enabled()
    if test_bypass:
        st.warning("FULL TEST BYPASS AKTIF — USB, Face Recognition, password, dan Vigenere dilewati. Hanya untuk development lokal; jangan aktifkan di deployment.")

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

        if test_bypass:
            st.text_input(
                "USERNAME TEST",
                key="ug_test_username",
                placeholder="Masukkan username akun terdaftar"
            )
        else:
            st.text_input(
                "USERNAME",
                value=username,
                disabled=True
            )

        if not test_bypass:
            st.text_input(
                "PASSWORD",
                type="password",
                placeholder="Masukkan password Buyer",
                key="ug_password"
            )
            _show_result("ug_password_result")

    with challenge_col:
        if not test_bypass:
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
        "MASUK MODE TEST" if test_bypass else "LOGIN",
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
        st.session_state["ug_stage"] = "login" if _test_login_enabled() else "usb"

    if _test_login_enabled():
        st.session_state["ug_stage"] = "login"

    stage = st.session_state["ug_stage"]

    if stage == "usb":
        _render_usb_stage()

    elif stage == "biometric":
        _render_biometric_stage()

    elif stage == "login":
        _render_login_stage()

    else:
        st.error("Tahap autentikasi tidak dikenal.")
