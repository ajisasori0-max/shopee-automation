#!/bin/bash
cd "$(dirname "$0")/.."
/usr/local/bin/python3 monthly_report.py >> logs/monthly.log 2>&1
echo "✅ Monthly report done"
