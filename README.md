# Roblox Batch Animation Uploader

Upload banyak file animasi (`.rbxm`) ke Roblox **sekaligus**, tanpa save satu-satu di Studio.
Drag semua file ke jendela browser, klik upload, lalu paste script hasilnya ke Studio.

*English: drag many `.rbxm` animation files into a local web page and upload them all to Roblox
through the Open Cloud Assets API. Windows `.exe` available, or run the single Python file.*

## Cara pakai (Windows)

1. Download **[BatchAnimationUploader.exe](https://github.com/catsu1905/roblox-batch-animation-uploader/releases/latest/download/BatchAnimationUploader.exe)** dari halaman Releases.
2. Klik dua kali. Jendela hitam terbuka dan browser langsung menampilkan halaman uploader.
   Biarkan jendela hitam tetap terbuka selama dipakai.
3. Isi **API key** (cara bikinnya di bawah), pilih **User** atau **Group**, isi ID-nya.
4. Drop semua file `.rbxm` ke kotak File, lalu klik **Upload semua**.
5. Setelah selesai, klik **Copy script**, lalu paste ke **Command Bar** Studio (View → Command Bar) dan Enter.
   Semua `Animation` otomatis dibuat di `ReplicatedStorage.UploadedAnimations`, namanya sesuai nama file.

> Windows SmartScreen atau antivirus bisa memperingatkan karena `.exe` ini tidak bertanda tangan digital.
> Klik **More info → Run anyway**. Kalau ragu, pakai versi Python di bawah, kodenya satu file dan terbuka.

## Cara bikin API key

1. Buka <https://create.roblox.com/dashboard/credentials> lalu klik **Create API Key**.
   Untuk upload ke group, buat key dari halaman credentials milik group itu.
2. Di **Access Permissions** pilih **Assets API**, tambahkan operasi **Read** dan **Write**.
3. Di **Accepted IP Addresses** isi `0.0.0.0/0` (atau IP kamu sendiri).
4. Simpan key. Kasih tanggal expire kalau mau lebih aman.

**Jangan membagikan API key kamu.** Tiap orang bikin key sendiri.

## Keamanan

- Server jalan **hanya di komputer kamu** (`127.0.0.1`) dan menolak akses dari host lain.
- API key cuma dikirim ke `apis.roblox.com`. Tool ini tidak menyimpan apa pun ke disk.
- Kalau kamu centang **Ingat config di browser ini**, key disimpan sebagai teks biasa di `localStorage`
  browser kamu. Jangan centang di komputer bersama.

## Pakai versi Python

Butuh Python 3.8+, tanpa library tambahan.

```bash
python BatchAnimationUploader.py
```

Browser terbuka otomatis di `http://127.0.0.1:8765`. Tambahkan `--no-browser` kalau tidak mau browser dibuka.

## Catatan

- Animasi dimiliki User/Group yang kamu pilih, dan hanya bisa dipakai di game milik pemilik yang sama.
- Satu request = satu aset, maksimal 20 MB per file. Tool upload satu per satu dan otomatis menunggu kalau kena rate limit.
- File yang gagal bisa diulang: klik **Upload semua** lagi, yang sudah berhasil tidak diupload ulang.
- File `.rbxm` sebaiknya hasil save dari Studio. File yang diedit di luar Studio bisa gagal upload.
- Dukungan `.rbxmx` belum stabil di API Roblox, pakai `.rbxm` kalau bisa.
- Kenapa bukan plugin Studio? Studio memblokir `HttpService` ke domain Roblox, jadi plugin tidak bisa memanggil Open Cloud.

## Build otomatis

Tiap kali kode di `main` berubah, GitHub Actions membangun `.exe` Windows dan menerbitkannya sebagai Release baru.

## Lisensi

MIT
