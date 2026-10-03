#!/bin/bash

HITS_DIR="$1"

if [ -z "$HITS_DIR" ]; then
  echo "Usage: $0 HITS_DIR"
  exit 1
fi

uv run src/ai_generate_all_casey.py --config_json ./config.json --input_dir "$HITS_DIR" --output_dir "$HITS_DIR"