#!/bin/bash

music_dir="$1"

if [ -z "$music_dir" ]; then
  echo "Usage: $0 <music_dir>"
  exit 1
fi

if [ ! -d "$music_dir" ]; then
  echo "Music directory does not exist: $music_dir"
  exit 1
fi

uv run python src/music_scanner.py --music_root "$music_dir" --debug