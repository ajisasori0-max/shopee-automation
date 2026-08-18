#!/bin/bash
cd "$(dirname "$0")/.."
/usr/local/bin/python3 full_automation.py >> logs/boost_$(date +%Y%m%d).log 2>&1
echo "✅ Boost check done"
