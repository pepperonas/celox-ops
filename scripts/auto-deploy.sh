#!/usr/bin/env bash
# Auto-Deploy script — runs on VPS via cron every 5 minutes.
# Pulls latest from GitHub if main branch advanced, then rebuilds.
# Idempotent — only rebuilds if there were actual changes.

set -euo pipefail

REPO_DIR="/opt/celox-ops"
LOG_FILE="/var/log/celox-auto-deploy.log"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

cd "$REPO_DIR"

# Skip if no .git (e.g. tarball-deployed) — manual deploy still works
if [ ! -d .git ]; then
  exit 0
fi

# Fetch and check if we're behind
git fetch origin main --quiet
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
  exit 0
fi

log "=== Update detected: $LOCAL → $REMOTE ==="

# Pull and rebuild
if git pull --rebase origin main >>"$LOG_FILE" 2>&1; then
  log "git pull OK"
else
  log "git pull FAILED"
  exit 1
fi

# Detect what changed — only rebuild what's needed
CHANGED=$(git diff --name-only "$LOCAL" "$REMOTE")
REBUILD_BACKEND=false
REBUILD_FRONTEND=false
NGINX_CHANGED=false

if echo "$CHANGED" | grep -qE "^backend/"; then REBUILD_BACKEND=true; fi
if echo "$CHANGED" | grep -qE "^frontend/"; then REBUILD_FRONTEND=true; fi
if echo "$CHANGED" | grep -qE "^nginx/"; then NGINX_CHANGED=true; fi

if [ "$REBUILD_BACKEND" = true ] && [ "$REBUILD_FRONTEND" = true ]; then
  docker compose up -d --build backend frontend >>"$LOG_FILE" 2>&1
elif [ "$REBUILD_BACKEND" = true ]; then
  docker compose up -d --build backend >>"$LOG_FILE" 2>&1
elif [ "$REBUILD_FRONTEND" = true ]; then
  docker compose up -d --build frontend >>"$LOG_FILE" 2>&1
fi

# nginx löst die Upstreams dynamisch auf (resolver in nginx/default.conf) → nach
# einem backend/frontend-Rebuild findet nginx die neue Container-IP selbst
# (innerhalb valid=10s), KEIN nginx-Eingriff nötig. Nur wenn sich die
# nginx-Config SELBST ändert, muss der Container NEU ERZEUGT werden: der
# Bind-Mount hält den alten Datei-Inode fest — 'restart' übernimmt geänderte
# Config NICHT, nur '--force-recreate' bindet die neue Datei ein.
if [ "$NGINX_CHANGED" = true ]; then
  docker compose up -d --force-recreate nginx >>"$LOG_FILE" 2>&1
  log "nginx config changed → container recreated"
fi

if [ "$REBUILD_BACKEND" = true ] || [ "$REBUILD_FRONTEND" = true ]; then
  log "Rebuilt (backend=$REBUILD_BACKEND frontend=$REBUILD_FRONTEND); nginx resolvt dynamisch"
fi

# Run smoke tests if backend changed
if [ "$REBUILD_BACKEND" = true ]; then
  sleep 5
  HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8090/api/health || echo "ERR")
  log "Health check: $HEALTH"
fi

log "=== Deploy done ==="
