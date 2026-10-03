#!/bin/bash

YEAR="$1"
if [ -z "$YEAR" ]; then
  echo "Usage: $0 YEAR"
  exit 1
fi
OUTDIR="/data/shared/project_casey/$YEAR"
mkdir -p "$OUTDIR"

function psql_json_stdin() {
  psql -h 127.0.0.1 -p 5432 -U ai_app -d ai_workstation  --csv | \
  python3 -c 'import csv,json,sys; print(json.dumps(list(csv.DictReader(sys.stdin))))'
}

function psql_json() {
  psql -h 127.0.0.1 -p 5432 -U ai_app -d ai_workstation  --csv -c "$@"| \
  python3 -c 'import csv,json,sys; print(json.dumps(list(csv.DictReader(sys.stdin))))'
}

uv run jinja2 sql/number_ones.sql -D YEAR="$YEAR" | psql_json_stdin > "$OUTDIR/hits.json"
