launch_sh = """#!/bin/sh
SCRIPT_DIR="/mnt/us/ai"
LOG="$SCRIPT_DIR/ai.log"

exec 1>>"$LOG" 2>&1
echo "=== Starting Kindle AI Chat $(date) ==="

sleep 1.5

CVM_PID="$(pidof cvm)"
LP_PID="$(pidof launchpad)"

restore_kindle() {
    echo "=== Watchdog: Restoring Kindle $(date) ==="
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

# Autonomous safety watchdog: unfreezes Kindle UI if kindle-ai terminates
(
    sleep 3
    while pidof kindle-ai >/dev/null 2>&1; do
        sleep 1
    done
    restore_kindle
) &

chmod +x "$SCRIPT_DIR/kindle-ai" 2>/dev/null || true

cd "$SCRIPT_DIR" || exit 1
"$SCRIPT_DIR/kindle-ai"
ret=$?
echo "=== kindle-ai exited with code $ret $(date) ==="
exit $ret
"""

with open('D:/ai/launch_ai.sh', 'wb') as f:
    f.write(launch_sh.replace('\r\n', '\n').encode('utf-8'))

run_sh = """#!/bin/sh
( /mnt/us/ai/launch_ai.sh ) >/dev/null 2>&1 &
"""

with open('D:/extensions/ai_chat/bin/run.sh', 'wb') as f:
    f.write(run_sh.replace('\r\n', '\n').encode('utf-8'))

print("Wrote launch_ai.sh and run.sh with LF")
