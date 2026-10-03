#!/bin/bash

HITS_DIR="$1"

if [ -z "$HITS_DIR" ]; then
  echo "Usage: $0 HITS_DIR"
  exit 1
fi

uv run src/merge_all_casey.py --config_json ./config.json --hits_file "$HITS_DIR/HITS.json" --casey_dir "$HITS_DIR" --output_dir "$HITS_DIR"