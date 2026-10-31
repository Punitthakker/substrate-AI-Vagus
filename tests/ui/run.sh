#!/usr/bin/env bash
# Browser walkthrough of the console against a local server (rule core, no model key needed).
# Needs: pip install -r requirements.txt, npm i -g playwright (or npx playwright install chromium).
set -euo pipefail
cd "$(dirname "$0")/../.."
SUBSTRATE_SELFCHECK=0 SUBSTRATE_DB=":memory:" python -m uvicorn app.main:app --port 8790 >/tmp/substrate-ui.log 2>&1 &
PID=$!
trap 'kill $PID 2>/dev/null || true' EXIT
for i in $(seq 1 40); do curl -sf localhost:8790/v1/health >/dev/null && break; sleep 0.5; done
node tests/ui/console.js
node tests/ui/voice.js
node tests/ui/readaloud_money.js
echo "UI walkthrough: OK"
