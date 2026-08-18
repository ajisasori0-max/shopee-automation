#!/bin/bash
cd "$(dirname "$0")/.."
/usr/local/bin/python3 shopee_monitor.py --check prices >> logs/prices.log 2>&1
echo "✅ Price check done"
