#!/bin/bash
cd "$(dirname "$0")/.."
/usr/local/bin/python3 shopee_monitor.py --check growth >> logs/growth.log 2>&1
echo "✅ Growth check done"
