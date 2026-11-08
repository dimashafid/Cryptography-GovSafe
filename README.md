# GOVSAFE — Government Asset Security & Verification

GOVSAFE adalah aplikasi administrasi aset negara berbasis Streamlit. Sistem membedakan peran Pemohon dan Petugas, menyediakan katalog aset, permohonan informasi, pesan terenkripsi, serta pencatatan audit berbasis ledger.

## Menjalankan aplikasi

1. Siapkan Python dan pasang dependensi:

   ~~~powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ~~~

2. Siapkan konfigurasi kunci pada file lingkungan lokal sesuai nama variabel yang digunakan oleh modul pada folder crypto/. Jangan mengunggah .env, kunci, database lokal, atau data pribadi ke repositori.

3. Inisialisasi database dan jalankan aplikasi:

   ~~~powershell
   python -m scripts.generate_keys
   python -m scripts.init_db
   python -m streamlit run app.py
   ~~~

4. Jalankan pengujian:

   ~~~powershell
   python -m pytest -q
   ~~~

## Sumber kebenaran metadata

Metadata katalog terkini berada di database GOVSAFE. Petugas dapat mengedit nama, kategori, status hukum, kondisi, deskripsi, lokasi, dan tingkat akses. Pengeditan tersebut memperbarui kolom database terenkripsi dan catatan audit, tetapi **tidak mengubah gambar atau menulis ulang payload LSB**.

Metadata di dalam PNG merupakan snapshot pada saat aset pertama kali didaftarkan. Karena itu, snapshot dapat berbeda dari data katalog terkini setelah dilakukan pengeditan. Untuk informasi terbaru, gunakan katalog aplikasi.

## Format interoperabilitas steganografi LSB GOVSAFE

GOVSAFE menggunakan LSB saja untuk penyisipan metadata. Foto keluaran disimpan sebagai PNG RGB tanpa enkripsi file agar dapat dibaca oleh decoder eksternal yang mengikuti format berikut.

- Citra: PNG, dikonversi ke RGB 8-bit.
- Pemindaian: urutan piksel baris demi baris (row-major), kanal R lalu G lalu B.
- Penyisipan: satu bit paling rendah (least significant bit) dari setiap nilai kanal.
- Urutan bit: most-significant-bit first untuk setiap byte.
- Header tetap 41 byte: UGLS (4 byte) + versi (1 byte, saat ini 0x01) + panjang payload (4 byte, unsigned big-endian) + SHA-256 payload (32 byte).
- Payload: JSON UTF-8, serialisasi kompak dengan kunci terurut.
- Kapasitas payload maksimum: floor(width × height × 3 / 8) − 41 byte.

Decoder harus mengekstrak total 328 bit pertama sebagai header, membaca panjang payload dari byte 5–8 (indeks berbasis nol), kemudian mengekstrak payload sebanyak panjang tersebut. SHA-256 dihitung ulang dan dibandingkan dengan digest pada header sebelum metadata dinyatakan valid. Jangan mengubah ukuran, mengompresi ulang, atau mengonversi PNG ke JPEG karena operasi tersebut dapat merusak bit LSB.

File lama yang memiliki header UGFILE merupakan format file terenkripsi ChaCha20-Poly1305. Format tersebut harus didekripsi lebih dahulu dengan kunci file yang sesuai sebelum decoder LSB digunakan. File PNG baru tidak memerlukan tahap dekripsi file.

## Ringkasan kriptografi

- Pesan permohonan: Vigenère → padding PKCS7 → AES-256-CBC → HMAC-SHA256 (Encrypt-then-MAC).
- Metadata database: AES-256-GCM dengan nonce acak dan AAD terikat pada tabel, kolom, serta ID record.
- Enkripsi file: ChaCha20-Poly1305 tersedia sebagai utilitas terpisah. Jalur foto aset baru tidak memakainya agar PNG LSB tetap dapat didekode secara langsung.
- Password: Argon2id untuk hashing satu arah; bukan enkripsi dan tidak dapat didekripsi.
- Steganografi: LSB untuk penyisipan metadata; bukan algoritma enkripsi.

Menu Lab Kriptografi menampilkan tahapan demonstrasi algoritma beserta parameter publik, tanpa menampilkan nilai kunci rahasia.
