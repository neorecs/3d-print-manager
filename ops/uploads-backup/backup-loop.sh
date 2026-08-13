#!/bin/sh
set -eu

SOURCE_DIR="${UPLOAD_SOURCE_DIR:-/uploads}"
BACKUP_DIR="${UPLOAD_BACKUP_DIR:-/backups/uploads}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
INTERVAL_SECONDS="${BACKUP_INTERVAL_SECONDS:-86400}"
RUN_ONCE="${BACKUP_RUN_ONCE:-false}"
BACKUP_STATUS_DIR="${BACKUP_STATUS_DIR:-/backups/status}"

mkdir -p "$BACKUP_DIR" "$BACKUP_STATUS_DIR"

run_backup() {
  timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
  target="$BACKUP_DIR/print_manager_uploads_$timestamp.tar.gz"
  tmp="$target.tmp"

  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting uploads backup: $target"
  tar -C "$SOURCE_DIR" -czf "$tmp" .
  mv "$tmp" "$target"
  sha256sum "$target" > "$target.sha256"
  date -u +%Y-%m-%dT%H:%M:%SZ > "$BACKUP_STATUS_DIR/uploads-last-success"
  find "$BACKUP_DIR" -type f -name 'print_manager_uploads_*.tar.gz' -mtime +"$RETENTION_DAYS" -delete
  find "$BACKUP_DIR" -type f -name 'print_manager_uploads_*.tar.gz.sha256' -mtime +"$RETENTION_DAYS" -delete
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Uploads backup completed: $target"
}

while true; do
  run_backup
  if [ "$RUN_ONCE" = "true" ]; then
    exit 0
  fi
  sleep "$INTERVAL_SECONDS"
done
