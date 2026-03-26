#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/mothejeweler/Documents/AI Projects/Personal Assistant"
PY="/Users/mothejeweler/Documents/.venv/bin/python"

cd "$ROOT"

echo "Step 1/5: Syntax checks"
"$PY" -m compileall -q main.py personality.py video_personality_updater.py smoke_tests.py

echo "Step 2/5: Smoke tests"
"$PY" smoke_tests.py

echo "Step 3/5: Dry-run personality sync status"
"$PY" - <<'PY'
import main
updater = main.video_updater
print({
    "updater_available": bool(updater),
    "enabled": bool(updater and updater.enabled()),
    "refresh_minutes": main.PERSONALITY_REFRESH_MINUTES,
    "rss_url": updater.rss_url if updater else "",
})
PY

echo "Step 4/5: Git diff summary"
git status --short

echo "Step 5/5: Done"
echo "All automated checks completed."
