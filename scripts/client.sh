curl --fail-with-body \
  -X POST \
  -H "Content-Type: application/json" \
  --data-binary @./a.json \
  http://ai.greg-smith.com:8101/api/tts
