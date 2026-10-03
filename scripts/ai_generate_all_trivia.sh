#!/bin/bash

HITS_FILE="$1"
OUTDIR="$2"

if [ -z "$HITS_FILE" ] || [ -z "$OUTDIR" ]; then
  echo "Usage: $0 HITS_FILE OUTDIR"
  exit 1
fi

uv run src/ai_generate_all_trivia.py --config_json ./config.json --hits_file "$HITS_FILE" --output_dir "$OUTDIR"