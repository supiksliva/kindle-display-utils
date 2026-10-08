#!/bin/sh
export LD_LIBRARY_PATH="/mnt/us/usbnet/lib:$LD_LIBRARY_PATH"
export PATH="/mnt/us/usbnet/bin:$PATH"

REQ_FILE="/var/tmp/ai_req.txt"
RESP_FILE="/var/tmp/ai_resp.txt"
HIST_FILE="/var/tmp/ai_hist.json"

CURL="/mnt/us/usbnet/bin/curl"
JQ="/mnt/us/usbnet/bin/jq"
CONFIG_FILE="/mnt/us/ai/config.json"
KEY_FILE="/mnt/us/ai/api_key.txt"
MODEL="z-ai/glm-5.3-flash"
API_URL="https://api.polza.ai/v1/chat/completions"

if [ ! -f "$REQ_FILE" ]; then
    exit 0
fi

prompt=$(cat "$REQ_FILE")
rm -f "$REQ_FILE"

if [ -z "$prompt" ]; then
    exit 0
fi

if [ "$prompt" = "/new" ] || [ "$prompt" = "/clear" ]; then
    echo '[{"role":"system","content":"Ты полезный, умный ассистент на электронной книге Kindle. Отвечай емко, понятно, по существу на русском языке."}]' > "$HIST_FILE"
    exit 0
fi

API_KEY=""
if [ -f "$KEY_FILE" ]; then
    API_KEY=$(cat "$KEY_FILE" | tr -d '
[:space:]')
fi
if [ -z "$API_KEY" ] && [ -f "$CONFIG_FILE" ]; then
    API_KEY=$("$JQ" -r '.api_key // empty' "$CONFIG_FILE" 2>/dev/null)
fi

if [ -z "$API_KEY" ]; then
    echo "[Ошибка: укажите API ключ в /mnt/us/ai/config.json или api_key.txt]" > "$RESP_FILE"
    exit 1
fi

if [ ! -f "$HIST_FILE" ]; then
    echo '[{"role":"system","content":"Ты полезный, умный ассистент на электронной книге Kindle. Отвечай емко, понятно, по существу на русском языке."}]' > "$HIST_FILE"
fi

HIST=$(cat "$HIST_FILE")
HIST=$(echo "$HIST" | "$JQ" --arg p "$prompt" '. += [{"role":"user","content":$p}]')

PAYLOAD=$(echo "$HIST" | "$JQ" -c --arg m "$MODEL" '{model: $m, messages: ., temperature: 0.7}')

RES=$("$CURL" -k -s --max-time 35 -X POST "$API_URL"     -H "Authorization: Bearer $API_KEY"     -H "Content-Type: application/json"     --data-binary "$PAYLOAD" 2>/dev/null)

if [ -z "$RES" ]; then
    echo "[Ошибка сети: нет ответа от сервера. Проверьте Wi-Fi]" > "$RESP_FILE"
    exit 1
fi

ERR_MSG=$(echo "$RES" | "$JQ" -r '.error.message // empty' 2>/dev/null)
if [ -n "$ERR_MSG" ]; then
    echo "[Ошибка API: $ERR_MSG]" > "$RESP_FILE"
    exit 1
fi

AI_TEXT=$(echo "$RES" | "$JQ" -r '.choices[0].message.content // empty' 2>/dev/null)
if [ -z "$AI_TEXT" ]; then
    echo "[ИИ вернул пустой ответ]" > "$RESP_FILE"
    exit 1
fi

HIST=$(echo "$HIST" | "$JQ" --arg a "$AI_TEXT" '. += [{"role":"assistant","content":$a}]')
echo "$HIST" > "$HIST_FILE"

echo "$AI_TEXT" > "$RESP_FILE"
