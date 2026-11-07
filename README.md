# GOVSAFE — Government Seized Asset Security & Management System

GOVSAFE adalah aplikasi demonstrasi akademik untuk pencatatan informasi barang sitaan, barang rampasan negara, dan barang bukti, pengajuan permohonan informasi/dokumen, serta komunikasi terenkripsi antara Pemohon dan Petugas. GOVSAFE **bukan marketplace** dan tidak memiliki transaksi jual beli, pembayaran, saldo, escrow, atau fitur lelang.

## Peran pengguna

| Peran | Hak akses utama |
|---|---|
| **Pemohon** | Melihat katalog aset yang aktif dan informasinya sesuai tingkat akses; mengajukan permohonan informasi/dokumen; membaca dan mengirim pesan pada permohonan miliknya. |
| **Petugas** | Mendaftarkan dan mengarsipkan aset; melihat detail internal termasuk lokasi penyimpanan; mengambil permohonan; memperbarui status; membalas pesan Pemohon. |
| **Pengelola sistem** | Menyiapkan akun melalui CLI, mengatur kunci, dan mengelola instalasi. Tidak ada registrasi publik atau halaman admin umum. |

Akun lama UnderGrid dimigrasikan otomatis menjadi `pemohon`. Untuk akun lama yang harus menjadi Petugas, gunakan `scripts/set_user_role.py`.

## Alur aplikasi

1. Pengguna melewati autentikasi berlapis yang telah tersedia: USB dongle, pengenalan wajah, password Argon2id, dan challenge Vigenère.
2. Pemohon menyelesaikan tantangan Caesar demonstratif pada Ringkasan sebelum membuka Katalog Aset.
3. Pemohon memilih aset dan mengajukan `Permohonan Informasi` atau `Permohonan Dokumen`.
4. Petugas mengambil permohonan. Status berubah menjadi `Diproses`; kemudian Petugas dan Pemohon dapat berkomunikasi dalam percakapan yang terkait dengan nomor permohonan.
5. Petugas memperbarui status menjadi `Dijawab` atau `Ditutup` sesuai hasil penanganan.
6. Aktivitas penting dicatat pada audit ledger linked-hash SHA-256. Payload ledger hanya memuat metadata ID/status; plaintext pesan dan informasi rahasia tidak dimasukkan ke ledger.

## Status hukum dan batasan data

`Barang sitaan` dan `Barang rampasan negara` adalah kategori status hukum yang berbeda. Pencatatan pada GOVSAFE tidak dengan sendirinya membuktikan bahwa barang dapat dialihkan, dijual, dilelang, atau digunakan. Penetapan status dan kewenangan akses tetap mengikuti dokumen serta keputusan pejabat/instansi yang berwenang. Data pada aplikasi demo sebaiknya fiktif atau telah dianonimkan.

Lokasi penyimpanan memiliki tingkat akses `Terbatas` atau `Publik`. Lokasi berstatus Terbatas tidak ditampilkan pada akun Pemohon. Isi deskripsi, nama, kondisi, lokasi, dan path foto disimpan terenkripsi menggunakan AES-256-GCM dengan AAD yang mengikat tabel, kolom, dan ID record.

## Penerapan patch

Patch ini ditujukan untuk branch `Trial` dari repository ProjectCrypto-UnderGrid. Ekstrak isi ZIP ke folder root proyek dan izinkan berkas dengan nama sama ditimpa. Patch **tidak** menyertakan `.env`, database, folder virtual environment, foto biometrik, maupun data akun.

Jalankan sekali untuk menyesuaikan istilah yang masih tertulis Buyer pada halaman login lama:

```bash
python -m scripts.migrate_login_labels
```

Lalu migrasikan skema database dan pertahankan data lama:

```bash
python -m scripts.init_db
```

Perintah tersebut menambahkan kolom peran ke tabel akun serta membuat tabel `govsafe_assets`, `govsafe_requests`, dan `govsafe_messages`. Tabel lama tidak dihapus. Akun lama memperoleh peran default `pemohon`. Baris pada tabel `products` versi UnderGrid tidak otomatis dipindahkan ke tabel aset GOVSAFE karena data lama tidak memiliki atribut status hukum dan lokasi penyimpanan; daftarkan ulang sebagai data aset yang telah diverifikasi oleh Petugas. Data pesan lama juga tidak dipindahkan ke percakapan GOVSAFE.

Buat akun baru melalui CLI:

```bash
python -m scripts.create_buyer
```

Saat diminta, pilih `pemohon` atau `petugas`. Setelah itu, daftarkan USB dongle dan template wajah menggunakan username yang sama seperti sebelumnya:

```bash
python -m scripts.generate_dongle username E:\
python -m scripts.enroll_face username path/foto_referensi.jpg
```

Untuk mengubah akun lama menjadi Petugas:

```bash
python -m scripts.set_user_role username petugas --nama "Nama Petugas Demo"
```

Untuk akun lama sebagai Pemohon:

```bash
python -m scripts.set_user_role username pemohon
```

Jalankan aplikasi:

```bash
streamlit run app.py
```

## Pemetaan komponen kriptografi

| Kriteria | Penggunaan dalam GOVSAFE |
|---|---|
| USB dongle | Verifikasi token USB akun Pemohon/Petugas yang diprovisikan pengelola. Nama file lama `undergrid.key` dipertahankan agar flashdisk yang sudah terdaftar tetap kompatibel. |
| Argon2id | Hash password akun. |
| Vigenère challenge | Challenge pada tahapan autentikasi tetap dipakai. Tantangan Caesar pada Ringkasan adalah langkah demonstrasi tambahan, bukan faktor keamanan. |
| LSB + ChaCha20-Poly1305 | Metadata internal aset disisipkan ke PNG melalui LSB, lalu hasil PNG dienkripsi dengan ChaCha20-Poly1305. LSB sendiri bukan enkripsi. |
| Vigenère + AES-256-CBC + HMAC-SHA256 | Isi pesan percakapan dienkripsi sebelum disimpan. Saat dekripsi, HMAC diverifikasi lebih dahulu. Kunci AES dan HMAC terpisah. |
| AES-256-GCM + AAD | Field aset dan permohonan yang sensitif dienkripsi dengan AAD sesuai tabel, kolom, dan record. |
| Linked hash SHA-256 | Pencatatan event `ASSET_CREATED`, `ASSET_ARCHIVED`, `INFORMATION_REQUESTED`, `DOCUMENT_REQUESTED`, `REQUEST_CLAIMED`, `MESSAGE_SENT`, dan `REQUEST_STATUS_UPDATED`. |

## Variabel lingkungan

Nama variabel `UNDERGRID_*` dipertahankan agar kunci `.env` yang sudah dibuat tidak berubah dan data lama masih dapat dibaca. Jangan mengganti kunci ketika database dan file terenkripsi lama masih digunakan. Tambahkan `GOVSAFE_ASSET_STORAGE_PATH` secara opsional untuk mengatur folder foto aset terenkripsi; default-nya `storage/govsafe_assets`.

## Batasan keamanan dan demo

- Aplikasi ini merupakan prototipe akademik, bukan sistem resmi pemerintah dan bukan sumber penetapan status hukum barang.
- Challenge Caesar dan kode katalog statis hanya gerbang pembelajaran; keduanya bukan kontrol akses kuat. Kode demonstrasi tersedia dalam berkas panduan yang dapat diunduh setelah tantangan selesai.
- Face recognition yang ada tidak dilengkapi liveness detection dan tidak boleh dianggap sebagai verifikasi biometrik tingkat produksi.
- File dongle dapat disalin; USB bukan hardware security module.
- Ledger lokal bersifat tamper-evident pada level aplikasi, bukan blockchain terdistribusi atau jaminan immutability absolut.
- Gunakan nama, foto, kode aset, lokasi, dan dokumen sintetis untuk demonstrasi. Jangan unggah dokumen perkara atau data pribadi sungguhan ke repository publik.
- Event `PURCHASE_INTENT` dari versi lama mungkin tetap muncul di ledger historis yang sudah ada. Aplikasi GOVSAFE baru tidak membuat event pembelian; riwayat lama tidak dihapus agar integritas hash chain tidak rusak.

## Pengujian

Setelah dependency proyek terpasang dan `.env` terisi:

```bash
python -m compileall -q .
pytest -q
```

Uji visual Streamlit, USB, webcam, dan percakapan dua akun harus dilakukan pada komputer demonstrasi yang memiliki dependency dan perangkat terkait.
