#!/usr/bin/env bash
# N9 guard: the internal token must never reach the public bundle.
# Builds with VITE_INTERNAL_TOKEN set to a marker and fails if the marker,
# the env var name, or the X-Internal-Token header shows up in dist/.
set -euo pipefail
cd "$(dirname "$0")/.."
MARKER="N9_MARKER_$RANDOM$RANDOM"
VITE_INTERNAL_TOKEN="$MARKER" npm run build >/dev/null
if grep -rlE "$MARKER|VITE_INTERNAL_TOKEN|X-Internal-Token" dist; then
  echo "FAIL: internal token code path found in dist/" >&2
  exit 1
fi
echo "OK: no internal token in dist/"
