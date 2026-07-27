#!/bin/bash
# Zieht die celox-ops-Backups (DB-Dump + Datei-Archiv) vom VPS auf raspi1.
#
# Warum ziehend statt schiebend: der Schlüssel liegt hier und ist auf dem VPS per
# rrsync auf genau ein Verzeichnis LESEND beschränkt — ein kompromittierter VPS
# kann damit nichts auf raspi1 verändern oder löschen.
#
# Gleiches Muster wie viacamp-pull-backup.sh. Cron: täglich 03:40 (nach dem
# 03:00-Backup auf dem VPS).
set -euo pipefail

DEST=/home/pi/celox-ops-backup
LOG=/home/pi/celoxops-pull.log
mkdir -p "$DEST"

{
  echo "[$(date -Iseconds)] start pull"
  # Bewusst OHNE --delete: die Rotation auf dem VPS (30 Tage) soll die
  # Zweitkopie nicht mitloeschen. Aufraeumen passiert hier separat.
  rsync -az \
    -e "ssh -i /home/pi/.ssh/id_ed25519_celoxops -o StrictHostKeyChecking=accept-new" \
    root@69.62.121.168: "$DEST/"

  # Eigene Aufbewahrung: 60 Tage (doppelt so lang wie auf dem VPS).
  find "$DEST" -maxdepth 1 -type f \( -name 'db-*.sql.gz' -o -name 'data-*.tar.gz' \) \
       -mtime +60 -delete

  DUMPS=$(ls -1 "$DEST"/db-*.sql.gz 2>/dev/null | wc -l)
  LATEST=$(ls -t "$DEST"/db-*.sql.gz 2>/dev/null | head -1)
  SIZE=$(du -hL "$LATEST" 2>/dev/null | cut -f1 || echo "?")
  echo "[$(date -Iseconds)] success ($DUMPS dumps, latest $LATEST = $SIZE)"
} >> "$LOG" 2>&1
