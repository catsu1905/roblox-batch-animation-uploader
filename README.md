# Roblox Batch Animation Uploader

Upload banyak file animasi (`.rbxm`) ke Roblox **sekaligus**, tanpa save satu-satu di Studio.
Hasilnya langsung jadi daftar `rbxassetid://...` dan script Studio yang otomatis bikin semua `Animation`.

> Kenapa bukan plugin? Studio memblokir `HttpService` ke domain Roblox, jadi plugin tidak bisa memanggil
> Open Cloud. Tool ini jalan di luar Studio dan memakai API resmi **Open Cloud Assets API**.

## Cara pakai (Windows)

1. Buka tab **Releases** di repo ini, download `BatchAnimationUploader.exe`.
2. Siapkan **API key** (lihat bawah).
3. Klik dua kali `.exe`, **drag folder** berisi file `.rbxm` ke jendelanya, lalu Enter.
4. Pilih upload ke akun sendiri (User ID) atau Group (Group ID), paste API key, selesai.

> Windows SmartScreen mungkin memperingatkan karena `.exe` ini tidak bertanda tangan digital.
> Kalau ragu, jalankan versi Python di bawah. Semua kodenya terbuka di repo ini.

Hasil ditulis ke folder animasi kamu:

| File | Isi |
| --- | --- |
| `results.txt` | `nama = rbxassetid://ID` per baris |
| `results.lua` | Paste ke **Command Bar** Studio untuk bikin semua `Animation` di `ReplicatedStorage.UploadedAnimations` |
| `results.json` | Data lengkap. Kalau tool dijalankan ulang, file yang sudah berhasil di-skip |

## Cara bikin API key

1. Buka <https://create.roblox.com/dashboard/credentials> dan klik **Create API Key**.
   Untuk upload ke group, buat key dari halaman credentials milik group itu.
2. Di **Access Permissions** pilih **Assets API**, tambahkan operasi **Read** dan **Write**.
3. Di **Accepted IP Addresses** isi `0.0.0.0/0` (atau IP kamu sendiri).
4. Simpan key. Kasih tanggal expire kalau mau lebih aman.

**Jangan pernah membagikan API key kamu.** Tiap orang bikin key sendiri. Tool ini tidak mengirim key ke mana pun
selain ke `apis.roblox.com`. Key hanya disimpan di komputer kamu kalau kamu menjawab "y" saat ditanya.

## Pakai versi Python

```bash
pip install -r requirements.txt
python upload_animations.py "C:\path\ke\folder" --user 123456
python upload_animations.py "C:\path\ke\folder" --group 987654
```

API key dibaca dari environment variable `ROBLOX_API_KEY`, atau diketik saat diminta.

## Catatan

- Animasi dimiliki User/Group yang kamu pilih. Animasi hanya bisa dipakai di game milik pemilik yang sama.
- Satu request = satu aset, maksimal 20 MB per file.
- File `.rbxm` sebaiknya hasil save dari Studio. File yang diedit di luar Studio bisa gagal upload.
- Dukungan `.rbxmx` belum stabil di API Roblox, pakai `.rbxm` kalau bisa.

## Build `.exe` sendiri

Push tag versi (misalnya `v1.0.0`). GitHub Actions otomatis build `.exe` Windows dan menempelkannya ke Release.

```bash
git tag v1.0.0
git push origin v1.0.0
```

## Lisensi

MIT
