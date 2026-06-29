#!/bin/sh
set -eu

: "${DATABASE_URL:?DATABASE_URL is required}"

BACKUP_DIR="${BACKUP_DIR:-/backups/daily}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
BACKUP_INTERVAL_SECONDS="${BACKUP_INTERVAL_SECONDS:-86400}"
BACKUP_RUN_ONCE="${BACKUP_RUN_ONCE:-false}"

mkdir -p "$BACKUP_DIR"

normalize_database_url() {
  printf '%s' "$DATABASE_URL" | sed 's#^postgresql+psycopg://#postgresql://#'
}

run_backup() {
  timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
  target="$BACKUP_DIR/print_manager_$timestamp.dump"
  tmp="$target.tmp"
  database_url="$(normalize_database_url)"

  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting PostgreSQL backup: $target"
  if pg_dump --format=custom --file="$tmp" "$database_url"; then
    mv "$tmp" "$target"
    sha256sum "$target" > "$target.sha256"
    find "$BACKUP_DIR" -type f -name 'print_manager_*.dump' -mtime +"$BACKUP_RETENTION_DAYS" -delete
    find "$BACKUP_DIR" -type f -name 'print_manager_*.dump.sha256' -mtime +"$BACKUP_RETENTION_DAYS" -delete
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Backup completed: $target"
    return 0
  fi

  rm -f "$tmp"
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Backup failed"
  return 1
}

while true; do
  run_backup
  if [ "$BACKUP_RUN_ONCE" = "true" ]; then
    exit 0
  fi
  sleep "$BACKUP_INTERVAL_SECONDS"
done
