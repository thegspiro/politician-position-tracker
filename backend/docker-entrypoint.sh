#!/bin/sh
# Container entrypoint: bring the schema up to date, then start the server.
#
# POSIX sh for portability across Unraid, Docker, plain Linux hosts and AWS.
# Migrations run here rather than inside the application so that they execute
# exactly once per container start, before any request is served.
#
# By default the container runs as root, as it always has. Set PUID (and
# optionally PGID, which defaults to PUID) to drop privileges after fixing
# ownership of /app/data. Unraid appdata is normally owned by nobody:users,
# which is PUID=99 PGID=100.
set -eu

if [ "$(id -u)" = "0" ] && [ -n "${PUID:-}" ]; then
  PGID="${PGID:-$PUID}"
  case "$PUID$PGID" in
    *[!0-9]*)
      echo "PUID and PGID must be numeric (got PUID='${PUID}' PGID='${PGID}')." >&2
      exit 1
      ;;
  esac
  mkdir -p /app/data
  chown -R "${PUID}:${PGID}" /app/data
  echo "Dropping privileges to ${PUID}:${PGID}..."
  exec setpriv --reuid="${PUID}" --regid="${PGID}" --clear-groups "$0" "$@"
fi

echo "Running database migrations..."
alembic upgrade head

echo "Starting application..."
exec uvicorn app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}"
