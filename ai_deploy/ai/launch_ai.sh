#!/bin/sh
SCRIPT_DIR="/mnt/us/ai"
LOG="$SCRIPT_DIR/ai.log"

exec 1>>"$LOG" 2>&1
echo "=== Starting Kindle AI Chat $(date) ==="

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

if [ -n "$CVM_PID" ]; then
    kill -STOP "$CVM_PID" 2>/dev/null || true
fi
if [ -n "$LP_PID" ]; then
    kill -STOP "$LP_PID" 2>/dev/null || true
fi

rm -f /var/tmp/ai_req.txt /var/tmp/ai_resp.txt 2>/dev/null || true

(
    while true; do
        if [ -f /var/tmp/ai_req.txt ]; then
            /mnt/us/ai/ask.sh
        fi
        sleep 1
    done
) &
WORKER_PID=$!

chmod +x "$SCRIPT_DIR/kindle-ai" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/ask.sh" 2>/dev/null || true

cd "$SCRIPT_DIR" || exit 1
"$SCRIPT_DIR/kindle-ai"
ret=$?
echo "=== kindle-ai exited with code $ret $(date) ==="
exit $ret
