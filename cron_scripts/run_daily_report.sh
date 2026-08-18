#!/bin/bash
cd "$(dirname "$0")/.."
/usr/local/bin/python3 -c "
import sys, os
sys.path.insert(0, '.')
from full_automation import get_daily_report, get_campaign_targets, generate_recommendations, send_report
from datetime import datetime
import json

report = get_daily_report()
targets = get_campaign_targets()

if report:
    last_change = None
    if os.path.exists('last_change.json'):
        with open('last_change.json', 'r') as f:
            last_change = json.load(f).get('date')
    recommendations, action = generate_recommendations(report, targets, last_change)
    send_report(report, targets, recommendations, action)
    print('✅ Daily report sent')
else:
    print('❌ No report data available')
" >> logs/daily_report_$(date +%Y%m%d).log 2>&1
echo "✅ Daily report done"
