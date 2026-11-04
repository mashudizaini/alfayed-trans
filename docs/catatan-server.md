# Catatan Server Alfayed ERP

Log perubahan konfigurasi server development/on-premise. **Tanpa kata sandi, token, alamat IP,
atau nama pengguna**: repositori ini publik. Simpan detail akses di catatan lokal.

## Ringkasan lingkungan (per 2026-11-03)

| Komponen | Nilai |
| --- | --- |
| OS | Ubuntu 24.04.4 LTS, x86_64 |
| Sumber daya | 4 CPU, RAM 5,8 GiB (+ swap 4 GiB), disk root 58 GB |
| Docker / Compose | Docker 29.9.2, Compose v5.6.1 |
| Akses | Hanya lewat Tailscale; ERPNext di port 8080 yang di-bind ke alamat Tailscale server |
| Folder compose | `~/alfayed-erp` (`compose.yaml` + `overrides/compose.mariadb.yaml`, `compose.redis.yaml`, `compose.tailscale.yaml`) |
| Project compose | `alfayed-erp` (container `alfayed-erp-*-1`) |
| Situs | `erp.alfayedtrans.com` (data uji, rancangan lama; akan dihapus), `rental.aimz.my.id`, `pos.aimz.my.id` (rancangan 3 situs, lihat Panduan Domain dan Cloudflare) |
| Versi | Frappe 16.54.0, ERPNext 16.53.0, alfayed_rental 0.0.1 |
| Image | `alfayed-erp:16`, dibangun dari `deploy/Containerfile` (dasar `frappe/erpnext:v16.53.0`; memuat `alfayed_rental` dan `alfayed_pos`) |
| Database / Redis | MariaDB 11.8, Redis 8.6 (alpine) |

## Cara memperbarui app

Setelah perubahan di-push ke `main`, jalankan di server:

```bash
curl -fsSL https://raw.githubusercontent.com/mashudizaini/alfayed-trans/main/deploy/update.sh | bash
```

Skrip `deploy/update.sh` melakukan (untuk semua situs; batasi dengan `SITE=nama.situs`): backup, menyimpan image lama sebagai `alfayed-erp:16-sebelum`,
build image baru, `docker compose up -d`, `bench migrate`, lalu menampilkan versi terpasang.

Rollback bila ada masalah:

```bash
docker tag alfayed-erp:16-sebelum alfayed-erp:16
cd ~/alfayed-erp && docker compose -f compose.yaml -f overrides/compose.mariadb.yaml \
  -f overrides/compose.redis.yaml -f overrides/compose.tailscale.yaml up -d
```

Catatan: rollback image tidak membatalkan migrasi database. Bila migrasi mengubah skema,
pulihkan juga dari backup (`bench --site erp.alfayedtrans.com restore ...`).

## Log perubahan

### 2026-11-03

- Kondisi awal: ERPNext v16 sudah berjalan dengan image `alfayed-erp:16` (dibangun di luar server),
  `alfayed_rental` sudah terpasang di site dari commit `66516b4`.
- Backup site lengkap (`backup --with-files`) sebelum perubahan; file masih di volume `sites`
  (`erp.alfayedtrans.com/private/backups/`), **belum disalin ke luar server**.
- Branch `perbaikan-integrasi-erpnext` digabung ke `main` (commit `644e3f5`): `required_apps`,
  customer tidak ganda, invoice dibatalkan saat reservasi Batal.
- Image lama disimpan sebagai `alfayed-erp:16-sebelum`.
- Image baru dibangun di server dari `~/alfayed-erp/build/Containerfile` (isi sama dengan `deploy/Containerfile`),
  container dijalankan ulang, `migrate` sukses. Terverifikasi: `alfayed_rental 0.0.1 main (644e3f5)`.
- Deploy key read-only dibuat di server (`~/.ssh/alfayed_deploy`) tetapi belum dipasang di GitHub,
  karena repositori sekarang publik.

### 2026-11-03 (lanjutan)

- Keputusan: ikuti rancangan tiga situs. Dibuat situs `rental.aimz.my.id` (erpnext + alfayed_rental)
  dan `pos.aimz.my.id` (erpnext). `hotel.aimz.my.id` menunggu nama Company.
- `erp.alfayedtrans.com` hanya berisi data uji; dihapus setelah dua situs baru terverifikasi.
- `deploy/update.sh` kini mem-backup dan me-migrate semua situs (`--site all`).

### 2026-11-04

- App: peran `Staf Rental`, profil modul `Staf Rental` dan `Keuangan` (dibuat otomatis saat migrate),
  workspace/sidebar/dock **Rental** (`/desk/rental`), 4 number card, Kalender Reservasi, Script Report
  **Laporan Reservasi**. Hak akses: staf rental mengelola reservasi dan denda; keuangan (Accounts User)
  mencatat pembayaran dan deposit, hanya membaca data rental.
- User operasional situs rental dibuat dengan:
  `bench --site rental.aimz.my.id execute alfayed_rental.alfayed_rental.pengguna.buat_user_operasional --kwargs "{...}"`
  lalu kata sandi diatur dengan `bench --site rental.aimz.my.id set-password <email>`.

- Laporan Pendapatan Rental (per bulan, per kelompok/model/kendaraan) dan Utilisasi Kendaraan.
- Akses publik lewat Cloudflare Tunnel: `deploy/compose.cloudflared.yaml` disalin ke `overrides/`,
  `TUNNEL_TOKEN` di `.env` (tidak di Git); `update.sh` ikut memuatnya bila file ada.
  Hostname: `rental.aimz.my.id`, `pos.aimz.my.id` -> `http://frontend:8080`.

- App kedua `alfayed_pos` (repo `mashudizaini/alfayed_pos`) ikut dibangun ke image dan dipasang hanya
  di situs pos: peran Kasir dan Kepala Toko, beranda Toko (`/desk/toko`), QRIS, POS Profile Toko A/B/C,
  laporan Penjualan Harian per Toko, Stok per Toko, Barang Terlaris. Hak tambahan untuk doctype ERPNext
  disimpan sebagai Custom DocPerm (tidak mengubah core); setelah upgrade ERPNext, periksa ulang izinnya.

- App ketiga `alfayed_hotel` (repo `mashudizaini/alfayed_hotel`) untuk situs `hotel.aimz.my.id`
  (Company Alfayed Hotel): hotel, penginapan, homestay, villa (per malam) serta kost dan kontrakan
  (Kontrak Sewa dengan tagihan otomatis harian). Hostname `hotel` ditambahkan ke tunnel.

## Backup

- `deploy/backup.sh` (disalin ke `~/alfayed-erp/backup.sh`) dijalankan cron setiap hari 01:30: backup semua situs
  (`--with-files --compress`) ke `~/backups/<tanggal>/<situs>/`, retensi lokal 14 hari, lalu `rclone copy` ke remote
  terenkripsi `gdrive-crypt:alfayed-erp` (Google Drive), retensi 60 hari. Log: `~/backups/backup.log`.
- Kata sandi enkripsi rclone crypt disimpan di pengelola kata sandi pemilik; tanpa itu salinan di Drive tidak bisa dibuka.
- Backup memuat `site_config` (berisi `encryption_key` situs) yang dibutuhkan untuk memulihkan kata sandi tersimpan.
- Uji restore: `deploy/uji_restore.sh <situs>` memulihkan backup terbaru ke `uji-restore.local`, membandingkan jumlah
  dokumen, lalu menghapus situs uji.

## Pekerjaan terbuka

- Ganti kata sandi SSH server, pasang kunci SSH, matikan `PasswordAuthentication`.
- Uji app end to end (seed, alur reservasi, deposit, denda, API) dan tes otomatis.
