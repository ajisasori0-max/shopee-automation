#!/bin/bash
# Daily Growth Engine Run
# Runs every morning at 9 AM via the central CommerceOS token provider.
# Token refresh is handled by token_manager.py; this script does NOT refresh.

WORKSPACE="/Users/gerard/.openclaw/workspace/shopee-api-onboarding"
LOG_FILE="$WORKSPACE/logs/growth_engine_$(date +%Y%m%d).log"

mkdir -p "$WORKSPACE/logs"
cd "$WORKSPACE"
source "$WORKSPACE/.venv/bin/activate" || true
PYTHON="$WORKSPACE/.venv/bin/python3"

echo "========================================" >> "$LOG_FILE"
echo "Growth Engine Run: $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# Run growth engine
"$PYTHON" "$WORKSPACE/growth_engine.py" --mode all --budget 3000000 >> "$LOG_FILE" 2>&1

# Run competitor scraper (twice a week)
DAY_OF_WEEK=$(date +%u)
if [ "$DAY_OF_WEEK" -eq 1 ] || [ "$DAY_OF_WEEK" -eq 4 ]; then
    echo "Running competitor scraper..." >> "$LOG_FILE"
    "$PYTHON" "$WORKSPACE/competitor_scraper.py" >> "$LOG_FILE" 2>&1
fi

echo "Complete: $(date)" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
