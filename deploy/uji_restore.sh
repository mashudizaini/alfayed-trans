#!/usr/bin/env bash
# Uji restore: pulihkan backup terbaru satu situs ke situs sementara, bandingkan jumlah data, lalu hapus.
# Situs asli tidak disentuh. Pakai:  bash uji_restore.sh rental.aimz.my.id
set -euo pipefail

SITUS="${1:?Pakai: uji_restore.sh <nama situs>, misalnya rental.aimz.my.id}"
BACKEND="${BACKEND:-alfayed-erp-backend-1}"
DB="${DB:-alfayed-erp-db-1}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups}"
UJI="uji-restore.local"
BENCH=/home/frappe/frappe-bench

TERBARU=$(ls -1d "$BACKUP_DIR"/*/"$SITUS" 2>/dev/null | sort | tail -1)
[ -n "$TERBARU" ] || { echo "Belum ada backup $SITUS di $BACKUP_DIR"; exit 1; }
SQL=$(ls -1 "$TERBARU"/*-database.sql.gz | head -1)
PUB=$(ls -1 "$TERBARU"/*-files.tgz "$TERBARU"/*-files.tar 2>/dev/null | grep -v private | head -1 || true)
PRIV=$(ls -1 "$TERBARU"/*-private-files.tgz "$TERBARU"/*-private-files.tar 2>/dev/null | head -1 || true)
echo "Backup: $TERBARU"

DBPW=$(docker inspect "$DB" --format '{{range .Config.Env}}{{println .}}{{end}}' | sed -n -E 's/^(MYSQL|MARIADB)_ROOT_PASSWORD=//p' | head -1)
docker exec "$BACKEND" mkdir -p /tmp/uji
docker cp "$TERBARU/." "$BACKEND:/tmp/uji/"
ARG=""
[ -n "$PUB" ] && ARG="$ARG --with-public-files /tmp/uji/$(basename "$PUB")"
[ -n "$PRIV" ] && ARG="$ARG --with-private-files /tmp/uji/$(basename "$PRIV")"

echo "== restore ke situs sementara $UJI"
docker exec "$BACKEND" bash -c "cd $BENCH && bench --site $UJI restore /tmp/uji/$(basename "$SQL") $ARG --db-root-password '$DBPW' --admin-password \"\$(python3 -c 'import secrets; print(secrets.token_hex(12))')\" --force" > /dev/null

echo "== perbandingan jumlah dokumen (asli vs hasil restore)"
hitung() {
  for d in "Sales Invoice" "Payment Entry" "Journal Entry" "Customer" "Item" \
           "Reservasi Rental" "Reservasi Akomodasi" "Kontrak Sewa"; do
    n=$(docker exec "$BACKEND" bash -c "cd $BENCH && bench --site $1 execute frappe.db.count --args \"['$d']\"" 2>/dev/null | tail -1 || true)
    case "$n" in ''|*[!0-9]*) n="-" ;; esac
    printf '%s=%s ' "$d" "$n"
  done
}
ASLI=$(hitung "$SITUS")
HASIL=$(hitung "$UJI")
echo "asli   : $ASLI"
echo "restore: $HASIL"

echo "== hapus situs sementara"
docker exec "$BACKEND" bash -c "cd $BENCH && bench drop-site $UJI --db-root-password '$DBPW' --no-backup --force" > /dev/null
docker exec "$BACKEND" rm -rf /tmp/uji
if [ "$ASLI" = "$HASIL" ]; then
  echo "HASIL: restore BERHASIL, jumlah data sama."
else
  echo "HASIL: jumlah berbeda (wajar bila ada transaksi baru sejak backup). Periksa angka di atas."
fi
