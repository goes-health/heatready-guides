#!/usr/bin/env bash
# HeatReady publish gate: the ONE command the nightly routine runs before commit/push.
# Regenerates layout + agent files from data/guides.json, verifies nothing is stale,
# then runs the Playwright mobile check on every page at 375/390/768/1280. Exits non-zero on any failure.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d node_modules/playwright-core ] || npm install --silent --no-audit --no-fund
python3 scripts/agents.py            # applies scripts/layout.py first, then llms.txt / feeds / Markdown twins
python3 scripts/agents.py --check
node scripts/mobile-check.mjs "$@"
