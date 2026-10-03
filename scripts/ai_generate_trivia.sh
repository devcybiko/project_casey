#!/bin/bash

set -a
source ~/.secrets
set +a

PAYLOAD_TEMPLATE="./scripts/payload_j2.json"
TMP_PAYLOAD="/tmp/payload.json"
TMP_RESPONSE="/tmp/response.json"
PROMPT_TEMPLATE="./prompts/song_trivia_j2.md"
TMP_PROMPT="/tmp/prompt.md"
MODEL="gemma412b-wikipedia"
URL='http://ai.greg-smith.com:3000/api/chat/completions'
# URL="http://localhost:11434/api/generate"

jinja2 "$PROMPT_TEMPLATE" -D ARTIST="Elton John" -D SONG="Tiny Dancer" -D CHART_DATE="1971-08-01" -D RANKING="5" > "$TMP_PROMPT"
jinja2 "$PAYLOAD_TEMPLATE" -D PROMPT="$(cat $TMP_PROMPT)" -D MODEL="$MODEL" > "$TMP_PAYLOAD"

curl -X POST "$URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPEN_WEBUI_API_KEY" \
  -d @"$TMP_PAYLOAD" > "$TMP_RESPONSE"

jq '.choices[0].message.content' "$TMP_RESPONSE" 
# cat $TMP_RESPONSE