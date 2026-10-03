#!/bin/bash

HITS_DIR=/data/shared/project_casey/1970
CASEY_FILE="$HITS_DIR/CASEY_001.wav"
SONG_FILE="/mnt/plex/Music/Johnny Cash/American IV_ The Man Comes Around/04 Bridge Over Troubled Water.m4a"
MIX_FILTER_FILE="./prompts/mix_filter.txt"

ffmpeg -i "$CASEY_FILE" -i "$SONG_FILE" \
  -filter_complex_script "$MIX_FILTER_FILE" \
  -map "[out]" \
  -c:a libmp3lame -q:a 2 \
  "$HITS_DIR/HIT001.mp3"
