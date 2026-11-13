#!/bin/sh
# Copies the local database and upload backups to an encrypted restic repository
# outside the NAS (S3, Backblaze B2, SFTP, rest-server, ...). restic encrypts
# everything with RESTIC_PASSWORD before it leaves the NAS.
set -eu

SOURCE_DIR="${OFFSITE_SOURCE_DIR:-/backups}"
STATUS_DIR="${BACKUP_STATUS_DIR:-/backups/status}"
INTERVAL_SECONDS="${OFFSITE_INTERVAL_SECONDS:-86400}"
RUN_ONCE="${BACKUP_RUN_ONCE:-false}"
KEEP_DAILY="${OFFSITE_KEEP_DAILY:-14}"
KEEP_WEEKLY="${OFFSITE_KEEP_WEEKLY:-8}"
KEEP_MONTHLY="${OFFSITE_KEEP_MONTHLY:-12}"
CHECK_SUBSET="${OFFSITE_CHECK_SUBSET:-5%}"

mkdir -p "$STATUS_DIR"

log() {
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"
}

if [ -z "${RESTIC_REPOSITORY:-}" ] || { [ -z "${RESTIC_PASSWORD:-}" ] && [ -z "${RESTIC_PASSWORD_FILE:-}" ]; }; then
  log "Offsite backup is not configured (RESTIC_REPOSITORY and RESTIC_PASSWORD missing). Waiting without doing anything."
  while true; do sleep 86400; done
fi

if ! restic cat config >/dev/null 2>&1; then
  log "Initialising restic repository $RESTIC_REPOSITORY"
  restic init
fi

run_backup() {
  log "Starting offsite backup of $SOURCE_DIR"
  restic backup "$SOURCE_DIR" --tag print-manager --exclude "$STATUS_DIR" --host print-manager-nas
  restic forget --tag print-manager --host print-manager-nas \
    --keep-daily "$KEEP_DAILY" --keep-weekly "$KEEP_WEEKLY" --keep-monthly "$KEEP_MONTHLY" --prune
  restic check --read-data-subset="$CHECK_SUBSET"
  date -u +%Y-%m-%dT%H:%M:%SZ > "$STATUS_DIR/offsite-last-success"
  log "Offsite backup completed and verified"
}

while true; do
  if ! run_backup; then
    log "Offsite backup FAILED; the readiness check will show it as missing."
  fi
  if [ "$RUN_ONCE" = "true" ]; then
    exit 0
  fi
  sleep "$INTERVAL_SECONDS"
done
