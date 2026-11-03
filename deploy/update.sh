#!/usr/bin/env bash
# Perbarui app alfayed_rental di server: backup, build image, jalankan ulang, migrate.
# Jalankan di server dari folder compose:  bash /path/ke/update.sh
# Variabel yang bisa diubah: COMPOSE_DIR, SITE (bawaan: all), IMAGE, APP_BRANCH.
set -euo pipefail

COMPOSE_DIR="${COMPOSE_DIR:-$HOME/alfayed-erp}"
SITE="${SITE:-all}"  # "all" = semua situs di bench
IMAGE="${IMAGE:-alfayed-erp:16}"
APP_BRANCH="${APP_BRANCH:-main}"
BACKEND="alfayed-erp-backend-1"
COMPOSE=(docker compose
  -f compose.yaml
  -f overrides/compose.mariadb.yaml
  -f overrides/compose.redis.yaml
  -f overrides/compose.tailscale.yaml)

cd "$COMPOSE_DIR"

echo "== 1. Backup situs ($SITE) =="
docker exec "$BACKEND" bench --site "$SITE" backup --with-files

echo "== 2. Simpan image lama untuk rollback =="
docker tag "$IMAGE" "${IMAGE}-sebelum"

echo "== 3. Build image baru =="
mkdir -p build
curl -fsSL "https://raw.githubusercontent.com/mashudizaini/alfayed-trans/${APP_BRANCH}/deploy/Containerfile" -o build/Containerfile
docker build -f build/Containerfile \
  --build-arg APP_BRANCH="$APP_BRANCH" \
  --build-arg CACHEBUST="$(date +%s)" \
  -t "$IMAGE" build

echo "== 4. Jalankan ulang container =="
"${COMPOSE[@]}" up -d

echo "== 5. Migrate =="
docker exec "$BACKEND" bench --site "$SITE" migrate 2>&1 | tail -5

echo "== 6. Versi terpasang =="
docker exec "$BACKEND" bench version

cat <<MSG

Selesai. Bila ada masalah, rollback:
  docker tag ${IMAGE}-sebelum ${IMAGE} && cd $COMPOSE_DIR && ${COMPOSE[*]} up -d
MSG
