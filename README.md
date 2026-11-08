# GOVSAFE — Government Seized Asset Security & Management System

GOVSAFE adalah aplikasi administrasi aset negara berbasis Streamlit untuk pencatatan informasi barang sitaan, barang rampasan negara, dan barang bukti, pengajuan permohonan informasi/dokumen, serta komunikasi terenkripsi antara Pemohon dan Petugas. Sistem membedakan peran Pemohon dan Petugas, menyediakan katalog aset, dan mencatat aktivitas penting pada audit ledger.

GOVSAFE adalah aplikasi demonstrasi akademik. GOVSAFE **bukan marketplace** dan tidak memiliki transaksi jual beli, pembayaran, saldo, escrow, atau fitur lelang.

## Daftar isi

1. [Peran pengguna](#peran-pengguna)
2. [Alur aplikasi](#alur-aplikasi)
3. [Status hukum dan batasan data](#status-hukum-dan-batasan-data)
4. [Menjalankan aplikasi](#menjalankan-aplikasi)
5. [Migrasi dari UnderGrid (penerapan patch)](#migrasi-dari-undergrid-penerapan-patch)
6. [Manajemen akun](#manajemen-akun)
7. [Sumber kebenaran metadata](#sumber-kebenaran-metadata)
8. [Format interoperabilitas steganografi LSB](#format-interoperabilitas-steganografi-lsb)
9. [Pemetaan komponen kriptografi](#pemetaan-komponen-kriptografi)
10. [Variabel lingkungan](#variabel-lingkungan)
11. [Batasan keamanan dan demo](#batasan-keamanan-dan-demo)
12. [Pengujian](#pengujian)

## Peran pengguna

| Peran | Hak akses utama |
|---|---|
| **Pemohon** | Melihat katalog aset yang aktif dan informasinya sesuai tingkat akses; mengajukan permohonan informasi/dokumen; membaca dan mengirim pesan pada permohonan miliknya. |
| **Petugas** | Mendaftarkan, mengedit, dan mengarsipkan aset; melihat detail internal termasuk lokasi penyimpanan; mengambil permohonan; memperbarui status; membalas pesan Pemohon. |
| **Pengelola sistem** | Menyiapkan akun melalui CLI, mengatur kunci, dan mengelola instalasi. Tidak ada registrasi publik atau halaman admin umum. |

## Alur aplikasi

1. Pengguna melewati autentikasi berlapis: USB dongle, pengenalan wajah, password Argon2id, dan challenge Vigenère.
2. Pemohon menyelesaikan tantangan Caesar demonstratif pada Ringkasan sebelum membuka Katalog Aset.
3. Pemohon memilih aset dan mengajukan `Permohonan Informasi` atau `Permohonan Dokumen`.
4. Petugas mengambil permohonan. Status berubah menjadi `Diproses`; kemudian Petugas dan Pemohon dapat berkomunikasi dalam percakapan yang terkait dengan nomor permohonan.
5. Petugas memperbarui status menjadi `Dijawab` atau `Ditutup` sesuai hasil penanganan.
6. Aktivitas penting dicatat pada audit ledger linked-hash SHA-256. Payload ledger hanya memuat metadata ID/status; plaintext pesan dan informasi rahasia tidak dimasukkan ke ledger.

Menu **Lab Kriptografi** menampilkan tahapan demonstrasi algoritma beserta parameter publik, tanpa menampilkan nilai kunci rahasia.

## Status hukum dan batasan data

`Barang sitaan` dan `Barang rampasan negara` adalah kategori status hukum yang berbeda. Pencatatan pada GOVSAFE tidak dengan sendirinya membuktikan bahwa barang dapat dialihkan, dijual, dilelang, atau digunakan. Penetapan status dan kewenangan akses tetap mengikuti dokumen serta keputusan pejabat/instansi yang berwenang. Data pada aplikasi demo sebaiknya fiktif atau telah dianonimkan.

Lokasi penyimpanan memiliki tingkat akses `Terbatas` atau `Publik`. Lokasi berstatus Terbatas tidak ditampilkan pada akun Pemohon. Isi deskripsi, nama, kondisi, lokasi, dan path foto disimpan terenkripsi menggunakan AES-256-GCM dengan AAD yang mengikat tabel, kolom, dan ID record.

## Menjalankan aplikasi

Langkah ini untuk instalasi baru.

1. Siapkan Python dan pasang dependensi:

   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Siapkan konfigurasi kunci pada file lingkungan lokal (`.env`) sesuai nama variabel yang digunakan oleh modul pada folder `crypto/`. Jangan mengunggah `.env`, kunci, database lokal, atau data pribadi ke repositori.

3. Buat kunci, inisialisasi database, lalu jalankan aplikasi:

   ```powershell
   python -m scripts.generate_keys
   python -m scripts.init_db
   python -m streamlit run app.py
   ```

   Aplikasi juga dapat dijalankan dengan `streamlit run app.py`.

4. Buat akun dan daftarkan perangkat autentikasi (lihat [Manajemen akun](#manajemen-akun)).

## Migrasi dari UnderGrid (penerapan patch)

Bagian ini hanya untuk proyek yang sudah berjalan sebagai UnderGrid. Patch ditujukan untuk branch `Trial` dari repository ProjectCrypto-UnderGrid.

1. Ekstrak isi ZIP patch ke folder root proyek dan izinkan berkas dengan nama sama ditimpa. Patch **tidak** menyertakan `.env`, database, folder virtual environment, foto biometrik, maupun data akun.

2. Jalankan sekali untuk menyesuaikan istilah yang masih tertulis Buyer pada halaman login lama:

   ```bash
   python -m scripts.migrate_login_labels
   ```

3. Migrasikan skema database dan pertahankan data lama:

   ```bash
   python -m scripts.init_db
   ```

   Perintah ini menambahkan kolom peran ke tabel akun serta membuat tabel `govsafe_assets`, `govsafe_requests`, dan `govsafe_messages`. Tabel lama tidak dihapus.

Yang perlu diketahui saat migrasi:

- Akun lama UnderGrid dimigrasikan otomatis menjadi `pemohon`. Untuk akun lama yang harus menjadi Petugas, gunakan `scripts/set_user_role.py`.
- Baris pada tabel `products` versi UnderGrid tidak otomatis dipindahkan ke tabel aset GOVSAFE karena data lama tidak memiliki atribut status hukum dan lokasi penyimpanan. Daftarkan ulang sebagai data aset yang telah diverifikasi oleh Petugas.
- Data pesan lama tidak dipindahkan ke percakapan GOVSAFE.

## Manajemen akun

Buat akun baru melalui CLI. Saat diminta, pilih `pemohon` atau `petugas`:

```bash
python -m scripts.create_buyer
```

Daftarkan USB dongle dan template wajah menggunakan username yang sama:

```bash
python -m scripts.generate_dongle username E:\
python -m scripts.enroll_face username path/foto_referensi.jpg
```

Ubah peran akun yang sudah ada:

```bash
# Menjadi Petugas
python -m scripts.set_user_role username petugas --nama "Nama Petugas Demo"

# Menjadi Pemohon
python -m scripts.set_user_role username pemohon
```

## Sumber kebenaran metadata

Metadata katalog terkini berada di database GOVSAFE. Petugas dapat mengedit nama, kategori, status hukum, kondisi, deskripsi, lokasi, dan tingkat akses. Pengeditan tersebut memperbarui kolom database terenkripsi dan catatan audit, tetapi **tidak mengubah gambar atau menulis ulang payload LSB**.

Metadata di dalam PNG merupakan snapshot pada saat aset pertama kali didaftarkan. Karena itu, snapshot dapat berbeda dari data katalog terkini setelah dilakukan pengeditan. Untuk informasi terbaru, gunakan katalog aplikasi.

## Format interoperabilitas steganografi LSB

GOVSAFE menggunakan LSB saja untuk penyisipan metadata. Foto keluaran disimpan sebagai PNG RGB **tanpa enkripsi file** agar dapat dibaca oleh decoder eksternal yang mengikuti format berikut.

- Citra: PNG, dikonversi ke RGB 8-bit.
- Pemindaian: urutan piksel baris demi baris (row-major), kanal R lalu G lalu B.
- Penyisipan: satu bit paling rendah (least significant bit) dari setiap nilai kanal.
- Urutan bit: most-significant-bit first untuk setiap byte.
- Header tetap 41 byte: `UGLS` (4 byte) + versi (1 byte, saat ini `0x01`) + panjang payload (4 byte, unsigned big-endian) + SHA-256 payload (32 byte).
- Payload: JSON UTF-8, serialisasi kompak dengan kunci terurut.
- Kapasitas payload maksimum: `floor(width × height × 3 / 8) − 41` byte.

Decoder harus mengekstrak total 328 bit pertama sebagai header, membaca panjang payload dari byte 5–8 (indeks berbasis nol), kemudian mengekstrak payload sebanyak panjang tersebut. SHA-256 dihitung ulang dan dibandingkan dengan digest pada header sebelum metadata dinyatakan valid. Jangan mengubah ukuran, mengompresi ulang, atau mengonversi PNG ke JPEG karena operasi tersebut dapat merusak bit LSB.

**File format lama.** File yang memiliki header `UGFILE` merupakan format file terenkripsi ChaCha20-Poly1305 dari versi sebelumnya. Format tersebut harus didekripsi lebih dahulu dengan kunci file yang sesuai sebelum decoder LSB digunakan. File PNG baru tidak memerlukan tahap dekripsi file.

## Pemetaan komponen kriptografi

| Kriteria | Penggunaan dalam GOVSAFE |
|---|---|
| USB dongle | Verifikasi token USB akun Pemohon/Petugas yang diprovisikan pengelola. Nama file lama `undergrid.key` dipertahankan agar flashdisk yang sudah terdaftar tetap kompatibel. |
| Argon2id | Hash password akun. Merupakan hashing satu arah, bukan enkripsi, dan tidak dapat didekripsi. |
| Vigenère challenge | Challenge pada tahapan autentikasi. Tantangan Caesar pada Ringkasan adalah langkah demonstrasi tambahan, bukan faktor keamanan. |
| Steganografi LSB | Metadata aset disisipkan ke PNG pada saat pendaftaran (lihat format di atas). LSB sendiri bukan algoritma enkripsi. |
| ChaCha20-Poly1305 | Tersedia sebagai utilitas enkripsi file terpisah dan dipakai pada file format lama (`UGFILE`). Jalur foto aset baru tidak memakainya agar PNG LSB tetap dapat didekode secara langsung. |
| Vigenère + AES-256-CBC + HMAC-SHA256 | Isi pesan percakapan: Vigenère → padding PKCS7 → AES-256-CBC → HMAC-SHA256 (Encrypt-then-MAC). Saat dekripsi, HMAC diverifikasi lebih dahulu. Kunci AES dan HMAC terpisah. |
| AES-256-GCM + AAD | Field aset dan permohonan yang sensitif dienkripsi dengan nonce acak dan AAD yang mengikat tabel, kolom, serta ID record. |
| Linked hash SHA-256 | Pencatatan event `ASSET_CREATED`, `ASSET_ARCHIVED`, `INFORMATION_REQUESTED`, `DOCUMENT_REQUESTED`, `REQUEST_CLAIMED`, `MESSAGE_SENT`, dan `REQUEST_STATUS_UPDATED`. |

## Variabel lingkungan

Nama variabel `UNDERGRID_*` dipertahankan agar kunci `.env` yang sudah dibuat tidak berubah dan data lama masih dapat dibaca. Jangan mengganti kunci ketika database dan file terenkripsi lama masih digunakan.

Tambahkan `GOVSAFE_ASSET_STORAGE_PATH` secara opsional untuk mengatur folder penyimpanan foto aset; default-nya `storage/govsafe_assets`.

## Batasan keamanan dan demo

- Aplikasi ini merupakan prototipe akademik, bukan sistem resmi pemerintah dan bukan sumber penetapan status hukum barang.
- Challenge Caesar dan kode katalog statis hanya gerbang pembelajaran; keduanya bukan kontrol akses kuat. Kode demonstrasi tersedia dalam berkas panduan yang dapat diunduh setelah tantangan selesai.
- Face recognition yang ada tidak dilengkapi liveness detection dan tidak boleh dianggap sebagai verifikasi biometrik tingkat produksi.
- File dongle dapat disalin; USB bukan hardware security module.
- Ledger lokal bersifat tamper-evident pada level aplikasi, bukan blockchain terdistribusi atau jaminan immutability absolut.
- PNG hasil LSB tidak dienkripsi pada level file, sehingga siapa pun yang mengetahui formatnya dapat membaca snapshot metadata di dalamnya. Jangan menyisipkan informasi yang tidak boleh dibaca pihak lain.
- Gunakan nama, foto, kode aset, lokasi, dan dokumen sintetis untuk demonstrasi. Jangan unggah dokumen perkara atau data pribadi sungguhan ke repository publik.
- Event `PURCHASE_INTENT` dari versi lama mungkin tetap muncul di ledger historis yang sudah ada. Aplikasi GOVSAFE baru tidak membuat event pembelian; riwayat lama tidak dihapus agar integritas hash chain tidak rusak.

## Pengujian

Setelah dependency proyek terpasang dan `.env` terisi:

```bash
python -m compileall -q .
python -m pytest -q
```

Uji visual Streamlit, USB, webcam, dan percakapan dua akun harus dilakukan pada komputer demonstrasi yang memiliki dependency dan perangkat terkait.
