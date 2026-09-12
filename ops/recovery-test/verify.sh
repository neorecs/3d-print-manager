#!/bin/sh
set -eu

: "${RESTORE_DATABASE_URL:?RESTORE_DATABASE_URL is required}"

dump_file="$(find /backups/daily -type f -name 'print_manager_*.dump' | sort | tail -n 1)"
upload_file="$(find /backups/uploads -type f -name 'print_manager_uploads_*.tar.gz' | sort | tail -n 1)"
test -n "$dump_file"
test -n "$upload_file"
sha256sum -c "$dump_file.sha256"
sha256sum -c "$upload_file.sha256"
pg_restore --clean --if-exists --no-owner --no-privileges --dbname="$RESTORE_DATABASE_URL" "$dump_file"
count="$(psql "$RESTORE_DATABASE_URL" -tAc "SELECT count(*) FROM products WHERE name='Recovery test product'")"
test "$count" = "1"
mkdir -p /tmp/restored-uploads
tar -xzf "$upload_file" -C /tmp/restored-uploads
printf 'recovery-upload-content\n' | cmp - /tmp/restored-uploads/recovery/product.txt
echo "Gezamenlijke database- en uploadshersteltest geslaagd."
