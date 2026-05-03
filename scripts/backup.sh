#!/usr/bin/env bash
# Daily backup of celox-ops: DB dump + attached files (PDFs, attachments).
# Keeps last 30 days, removes older.
# Designed to run via cron on the VPS.

set -euo pipefail

BACKUP_DIR="/var/backups/celox-ops"
TS=$(date +%Y-%m-%d)
RETENTION_DAYS=30
LOG_FILE="$BACKUP_DIR/backup.log"

mkdir -p "$BACKUP_DIR"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

log "=== Backup start ==="

# 1. Database dump (compressed)
DB_FILE="$BACKUP_DIR/db-$TS.sql.gz"
if docker exec celox-ops-db-1 pg_dump -U celoxops celoxops 2>>"$LOG_FILE" | gzip > "$DB_FILE"; then
  DB_SIZE=$(du -h "$DB_FILE" | cut -f1)
  log "DB dump OK: $DB_FILE ($DB_SIZE)"
else
  log "DB dump FAILED"
  rm -f "$DB_FILE"
  exit 1
fi

# 2. Volume contents (PDFs, attachments, pagespeed reports, signature)
DATA_FILE="$BACKUP_DIR/data-$TS.tar.gz"
if docker run --rm -v celox-ops_invoice_data:/data -v "$BACKUP_DIR":/out alpine \
   tar czf "/out/data-$TS.tar.gz" -C /data . 2>>"$LOG_FILE"; then
  DATA_SIZE=$(du -h "$DATA_FILE" | cut -f1)
  log "Data backup OK: $DATA_FILE ($DATA_SIZE)"
else
  log "Data backup FAILED"
  exit 1
fi

# 3. Rotate: delete files older than RETENTION_DAYS
DELETED=$(find "$BACKUP_DIR" -maxdepth 1 -type f \( -name 'db-*.sql.gz' -o -name 'data-*.tar.gz' \) -mtime +$RETENTION_DAYS -delete -print | wc -l)
if [ "$DELETED" -gt 0 ]; then
  log "Rotated: $DELETED old backup file(s) removed"
fi

# 4. Off-site sync (optional — only if rclone is installed and configured)
# Configure with: rclone config (create remote named 'celox-backup')
# Then this will sync to e.g. Backblaze B2 / Hetzner Storage Box / Strato HiDrive
if command -v rclone >/dev/null && rclone listremotes | grep -q '^celox-backup:'; then
  if rclone sync "$BACKUP_DIR" celox-backup:celox-ops/ \
       --exclude '*.log' --transfers 4 --quiet 2>>"$LOG_FILE"; then
    log "Off-site sync OK (celox-backup:celox-ops/)"
  else
    log "Off-site sync FAILED (continuing)"
  fi
else
  log "Off-site sync skipped (rclone or remote 'celox-backup' not configured)"
fi

# 5. Final report
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
COUNT=$(find "$BACKUP_DIR" -maxdepth 1 -type f \( -name 'db-*.sql.gz' -o -name 'data-*.tar.gz' \) | wc -l)
log "=== Backup done: $COUNT files, $TOTAL_SIZE total ==="
