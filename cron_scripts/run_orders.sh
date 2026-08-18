#!/bin/bash
cd "$(dirname "$0")/.."
/usr/local/bin/python3 shopee_monitor.py --check orders >> logs/orders.log 2>&1
echo "✅ Orders check done"
