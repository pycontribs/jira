#!/usr/bin/env bash
# Smoke-test a freshly-built jira-software-standalone image: start it,
# poll until Jira responds (cold boot 10-20min), confirm /serverInfo
# returns the expected version, dump container logs to artifacts/
# regardless of outcome.
#
# Args:
#   $1  Image tag (e.g. ghcr.io/adehad/jira-software-standalone:11.3.4)
#   $2  Expected Jira version (asserted against /serverInfo JSON)
#   $3  Artifacts directory
set -euo pipefail

IMAGE="${1:?image tag required}"
EXPECTED_VERSION="${2:?expected version required}"
ARTIFACTS_DIR="${3:?artifacts directory required}"
NAME=jira-smoke
READY_URL=http://localhost:2990/jira/secure/Dashboard.jspa
INFO_URL=http://localhost:2990/jira/rest/api/2/serverInfo
POLL_INTERVAL=10
MAX_POLLS=180   # 30 min ceiling

mkdir -p "$ARTIFACTS_DIR"

cleanup() {
    docker logs "$NAME" > "$ARTIFACTS_DIR/container.log" 2>&1 || true
    docker rm -f "$NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT

# Pre-flight: drop any stale container left by a hard-killed previous
# run (Ctrl+C, kill -9). The cleanup trap handles graceful exits, but
# only on signals it can catch.
docker rm -f "$NAME" 2>/dev/null || true

# Tee docker run's stderr+stdout to smoke-run.log so pre-container
# failures (image pull errors, port collisions, name conflicts) are
# captured in artifacts even when no container exists for `docker logs`
# to read from.
docker run -dit -p 2990:2990 --name "$NAME" "$IMAGE" \
    2>&1 | tee "$ARTIFACTS_DIR/smoke-run.log"

ready=0
# GET (not HEAD): Jira 11 returns 405 Method Not Allowed on HEAD for
# secure servlets like Dashboard.jspa. GET produces a 200 once the
# webapp is up. Output is discarded via -o /dev/null to avoid streaming
# the rendered HTML.
for ((i = 1; i <= MAX_POLLS; i++)); do
    if curl --output /dev/null --silent --fail "$READY_URL"; then
        echo "Jira responsive after $((i * POLL_INTERVAL))s"
        ready=1
        break
    fi
    sleep "$POLL_INTERVAL"
done

if [ "$ready" != "1" ]; then
    echo "Jira not responsive after $((MAX_POLLS * POLL_INTERVAL))s" >&2
    exit 1
fi

RESP=$(curl --silent --show-error --fail -u admin:admin "$INFO_URL")
echo "$RESP" | tee "$ARTIFACTS_DIR/server-info.json"
echo "$RESP" | grep -F "\"version\":\"$EXPECTED_VERSION\"" \
    || { echo "Version mismatch: expected $EXPECTED_VERSION" >&2; exit 1; }
