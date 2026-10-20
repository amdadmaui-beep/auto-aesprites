#!/bin/bash
# Installs the Remotion project's packages at the start of cloud sessions,
# since each cloud session starts on a fresh machine.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR/video"
npm install --no-audit --no-fund
