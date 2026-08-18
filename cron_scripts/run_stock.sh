#!/bin/bash
cd "$(dirname "$0")/.."
/usr/local/bin/python3 shopee_monitor.py --check stock >> logs/stock.log 2>&1
echo "✅ Stock check done"
