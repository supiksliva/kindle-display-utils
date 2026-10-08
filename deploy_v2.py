import shutil

# 1. Copy binary
shutil.copyfile("C:/Users/Biba/kindle-display-utils/kindle-ai", "D:/ai/kindle-ai")
print("Copied kindle-ai (pure syscall, no epoll) to D:/ai/kindle-ai")

# 2. Write launch_ai.sh
launch_sh = """#!/bin/sh
SCRIPT_DIR="/mnt/us/ai"
LOG="$SCRIPT_DIR/ai.log"

exec 1>>"$LOG" 2>&1
echo "=== Starting Kindle AI Chat $(date) ==="

# Wait 2 seconds for KUAL to cleanly finish menu exit
sleep 2

CVM_PID="$(pidof cvm)"
LP_PID="$(pidof launchpad)"

restore_kindle() {
    echo "=== Watchdog: Restoring Kindle $(date) ==="
    if [ -n "$WORKER_PID" ]; then
        kill "$WORKER_PID" 2>/dev/null || true
    fi
    if [ -n "$LP_PID" ]; then
        kill -CONT "$LP_PID" 2>/dev/null || true
    fi
    if [ -n "$CVM_PID" ]; then
        kill -CONT "$CVM_PID" 2>/dev/null || true
    fi
    /usr/sbin/eips -c 2>/dev/null || true
    powerd_test -p 2>/dev/null || true
    sleep 1
    powerd_test -p 2>/dev/null || true
}

trap restore_kindle EXIT INT TERM HUP

# 1. Freeze Kindle UI
if [ -n "$CVM_PID" ]; then
    kill -STOP "$CVM_PID" 2>/dev/null || true
fi
if [ -n "$LP_PID" ]; then
    kill -STOP "$LP_PID" 2>/dev/null || true
fi

# 2. Clean stale files
rm -f /var/tmp/ai_req.txt /var/tmp/ai_resp.txt 2>/dev/null || true

# 3. Start background AI worker (pure sh + native curl + native jq)
(
    while true; do
        if [ -f /var/tmp/ai_req.txt ]; then
            /mnt/us/ai/ask.sh
        fi
        sleep 1
    done
) &
WORKER_PID=$!

# 4. Run native kindle-ai GUI
chmod +x "$SCRIPT_DIR/kindle-ai" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/ask.sh" 2>/dev/null || true

cd "$SCRIPT_DIR" || exit 1
"$SCRIPT_DIR/kindle-ai"
ret=$?
echo "=== kindle-ai exited with code $ret $(date) ==="
exit $ret
"""

with open("D:/ai/launch_ai.sh", "wb") as f:
    f.write(launch_sh.replace("\r\n", "\n").encode("utf-8"))
print("Wrote D:/ai/launch_ai.sh")

# 3. Write ask.sh
ask_sh = """#!/bin/sh
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

API_KEY=""
if [ -f "$KEY_FILE" ]; then
    API_KEY=$(cat "$KEY_FILE" | tr -d '\r\n[:space:]')
fi
if [ -z "$API_KEY" ] && [ -f "$CONFIG_FILE" ]; then
    API_KEY=$("$JQ" -r '.api_key // empty' "$CONFIG_FILE" 2>/dev/null)
fi

if [ -z "$API_KEY" ]; then
    echo "[Ошибка: укажите API ключ в /mnt/us/ai/config.json или api_key.txt]" > "$RESP_FILE"
    exit 1
fi

if [ ! -f "$REQ_FILE" ]; then
    exit 0
fi

prompt=$(cat "$REQ_FILE")
rm -f "$REQ_FILE"

if [ -z "$prompt" ]; then
    exit 0
fi

# Handle reset
if [ "$prompt" = "/new" ] || [ "$prompt" = "/clear" ]; then
    echo '[{"role":"system","content":"Ты полезный, умный ассистент на электронной книге Kindle. Отвечай емко, понятно, по существу на русском языке."}]' > "$HIST_FILE"
    exit 0
fi

# Initialize history if not present
if [ ! -f "$HIST_FILE" ]; then
    echo '[{"role":"system","content":"Ты полезный, умный ассистент на электронной книге Kindle. Отвечай емко, понятно, по существу на русском языке."}]' > "$HIST_FILE"
fi

# Append user message to history
HIST=$(cat "$HIST_FILE")
HIST=$(echo "$HIST" | "$JQ" --arg p "$prompt" '. += [{"role":"user","content":$p}]')

# Build payload
PAYLOAD=$(echo "$HIST" | "$JQ" -c --arg m "$MODEL" '{model: $m, messages: ., temperature: 0.7}')

# Call API via curl with SSL and 35s timeout
RES=$("$CURL" -k -s --max-time 35 -X POST "$API_URL" \\
    -H "Authorization: Bearer $API_KEY" \\
    -H "Content-Type: application/json" \\
    --data-binary "$PAYLOAD" 2>/dev/null)

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

# Save AI message to history
HIST=$(echo "$HIST" | "$JQ" --arg a "$AI_TEXT" '. += [{"role":"assistant","content":$a}]')
echo "$HIST" > "$HIST_FILE"

# Write response for GUI
echo "$AI_TEXT" > "$RESP_FILE"
"""

with open("D:/ai/ask.sh", "wb") as f:
    f.write(ask_sh.replace("\r\n", "\n").encode("utf-8"))
print("Wrote D:/ai/ask.sh")

# 4. Write run.sh
run_sh = """#!/bin/sh
( /mnt/us/ai/launch_ai.sh ) >/dev/null 2>&1 &
"""

with open("D:/extensions/ai_chat/bin/run.sh", "wb") as f:
    f.write(run_sh.replace("\r\n", "\n").encode("utf-8"))
print("Wrote D:/extensions/ai_chat/bin/run.sh")
