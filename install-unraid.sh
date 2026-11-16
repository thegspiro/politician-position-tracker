#!/bin/sh
# Politician Tracker — One-line Unraid installer
# Usage: sh install-unraid.sh
# Or: curl -sSL <raw-github-url>/install-unraid.sh | sh
#
# Pulls the prebuilt image from GitHub Container Registry, so neither git nor a
# local build is needed. Set BUILD_FROM_SOURCE=1 to clone and build instead
# (requires git, and enough RAM for the frontend build).

set -eu

APP_NAME="politician-tracker"
IMAGE="${IMAGE:-ghcr.io/thegspiro/politician-position-tracker:latest}"
DATA_DIR="${DATA_DIR:-/mnt/user/appdata/${APP_NAME}}"
PORT="${PORT:-9847}"
# Unraid appdata is owned by nobody:users.
PUID="${PUID:-99}"
PGID="${PGID:-100}"
BUILD_FROM_SOURCE="${BUILD_FROM_SOURCE:-0}"
# A password is generated when one is not supplied. The application refuses to
# start on a published default, so there is no weak fallback to inherit.
GENERATED_PASSWORD=""
if [ -z "${ADMIN_PASSWORD:-}" ]; then
  GENERATED_PASSWORD="$(head -c 18 /dev/urandom | base64 | tr -d '/+=' | cut -c1-20)"
  ADMIN_PASSWORD="${GENERATED_PASSWORD}"
fi
SECRET_KEY="${SECRET_KEY:-$(head -c 32 /dev/urandom | base64)}"

echo "=== Politician Tracker Installer ==="
echo ""
echo "  Image:           ${IMAGE}"
echo "  Port:            ${PORT}"
echo "  Data directory:  ${DATA_DIR}"
if [ -n "${GENERATED_PASSWORD}" ]; then
  echo "  Admin password:  ${ADMIN_PASSWORD}  (generated - save this now)"
else
  echo "  Admin password:  (supplied via ADMIN_PASSWORD)"
fi
echo ""

if [ "${BUILD_FROM_SOURCE}" = "1" ]; then
  BUILD_DIR="${BUILD_DIR:-${DATA_DIR}/.build}"
  IMAGE="${APP_NAME}:local"
  echo "[1/4] Downloading source and building image..."
  rm -rf "${BUILD_DIR}"
  git clone --depth 1 https://github.com/thegspiro/politician-position-tracker.git "${BUILD_DIR}"
  docker build -t "${IMAGE}" "${BUILD_DIR}"
  rm -rf "${BUILD_DIR}"
else
  echo "[1/4] Pulling image..."
  docker pull "${IMAGE}"
fi

echo "[2/4] Creating data directory..."
mkdir -p "${DATA_DIR}"

echo "[3/4] Removing any previous container..."
docker rm -f "${APP_NAME}" 2>/dev/null || true

echo "[4/4] Starting container..."
docker run -d \
  --name "${APP_NAME}" \
  --restart unless-stopped \
  -p "${PORT}:8000" \
  -v "${DATA_DIR}:/app/data" \
  -e "PUID=${PUID}" \
  -e "PGID=${PGID}" \
  -e "ADMIN_PASSWORD=${ADMIN_PASSWORD}" \
  -e "SECRET_KEY=${SECRET_KEY}" \
  "${IMAGE}"

echo ""
echo "=== Installation complete! ==="
echo "  Access the app at: http://$(hostname -I | awk '{print $1}'):${PORT}"
if [ -n "${GENERATED_PASSWORD}" ]; then
  echo "  Admin password:    ${ADMIN_PASSWORD}"
  echo "  ^ Generated for this install. Save it now; it is not stored anywhere else."
else
  echo "  Admin password:    (the value you supplied)"
fi
echo ""
echo "  To customize, set environment variables before running:"
echo "    PORT=9847 ADMIN_PASSWORD=mypassword sh install-unraid.sh"
