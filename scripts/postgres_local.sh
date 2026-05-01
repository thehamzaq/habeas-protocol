#!/usr/bin/env bash
# Local Postgres control for the habeas-protocol corpus.
#
# Stores everything under ~/.local/var/pgdata-habeas. Listens on 5433 (so it
# never collides with a system Postgres on 5432). User is your shell $USER.
# No sudo, no Homebrew, no system services.
#
# Usage:
#   ./scripts/postgres_local.sh init      # one-time: initdb + create database
#   ./scripts/postgres_local.sh start     # start the server in the background
#   ./scripts/postgres_local.sh stop      # stop the server
#   ./scripts/postgres_local.sh status    # is it running?
#   ./scripts/postgres_local.sh psql      # open psql shell into the habeas db
#   ./scripts/postgres_local.sh schema    # apply db/schema.sql
#   ./scripts/postgres_local.sh reset     # drop + recreate the habeas db
#   ./scripts/postgres_local.sh nuke      # delete the entire data dir
#
# After init+start+schema, run scripts/migrate_to_postgres.py to load the
# corpus. Connection env vars are exported automatically by `eval $(./scripts/postgres_local.sh env)`.

set -euo pipefail

PGDATA="${PGDATA:-$HOME/.local/var/pgdata-habeas}"
PGPORT="${PGPORT:-5433}"
PGHOST="${PGHOST:-localhost}"
PGUSER="${PGUSER:-$USER}"
PGDATABASE="${PGDATABASE:-habeas}"
LOG="${PGDATA}.log"

export PATH="$HOME/.local/bin:$PATH"

cmd=${1:-}
case "$cmd" in
  init)
    if [ -d "$PGDATA" ]; then
      echo "data dir already exists: $PGDATA"
    else
      mkdir -p "$(dirname "$PGDATA")"
      initdb -D "$PGDATA" -U "$PGUSER" --auth=trust --encoding=UTF8 --locale=C
    fi
    # write a minimal postgresql.conf overlay
    grep -q "^port = $PGPORT" "$PGDATA/postgresql.conf" 2>/dev/null || echo "port = $PGPORT" >> "$PGDATA/postgresql.conf"
    grep -q "^unix_socket_directories" "$PGDATA/postgresql.conf" 2>/dev/null || echo "unix_socket_directories = '$HOME/.local/var/pg-sock'" >> "$PGDATA/postgresql.conf"
    mkdir -p "$HOME/.local/var/pg-sock"
    # start, create db, stop
    pg_ctl -D "$PGDATA" -l "$LOG" -o "-p $PGPORT" -w start
    createdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$PGDATABASE" 2>/dev/null || echo "(database $PGDATABASE already exists)"
    pg_ctl -D "$PGDATA" -m fast stop
    echo
    echo "initialised. start with: $0 start"
    ;;
  start)
    if pg_ctl -D "$PGDATA" status >/dev/null 2>&1; then
      echo "already running"
    else
      pg_ctl -D "$PGDATA" -l "$LOG" -o "-p $PGPORT" -w start
    fi
    echo "ready: postgres://$PGUSER@$PGHOST:$PGPORT/$PGDATABASE"
    ;;
  stop)
    pg_ctl -D "$PGDATA" -m fast stop
    ;;
  status)
    pg_ctl -D "$PGDATA" status
    ;;
  psql)
    shift || true
    exec psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" "$@"
    ;;
  schema)
    SCHEMA_FILE="$(dirname "$0")/../db/schema.sql"
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -f "$SCHEMA_FILE"
    ;;
  reset)
    pg_ctl -D "$PGDATA" status >/dev/null 2>&1 && true
    dropdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$PGDATABASE" || true
    createdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$PGDATABASE"
    echo "database $PGDATABASE recreated empty"
    ;;
  nuke)
    pg_ctl -D "$PGDATA" -m immediate stop 2>/dev/null || true
    rm -rf "$PGDATA" "$LOG"
    echo "deleted $PGDATA"
    ;;
  env)
    cat <<EOF
export PGHOST="$PGHOST"
export PGPORT="$PGPORT"
export PGUSER="$PGUSER"
export PGDATABASE="$PGDATABASE"
export PATH="\$HOME/.local/bin:\$PATH"
EOF
    ;;
  *)
    sed -n '2,30p' "$0"
    exit 1
    ;;
esac
