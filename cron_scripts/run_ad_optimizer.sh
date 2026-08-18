#!/bin/bash
cd "$(dirname "$0")/.."
/usr/local/bin/python3 auto_optimizer.py >> logs/optimizer_$(date +%Y%m%d).log 2>&1
echo "✅ Ad optimizer done"
