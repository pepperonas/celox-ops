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

if echo "$CHANGED" | grep -qE "^backend/"; then REBUILD_BACKEND=true; fi
if echo "$CHANGED" | grep -qE "^frontend/"; then REBUILD_FRONTEND=true; fi

if [ "$REBUILD_BACKEND" = true ] && [ "$REBUILD_FRONTEND" = true ]; then
  docker compose up -d --build backend frontend >>"$LOG_FILE" 2>&1
elif [ "$REBUILD_BACKEND" = true ]; then
  docker compose up -d --build backend >>"$LOG_FILE" 2>&1
elif [ "$REBUILD_FRONTEND" = true ]; then
  docker compose up -d --build frontend >>"$LOG_FILE" 2>&1
fi

# Always restart nginx (safe, picks up potential IP changes)
if [ "$REBUILD_BACKEND" = true ] || [ "$REBUILD_FRONTEND" = true ]; then
  docker compose restart nginx >>"$LOG_FILE" 2>&1
  log "Containers rebuilt + nginx restarted"
fi

# Run smoke tests if backend changed
if [ "$REBUILD_BACKEND" = true ]; then
  sleep 5
  HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8090/api/health || echo "ERR")
  log "Health check: $HEALTH"
fi

log "=== Deploy done ==="
