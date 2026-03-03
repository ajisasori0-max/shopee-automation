#!/bin/bash
# Shopee Automation Cron Setup
# Run this to set up all automation schedules

echo "🦊 Setting up Shopee Automation Cron Jobs..."

WORKSPACE="$HOME/.openclaw/workspace/shopee-api-onboarding"
PYTHON="python3"

# Create cron jobs
crontab -l > /tmp/current_crontab 2>/dev/null || touch /tmp/current_crontab

# Remove old entries
sed -i '/# Shopee Automation/d' /tmp/current_crontab
sed -i '/shopee_monitor/d' /tmp/current_crontab
sed -i '/monthly_report/d' /tmp/current_crontab

# Add new entries with comments
cat >> /tmp/current_crontab << EOF

# Shopee Automation - Stock Monitoring (Every 4 hours)
0 */4 * * * cd $WORKSPACE && $PYTHON $WORKSPACE/shopee_monitor.py --check stock >> $WORKSPACE/logs/stock.log 2>&1

# Shopee Automation - Order Monitoring (Every 6 hours)
0 */6 * * * cd $WORKSPACE && $PYTHON $WORKSPACE/shopee_monitor.py --check orders >> $WORKSPACE/logs/orders.log 2>&1

# Shopee Automation - Price Monitoring (Daily at 8 AM)
0 8 * * * cd $WORKSPACE && $PYTHON $WORKSPACE/shopee_monitor.py --check prices >> $WORKSPACE/logs/prices.log 2>&1

# Shopee Automation - Ad Monitoring (Daily at 9 AM)
0 9 * * * cd $WORKSPACE && $PYTHON $WORKSPACE/shopee_monitor.py --check ads >> $WORKSPACE/logs/ads.log 2>&1

# Shopee Automation - Sales Growth Insights (Daily at 10 AM)
0 10 * * * cd $WORKSPACE && $PYTHON $WORKSPACE/shopee_monitor.py --check growth >> $WORKSPACE/logs/growth.log 2>&1

# Shopee Automation - Full Check (Daily at 7 AM)
0 7 * * * cd $WORKSPACE && $PYTHON $WORKSPACE/shopee_monitor.py --check all >> $WORKSPACE/logs/daily.log 2>&1

# Shopee Automation - Monthly Report (29th of each month at 11:59 PM)
59 23 29 * * cd $WORKSPACE && $PYTHON $WORKSPACE/monthly_report.py >> $WORKSPACE/logs/monthly.log 2>&1
EOF

# Install new crontab
crontab /tmp/current_crontab

# Create logs directory
mkdir -p "$WORKSPACE/logs"

echo ""
echo "✅ Cron jobs installed!"
echo ""
echo "📋 Schedule Summary:"
echo "  • Stock Check: Every 4 hours (low stock alerts)"
echo "  • Order Check: Every 6 hours (returns/cancellations)"
echo "  • Price Check: Daily 8:00 AM"
echo "  • Ad Check: Daily 9:00 AM"
echo "  • Growth Insights: Daily 10:00 AM"
echo "  • Full Daily Report: Daily 7:00 AM"
echo "  • Monthly Report: 29th of each month, 11:59 PM"
echo ""
echo "📁 Logs saved to: $WORKSPACE/logs/"
echo ""
crontab -l | grep "Shopee Automation"
