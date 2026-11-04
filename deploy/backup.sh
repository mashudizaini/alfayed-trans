#!/usr/bin/env bash
# Backup harian semua situs ERPNext Alfayed: database, file publik/privat, dan site_config.
# 1. bench backup --with-files per situs ke folder sementara di dalam container
# 2. disalin ke $BACKUP_DIR/<tanggal>/<situs>/ di server, lalu folder sementara dihapus
# 3. bila rclone dan remote $RCLONE_REMOTE ada: disalin ke luar server (misalnya Google Drive)
# 4. retensi: lokal $SIMPAN_LOKAL hari, remote $SIMPAN_REMOTE hari
#
# Pasang di cron (jam 01:30 setiap hari):
#   30 1 * * * $HOME/alfayed-erp/backup.sh >> $HOME/backups/backup.log 2>&1
set -euo pipefail

BACKEND="${BACKEND:-alfayed-erp-backend-1}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups}"
RCLONE_REMOTE="${RCLONE_REMOTE:-gdrive-crypt:alfayed-erp}"
SIMPAN_LOKAL="${SIMPAN_LOKAL:-14}"
SIMPAN_REMOTE="${SIMPAN_REMOTE:-60}"
BENCH=/home/frappe/frappe-bench
TMP="$BENCH/sites/.backup-harian"
TANGGAL="$(date +%Y-%m-%d_%H%M)"
TUJUAN="$BACKUP_DIR/$TANGGAL"

echo "== $(date '+%F %T') mulai backup ke $TUJUAN"
mkdir -p "$TUJUAN"
SITUS=$(docker exec "$BACKEND" bash -c "cd $BENCH/sites && for d in */; do [ -f \"\$d/site_config.json\" ] && echo \"\${d%/}\"; done")
GAGAL=0
for s in $SITUS; do
  echo "-- $s"
  if docker exec "$BACKEND" bash -c "rm -rf $TMP/$s && mkdir -p $TMP/$s && cd $BENCH && bench --site $s backup --with-files --compress --backup-path $TMP/$s" > /dev/null; then
    docker cp "$BACKEND:$TMP/$s" "$TUJUAN/" && ls -1 "$TUJUAN/$s" | sed 's/^/   /'
  else
    echo "   [GAGAL] backup $s"; GAGAL=1
  fi
done
docker exec "$BACKEND" rm -rf "$TMP"
chmod -R go-rwx "$BACKUP_DIR"

# Retensi lokal.
find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -mtime +"$SIMPAN_LOKAL" -print -exec rm -rf {} +

# Salinan di luar server.
if command -v rclone > /dev/null && rclone listremotes | grep -q "^${RCLONE_REMOTE%%:*}:"; then
  rclone copy "$TUJUAN" "$RCLONE_REMOTE/$TANGGAL" --transfers 2 && echo "== disalin ke $RCLONE_REMOTE/$TANGGAL"
  rclone delete "$RCLONE_REMOTE" --min-age "${SIMPAN_REMOTE}d" --rmdirs || true
else
  echo "== [PERINGATAN] rclone/remote $RCLONE_REMOTE belum ada: backup hanya tersimpan di server ini"
  GAGAL=1
fi
echo "== $(date '+%F %T') selesai (status $GAGAL)"
exit $GAGAL
