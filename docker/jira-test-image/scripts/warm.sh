#!/usr/bin/env bash
# Build-time warmer. Boots atlas-run in the background, polls
# /rest/api/2/serverInfo until 200, SIGTERMs the JVM, waits for
# graceful shutdown, and validates the warmed paths exist + are
# non-empty.
#
# The `warmed` runtime stage COPY-s these paths from this stage:
#   /root/.m2/repository    - Maven cache (Jira deps, plugins, etc.)
#   /opt/jira-plugin/target - atlas-run unpacks Jira's webapp + the
#                             local plugin jar + initial HSQLDB here
#
# Failure modes that abort the build (rather than baking a half-warm
# image):
#   - atlas-run exits before /serverInfo becomes responsive
#   - poll ceiling hit (cold boot exceeded MAX_POLLS * POLL_INTERVAL)
#   - either warmed path missing or empty after shutdown
set -euo pipefail

LOG=/tmp/warm.log
WORKDIR_TARGET=/opt/jira-plugin/target
M2_REPO=/root/.m2/repository
READY_URL=http://localhost:2990/jira/rest/api/2/serverInfo
POLL_INTERVAL=10
MAX_POLLS=180  # 30 min ceiling; cold boot of Jira 11 is ~10-20min

# atlas-run hardcodes a call to the shut-down Atlassian Marketplace v1
# endpoint at startup; -DskipAllPrompts=true makes that 404 non-fatal.
#
# stdin is redirected from /dev/zero (not /dev/null) because the Cargo
# Maven plugin behind `atlas-run` reads stdin after "Type Ctrl-C to
# shutdown gracefully" and treats EOF as Ctrl-C. Docker build has no
# TTY, so /dev/null (or inherited closed stdin) returns EOF immediately
# and Jira shuts down within ~1s of finishing startup -- before the
# poll loop below can confirm /serverInfo. /dev/zero blocks the read
# forever, keeping the JVM alive until we send SIGTERM ourselves.
atlas-run -DskipAllPrompts=true < /dev/zero > "$LOG" 2>&1 &
ATLAS_PID=$!
echo "[warm] atlas-run pid=$ATLAS_PID, polling $READY_URL ..."

ready=0
for ((i = 1; i <= MAX_POLLS; i++)); do
    if curl --output /dev/null --silent --fail -u admin:admin "$READY_URL"; then
        echo "[warm] /serverInfo responsive after $((i * POLL_INTERVAL))s"
        ready=1
        break
    fi
    if ! kill -0 "$ATLAS_PID" 2>/dev/null; then
        echo "[warm] FAIL: atlas-run exited early (pid $ATLAS_PID gone)" >&2
        echo "[warm] last 200 lines of warm.log:" >&2
        tail -200 "$LOG" >&2
        exit 1
    fi
    sleep "$POLL_INTERVAL"
done

if [ "$ready" != "1" ]; then
    echo "[warm] FAIL: /serverInfo never became responsive after $((MAX_POLLS * POLL_INTERVAL))s" >&2
    tail -200 "$LOG" >&2
    kill -TERM "$ATLAS_PID" 2>/dev/null || true
    exit 1
fi

# SIGTERM the JVM. atlas-run forwards to mvn which forwards to Jetty;
# Jetty graceful shutdown takes ~30s. Wait for the process tree to
# drain so the warmed paths are not mid-write.
echo "[warm] shutting down atlas-run gracefully ..."
kill -TERM "$ATLAS_PID"
wait "$ATLAS_PID" 2>/dev/null || true

# Validate the paths the warmed runtime stage will COPY. If atlas-run's
# unpack location ever changes (e.g. AMPS major bump moves the webapp
# from target/ to elsewhere), this loop fails fast so we do not bake
# an image where the cache lives but the webapp does not.
for path in "$M2_REPO" "$WORKDIR_TARGET"; do
    if [ ! -d "$path" ]; then
        echo "[warm] FAIL: expected warmed path $path does not exist" >&2
        exit 1
    fi
    if [ -z "$(ls -A "$path" 2>/dev/null)" ]; then
        echo "[warm] FAIL: expected warmed path $path is empty" >&2
        exit 1
    fi
    size=$(du -sb "$path" 2>/dev/null | awk '{print $1}')
    echo "[warm] OK: $path size=${size} bytes"
done

echo "[warm] done"
