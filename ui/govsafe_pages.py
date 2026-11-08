"""Halaman katalog aset, pengelolaan petugas, dan percakapan permohonan GOVSAFE."""
import streamlit as st
from services import govsafe_service as gov
from ui.styles import render_page_heading


def render_asset_catalog(user: dict) -> None:
    render_page_heading("KATALOG ASET NEGARA", "Katalog Aset", "Informasi aset sitaan, barang rampasan negara, dan barang bukti yang dapat diakses sesuai tingkat keterbukaan data.")
    assets = gov.list_assets(role="pemohon")
    if not assets:
        st.info("Belum ada aset yang dipublikasikan. Petugas perlu menambahkan data aset terlebih dahulu.")
        return
    query = st.text_input("Cari kode, nama, atau kategori aset", key="govsafe_asset_search").strip().lower()
    filtered = [a for a in assets if not query or query in a["asset_code"].lower() or query in a["name"].lower() or query in a["category"].lower()]
    if not filtered:
        st.warning("Tidak ada aset yang sesuai dengan pencarian.")
        return
    for start in range(0, len(filtered), 2):
        cols = st.columns(2)
        for col, asset in zip(cols, filtered[start:start + 2]):
            with col:
                st.markdown('<div class="ug-card">', unsafe_allow_html=True)
                st.markdown(f"#### {asset['name']}")
                st.caption(f"{asset['asset_code']} · {asset['category']}")
                st.markdown(f"**Status hukum:** {asset['legal_status']}  \n**Kondisi:** {asset['condition']}")
                st.write(asset["description"][:210] + ("…" if len(asset["description"]) > 210 else ""))
                if asset["access_level"] == "Terbatas":
                    st.caption("Lokasi penyimpanan dibatasi untuk Petugas berwenang.")
                else:
                    st.caption(f"Lokasi: {asset['storage_location']}")
                if st.button("LIHAT DETAIL & AJUKAN PERMOHONAN", key=f"govsafe_asset_{asset['id']}", use_container_width=True):
                    st.session_state["govsafe_selected_asset"] = int(asset["id"])
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    selected_id = st.session_state.get("govsafe_selected_asset")
    if selected_id:
        st.divider()
        detail = gov.get_asset_detail(int(selected_id), role="pemohon")
        if not detail:
            st.warning("Aset tidak ditemukan.")
            st.session_state.pop("govsafe_selected_asset", None)
            return
        st.markdown(f"### Detail aset: {detail['name']}")
        c1, c2 = st.columns([1, 1.2])
        with c1:
            st.image(detail["image_bytes"], use_container_width=True)
            try:
                downloadable_png = gov.prepare_asset_download_png(
                    detail["image_bytes"],
                    access_level=detail["access_level"],
                    role=user.get("role", "pemohon"),
                )
                st.download_button(
                    "Download PNG",
                    data=downloadable_png,
                    file_name=f"{detail['asset_code']}.png",
                    mime="image/png",
                    key=f"govsafe_download_stego_{detail['id']}",
                    use_container_width=True,
                    help="Unduh salinan PNG yang mempertahankan payload steganografi LSB GOVSAFE.",
                )
                if detail["access_level"] == "Terbatas":
                    st.caption("Pada salinan unduhan, informasi lokasi terbatas disamarkan di dalam payload LSB.")
            except Exception as exc:
                st.warning(f"PNG belum dapat disiapkan untuk diunduh: {exc}")
        with c2:
            st.write(detail["description"])
            st.write(f"**Kode aset:** {detail['asset_code']}")
            st.write(f"**Kategori:** {detail['category']}")
            st.write(f"**Status hukum:** {detail['legal_status']}")
            st.write(f"**Kondisi:** {detail['condition']}")
            if detail["access_level"] == "Terbatas":
                st.info("Lokasi penyimpanan merupakan informasi terbatas.")
            else:
                st.write(f"**Lokasi:** {detail['storage_location']}")
        with st.form("govsafe_create_request"):
            st.markdown("#### Ajukan permohonan informasi")
            request_type = st.selectbox("Jenis permohonan", ["Permohonan Informasi", "Permohonan Dokumen"])
            subject = st.text_input("Subjek permohonan", placeholder="Contoh: Permintaan informasi kondisi aset")
            details = st.text_area("Rincian permohonan", height=110, placeholder="Jelaskan informasi atau dokumen yang dibutuhkan.")
            submitted = st.form_submit_button("KIRIM PERMOHONAN SECARA AMAN", use_container_width=True)
        if submitted:
            try:
                request_id = gov.create_request(applicant_id=int(user["id"]), asset_id=int(selected_id), request_type=request_type, subject=subject, details=details)
                st.success(f"Permohonan berhasil dicatat. ID internal: {request_id}. Petugas akan mengambil dan menindaklanjuti permohonan.")
                st.session_state.pop("govsafe_selected_asset", None)
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
        if st.button("TUTUP DETAIL", key="govsafe_close_asset_detail"):
            st.session_state.pop("govsafe_selected_asset", None)
            st.rerun()


def render_asset_management(user: dict) -> None:
    render_page_heading("MANAJEMEN DATA ASET", "Kelola Aset", "Pendaftaran dan pengendalian informasi aset dilakukan oleh akun Petugas yang telah diprovisikan.")
    with st.expander("Daftarkan aset baru", expanded=True):
        with st.form("govsafe_asset_create", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                code = st.text_input("Kode aset", placeholder="AST-2026-001")
                name = st.text_input("Nama aset")
                category = st.selectbox("Kategori", ["Kendaraan", "Elektronik", "Properti", "Mesin dan peralatan", "Barang bernilai", "Lainnya"])
                legal_status = st.selectbox("Status hukum", list(gov.LEGAL_STATUSES))
                condition = st.selectbox("Kondisi aset", ["Baik", "Rusak ringan", "Rusak berat", "Belum diperiksa"])
            with c2:
                storage_location = st.text_input("Lokasi penyimpanan", placeholder="Lokasi internal / kode gudang")
                access_level = st.selectbox("Keterbukaan lokasi", ["Terbatas", "Publik"], help="Lokasi Terbatas tidak ditampilkan pada akun Pemohon.")
                description = st.text_area("Deskripsi aset", height=155)
                image_file = st.file_uploader("Foto aset (PNG)", type=["png"])
            submitted = st.form_submit_button("SIMPAN DATA ASET", use_container_width=True)
        if submitted:
            try:
                if image_file is None:
                    raise ValueError("Foto aset wajib diunggah.")
                asset_id = gov.create_asset(
                    officer_id=int(user["id"]), asset_code=code, name=name,
                    category=category, legal_status=legal_status, condition=condition,
                    storage_location=storage_location, access_level=access_level,
                    description=description, image_bytes=image_file.getvalue(),
                )
                st.success(f"Aset berhasil didaftarkan dengan ID {asset_id}.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    st.markdown("### Data aset terdaftar")
    assets = gov.list_assets(role="petugas", include_inactive=True)
    if not assets:
        st.info("Belum ada data aset.")
    for asset in assets:
        with st.expander(f"{asset['asset_code']} · {asset['name']} · {asset['asset_status']}"):
            c1, c2 = st.columns([1, 2])
            with c1:
                try:
                    detail = gov.get_asset_detail(asset["id"], role="petugas")
                    st.image(detail["image_bytes"], use_container_width=True)
                except Exception as exc:
                    st.warning(f"Foto tidak dapat dibuka: {exc}")
            with c2:
                st.write(f"**Status hukum:** {asset['legal_status']}")
                st.write(f"**Kondisi:** {asset['condition']}")
                st.write(f"**Lokasi:** {asset['storage_location']}")
                st.write(f"**Tingkat akses:** {asset['access_level']}")

                with st.form(f"edit_asset_catalog_{asset['id']}"):
                    st.markdown("**Edit metadata katalog**")
                    categories = list(gov.ASSET_CATEGORIES)
                    if asset["category"] not in categories:
                        categories.append(asset["category"])
                    edit_name = st.text_input("Nama aset", value=asset["name"])
                    edit_category = st.selectbox("Kategori", categories, index=categories.index(asset["category"]))
                    legal_options = list(gov.LEGAL_STATUSES)
                    edit_legal = st.selectbox("Status hukum", legal_options, index=legal_options.index(asset["legal_status"]))
                    edit_condition = st.text_input("Kondisi", value=asset["condition"])
                    edit_description = st.text_area("Deskripsi / isi katalog", value=asset["description"], height=110)
                    edit_location = st.text_input("Lokasi penyimpanan", value=asset["storage_location"])
                    access_options = ["Terbatas", "Publik"]
                    edit_access = st.selectbox("Tingkat akses", access_options, index=access_options.index(asset["access_level"]))
                    save_edit = st.form_submit_button("SIMPAN PERUBAHAN KATALOG", use_container_width=True)

                if save_edit:
                    try:
                        gov.update_asset_catalog(
                            officer_id=int(user["id"]),
                            asset_id=int(asset["id"]),
                            name=edit_name,
                            category=edit_category,
                            legal_status=edit_legal,
                            condition=edit_condition,
                            description=edit_description,
                            storage_location=edit_location,
                            access_level=edit_access,
                        )
                        st.success("Metadata katalog diperbarui. PNG dan metadata snapshot LSB tidak diubah.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Metadata aset gagal diperbarui: {exc}")

                if asset["asset_status"] == "Aktif":
                    if st.button("ARSIPKAN ASET", key=f"archive_asset_{asset['id']}"):
                        try:
                            gov.archive_asset(officer_id=int(user["id"]), asset_id=int(asset["id"]))
                            st.success("Aset diarsipkan.")
                            st.rerun()
                        except Exception as exc:
                            st.error(str(exc))


def _render_conversation(user: dict, request: dict) -> None:
    request_id = int(request["id"])
    role = user.get("role", "pemohon")
    if role == "petugas" and request.get("assigned_officer_id") is None:
        if st.button("AMBIL PERMOHONAN INI", key=f"claim_{request_id}"):
            try:
                gov.claim_request(officer_id=int(user["id"]), request_id=request_id)
                st.success("Permohonan berhasil diambil dan ditugaskan kepada Anda.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    elif role == "petugas" and request.get("assigned_officer_id") != int(user["id"]):
        st.warning(f"Permohonan sedang ditangani oleh {request.get('officer_username') or 'Petugas lain'}.")
    else:
        st.caption(f"Petugas penanggung jawab: {request.get('officer_username') or 'Belum ditugaskan'}")

    st.markdown("#### Pesan aman")
    can_read = role == "pemohon" or request.get("assigned_officer_id") == int(user["id"])
    if can_read:
        try:
            messages = gov.list_request_messages(user_id=int(user["id"]), role=role, request_id=request_id)
            if not messages:
                st.info("Belum ada pesan dalam percakapan ini.")
            for msg in messages:
                label = "Anda" if msg["is_own"] else msg["sender_username"]
                st.markdown('<div class="ug-card">', unsafe_allow_html=True)
                st.markdown(f"**{label}** · {msg['created_at']}")
                st.write(msg["plaintext"])
                with st.expander("Lihat ciphertext tersimpan"):
                    st.code(msg["ciphertext"], language=None)
                st.markdown('</div>', unsafe_allow_html=True)
        except Exception as exc:
            st.error(f"Percakapan belum dapat dibuka: {exc}")

        can_send = request.get("request_status") != "Ditutup" and (
            (role == "pemohon" and request.get("assigned_officer_id") is not None)
            or (role == "petugas" and request.get("assigned_officer_id") == int(user["id"]))
        )
        if can_send:
            with st.form(f"send_request_message_{request_id}"):
                message = st.text_area("Tulis pesan", height=90, placeholder="Pesan akan dienkripsi sebelum disimpan.")
                send = st.form_submit_button("ENKRIPSI & KIRIM PESAN", use_container_width=True)
            if send:
                try:
                    gov.send_request_message(sender_id=int(user["id"]), request_id=request_id, plaintext=message)
                    st.success("Pesan berhasil dienkripsi, disimpan, dan dicatat pada audit ledger.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
        elif request.get("request_status") == "Ditutup":
            st.info("Permohonan telah ditutup sehingga percakapan tidak dapat menerima pesan baru.")
        elif role == "pemohon":
            st.info("Pesan dapat dikirim setelah Petugas mengambil permohonan dan ditetapkan sebagai penanggung jawab.")

    if role == "petugas" and request.get("assigned_officer_id") == int(user["id"]):
        current_status = request["request_status"]
        with st.form(f"update_request_status_{request_id}"):
            new_status = st.selectbox("Status permohonan", list(gov.REQUEST_STATUSES), index=list(gov.REQUEST_STATUSES).index(current_status) if current_status in gov.REQUEST_STATUSES else 0)
            update = st.form_submit_button("PERBARUI STATUS")
        if update and new_status != current_status:
            try:
                gov.update_request_status(officer_id=int(user["id"]), request_id=request_id, status=new_status)
                st.success("Status permohonan diperbarui.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))


def render_request_center(user: dict) -> None:
    role = user.get("role", "pemohon")
    is_officer = role == "petugas"
    render_page_heading("PUSAT LAYANAN GOVSAFE", "Permohonan & Pesan Aman", "Setiap pertanyaan aset menjadi percakapan terikat pada nomor permohonan. Isi pesan dienkripsi dengan Vigenère, AES-256-CBC, dan HMAC-SHA256.")
    requests = gov.list_requests(user_id=int(user["id"]), role=role)
    if not requests:
        st.info("Belum ada permohonan." if not is_officer else "Belum ada permohonan yang masuk dari Pemohon.")
        return

    labels = {r["id"]: f"{r['request_code']} · {r['asset_code']} · {r['request_status']}" for r in requests}
    selected = st.selectbox("Pilih permohonan", options=[r["id"] for r in requests], format_func=lambda x: labels[x], key=f"govsafe_request_selected_{role}")
    request = next(r for r in requests if r["id"] == selected)
    st.markdown('<div class="ug-card">', unsafe_allow_html=True)
    st.markdown(f"### {request['subject']}")
    st.caption(f"{request['request_code']} · {request['request_type']} · {request['created_at']}")
    st.write(request["details"])
    st.write(f"**Aset:** {request['asset_code']} · {request['category']} · {request['legal_status']}")
    st.write(f"**Pemohon:** {request['applicant_username']} · **Status:** {request['request_status']}")
    st.markdown('</div>', unsafe_allow_html=True)
    _render_conversation(user, request)


def render_ledger() -> None:
    from ui.blockchain_page import render_blockchain
    render_blockchain()
