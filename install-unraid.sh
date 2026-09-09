#!/bin/bash
# Politician Tracker — One-line Unraid installer
# Usage: bash install-unraid.sh
# Or: curl -sSL <raw-github-url>/install-unraid.sh | bash

set -e

APP_NAME="politician-tracker"
DATA_DIR="/mnt/user/appdata/${APP_NAME}"
PORT="${PORT:-9847}"
# A password is generated when one is not supplied. The application refuses to
# start on a published default, so there is no weak fallback to inherit.
GENERATED_PASSWORD=""
if [ -z "${ADMIN_PASSWORD:-}" ]; then
  GENERATED_PASSWORD="$(head -c 18 /dev/urandom | base64 | tr -d '/+=' | cut -c1-20)"
  ADMIN_PASSWORD="${GENERATED_PASSWORD}"
fi
SECRET_KEY="${SECRET_KEY:-$(head -c 32 /dev/urandom | base64)}"
BUILD_DIR="/tmp/${APP_NAME}-build"

echo "=== Politician Tracker Installer ==="
echo ""
echo "  Port:           ${PORT}"
echo "  Data directory:  ${DATA_DIR}"
if [ -n "${GENERATED_PASSWORD}" ]; then
  echo "  Admin password:  ${ADMIN_PASSWORD}  (generated - save this now)"
else
  echo "  Admin password:  (supplied via ADMIN_PASSWORD)"
fi
echo ""

# Clone and build
echo "[1/4] Downloading source..."
rm -rf "${BUILD_DIR}"
git clone --depth 1 https://github.com/thegspiro/politician-position-tracker.git "${BUILD_DIR}"

echo "[2/4] Building Docker image..."
docker build -t "${APP_NAME}" "${BUILD_DIR}"

echo "[3/4] Creating data directory..."
mkdir -p "${DATA_DIR}"

echo "[4/4] Starting container..."
docker rm -f "${APP_NAME}" 2>/dev/null || true
docker run -d \
  --name "${APP_NAME}" \
  --restart unless-stopped \
  -p "${PORT}:8000" \
  -v "${DATA_DIR}:/app/data" \
  -e "ADMIN_PASSWORD=${ADMIN_PASSWORD}" \
  -e "SECRET_KEY=${SECRET_KEY}" \
  "${APP_NAME}"

# Cleanup build
rm -rf "${BUILD_DIR}"

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
echo "    PORT=9847 ADMIN_PASSWORD=mypassword bash install-unraid.sh"
