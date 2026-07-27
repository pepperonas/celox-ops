#!/usr/bin/env bash
# Restore-Probe: stellt das neueste Backup in einer Wegwerf-Datenbank wieder her
# und prüft, ob die Geschäftsdaten wirklich drin sind.
#
# Ein Backup, das nie zurückgespielt wurde, ist eine Vermutung. Diese Probe läuft
# wöchentlich, fasst die Produktionsdatenbank NICHT an (eigener Container, eigener
# Port, eigenes Volume) und räumt sich selbst auf.
#
# Ergebnis: eine Zeile in restore-test.status (OK/FAIL + Zeitstempel + Zahlen)
# plus Details im Log. Bei FAIL geht — wenn msmtp konfiguriert ist — eine Mail raus.
#
# Aufruf: /opt/celox-ops/scripts/restore-test.sh
set -uo pipefail

BACKUP_DIR="/var/backups/celox-ops"
LOG_FILE="$BACKUP_DIR/restore-test.log"
STATUS_FILE="$BACKUP_DIR/restore-test.status"
CONTAINER="celox-ops-restore-probe"
PGPORT_TEST=55432
PGPASS="restore-probe"
MAIL_TO="martin.pfeffer@celox.io"
# Untergrenzen: darunter ist der Dump verdächtig leer (kein echter Bestand).
MIN_USERS=1
MIN_CUSTOMERS=1

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"; }

cleanup() { docker rm -f "$CONTAINER" >/dev/null 2>&1 || true; }
trap cleanup EXIT

fail() {
  log "FAIL: $*"
  echo "FAIL $(date '+%Y-%m-%dT%H:%M:%S%z') $*" > "$STATUS_FILE"
  if command -v msmtp >/dev/null 2>&1; then
    printf 'Subject: [celox-ops] Restore-Probe FEHLGESCHLAGEN\nTo: %s\n\n%s\n\nLog: %s\n' \
      "$MAIL_TO" "$*" "$LOG_FILE" | msmtp "$MAIL_TO" >/dev/null 2>&1 || true
  fi
  exit 1
}

log "=== Restore-Probe start ==="

# 1. Neuestes DB-Backup + Datei-Archiv finden
DB_DUMP=$(ls -1t "$BACKUP_DIR"/db-*.sql.gz 2>/dev/null | head -1)
DATA_TAR=$(ls -1t "$BACKUP_DIR"/data-*.tar.gz 2>/dev/null | head -1)
[ -n "$DB_DUMP" ] || fail "Kein DB-Backup in $BACKUP_DIR gefunden"
log "Dump: $DB_DUMP ($(du -h "$DB_DUMP" | cut -f1))"

# Frische prüfen: älter als 48 h heißt, das nächtliche Backup läuft nicht mehr.
AGE_HOURS=$(( ( $(date +%s) - $(stat -c %Y "$DB_DUMP") ) / 3600 ))
[ "$AGE_HOURS" -le 48 ] || fail "Neuestes Backup ist $AGE_HOURS h alt (> 48 h)"

# 2. Wegwerf-Postgres starten (gleiche Hauptversion wie Produktion)
PG_IMAGE=$(docker inspect celox-ops-db-1 --format '{{.Config.Image}}' 2>/dev/null || echo "postgres:16")
cleanup
docker run --rm -d --name "$CONTAINER" \
  -e POSTGRES_PASSWORD="$PGPASS" -e POSTGRES_USER=probe -e POSTGRES_DB=probe \
  -p "127.0.0.1:$PGPORT_TEST:5432" "$PG_IMAGE" >> "$LOG_FILE" 2>&1 \
  || fail "Wegwerf-Datenbank ($PG_IMAGE) konnte nicht gestartet werden"

# Warten, bis die Datenbank WIRKLICH bereit ist. `pg_isready` genügt nicht: das
# Postgres-Image startet zur Initialisierung einen temporären Server, fährt ihn
# herunter und startet dann den echten — ein Restore in diesem Fenster bricht mit
# „server closed the connection unexpectedly" ab. Deshalb auf den Abschluss-Marker
# im Log warten und danach eine echte Abfrage verlangen.
READY=0
for _ in $(seq 1 60); do
  if docker logs "$CONTAINER" 2>&1 | grep -q "database system is ready to accept connections" \
     && docker logs "$CONTAINER" 2>&1 | grep -q "PostgreSQL init process complete" \
     && docker exec "$CONTAINER" psql -U probe -d probe -tAc "select 1" >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 1
done
[ "$READY" -eq 1 ] || fail "Wegwerf-Datenbank wurde nicht bereit"

# 3. Dump einspielen. Der Dump enthält CREATE-Anweisungen für den Prod-Rollennamen
#    — die Rolle legen wir vorher an, sonst brechen die OWNER-Zeilen ab.
docker exec "$CONTAINER" psql -U probe -d probe -q \
  -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='celoxops') THEN CREATE ROLE celoxops; END IF; END \$\$;" \
  >> "$LOG_FILE" 2>&1

if ! gunzip -c "$DB_DUMP" | docker exec -i "$CONTAINER" psql -U probe -d probe -v ON_ERROR_STOP=0 \
     >> "$LOG_FILE" 2>&1; then
  fail "psql-Restore brach ab (siehe $LOG_FILE)"
fi

# 4. Sanity: sind die Geschäftsdaten wirklich da?
count() {
  docker exec "$CONTAINER" psql -U probe -d probe -tAc \
    "SELECT count(*) FROM $1" 2>/dev/null | tr -d '[:space:]'
}
USERS=$(count users); CUSTOMERS=$(count customers); INVOICES=$(count invoices)
LEADS=$(count rainmaker_leads)
[ -n "$USERS" ] && [ -n "$CUSTOMERS" ] && [ -n "$INVOICES" ] \
  || fail "Kerntabellen fehlen nach dem Restore (users/customers/invoices)"
[ "$USERS" -ge "$MIN_USERS" ] || fail "Nur $USERS Nutzer im Restore (erwartet >= $MIN_USERS)"
[ "$CUSTOMERS" -ge "$MIN_CUSTOMERS" ] || fail "Nur $CUSTOMERS Kunden im Restore"

# Rechnungssummen müssen rechenbar sein (nicht bloß Zeilen vorhanden)
SUM=$(docker exec "$CONTAINER" psql -U probe -d probe -tAc \
  "SELECT coalesce(sum(total),0)::text FROM invoices" 2>/dev/null | tr -d '[:space:]')
[ -n "$SUM" ] || fail "Rechnungsbeträge nicht lesbar"

# 5. Datei-Archiv prüfen (PDFs/Anhänge) — ein lesbares tar reicht als Nachweis
FILES="n/a"
if [ -n "$DATA_TAR" ]; then
  FILES=$(tar tzf "$DATA_TAR" 2>/dev/null | wc -l | tr -d '[:space:]')
  [ "${FILES:-0}" -gt 0 ] || fail "Datei-Archiv $DATA_TAR ist nicht lesbar/leer"
fi

RESULT="users=$USERS customers=$CUSTOMERS invoices=$INVOICES leads=${LEADS:-?} summe=$SUM dateien=$FILES alter=${AGE_HOURS}h"
log "OK: $RESULT"
echo "OK $(date '+%Y-%m-%dT%H:%M:%S%z') $RESULT" > "$STATUS_FILE"

# Log kurz halten
tail -n 2000 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
log "=== Restore-Probe Ende ==="
