# Shopee Automation - Manual Cron Setup

## 🦊 Add These Lines to Your Crontab

Run: `crontab -e` and paste:

```bash
# Shopee Automation - Stock Monitoring (Every 4 hours)
0 */4 * * * cd $HOME/.openclaw/workspace/shopee-api-onboarding && python3 shopee_monitor.py --check stock >> $HOME/.openclaw/workspace/shopee-api-onboarding/logs/stock.log 2>&1

# Shopee Automation - Order Monitoring (Every 6 hours)
0 */6 * * * cd $HOME/.openclaw/workspace/shopee-api-onboarding && python3 shopee_monitor.py --check orders >> $HOME/.openclaw/workspace/shopee-api-onboarding/logs/orders.log 2>&1

# Shopee Automation - Price Monitoring (Daily at 8 AM)
0 8 * * * cd $HOME/.openclaw/workspace/shopee-api-onboarding && python3 shopee_monitor.py --check prices >> $HOME/.openclaw/workspace/shopee-api-onboarding/logs/prices.log 2>&1

# Shopee Automation - Ad Monitoring (Daily at 9 AM)
0 9 * * * cd $HOME/.openclaw/workspace/shopee-api-onboarding && python3 shopee_monitor.py --check ads >> $HOME/.openclaw/workspace/shopee-api-onboarding/logs/ads.log 2>&1

# Shopee Automation - Sales Growth Insights (Daily at 10 AM)
0 10 * * * cd $HOME/.openclaw/workspace/shopee-api-onboarding && python3 shopee_monitor.py --check growth >> $HOME/.openclaw/workspace/shopee-api-onboarding/logs/growth.log 2>&1

# Shopee Automation - Full Check (Daily at 7 AM)
0 7 * * * cd $HOME/.openclaw/workspace/shopee-api-onboarding && python3 shopee_monitor.py --check all >> $HOME/.openclaw/workspace/shopee-api-onboarding/logs/daily.log 2>&1

# Shopee Automation - Monthly Report (29th of each month at 11:59 PM)
59 23 29 * * cd $HOME/.openclaw/workspace/shopee-api-onboarding && python3 monthly_report.py >> $HOME/.openclaw/workspace/shopee-api-onboarding/logs/monthly.log 2>&1
```

## 📋 Quick Commands

```bash
# Test stock check immediately
python3 shopee_monitor.py --check stock

# Test all checks
python3 shopee_monitor.py --check all

# Generate monthly report
python3 monthly_report.py

# View logs
tail -f logs/stock.log
tail -f logs/daily.log

# Check cron is running
crontab -l
```

## 🚨 Stock Alert Levels

| Stock Level | Status | Action |
|-------------|--------|--------|
| 106+ | ✅ Healthy | No alert |
| 102-105 | ⚠️ Warning | Alert once, re-alert if drops further |
| ≤101 | 🚨 Critical | Immediate alert |

## 📊 What Gets Monitored

1. **Stock** (Every 4h)
   - Tracks all product variants
   - Alerts at 105 and 101 thresholds
   - Prevents duplicate alerts

2. **Returns/Cancellations** (Every 6h)
   - IN_CANCEL status
   - CANCELLED orders
   - TO_RETURN / RETURNED

3. **Price Changes** (Daily 8 AM)
   - Tracks price modifications
   - Shows increase/decrease amounts

4. **Ad Performance** (Daily 9 AM)
   - Balance check
   - ROAS monitoring
   - Spend vs GMV

5. **Growth Insights** (Daily 10 AM)
   - Order trends
   - Sales tips
   - Actionable recommendations

6. **Monthly Report** (29th, 11:59 PM)
   - Total revenue
   - Order summary
   - Ad performance
   - Financial statement

## 🛠️ Customization

### Add More Products to Stock Check

Edit `shopee_monitor.py` line ~15:
```python
known_products = [844121225, 123456789, 987654321]  # Add your product IDs
```

### Change Alert Thresholds

Edit `automation.py` lines ~95-105:
```python
if stock <= 101:  # Change to your threshold
    # Critical
elif stock <= 105:  # Change to your threshold
    # Warning
```

### Add Telegram Notifications

Edit `shopee_monitor.py` to send Telegram messages when alerts trigger.

## 📁 Log Files

All logs saved to: `logs/`
- `stock.log` - Stock alerts
- `orders.log` - Returns/cancellations
- `prices.log` - Price changes
- `ads.log` - Ad performance
- `growth.log` - Growth insights
- `daily.log` - Full daily reports
- `monthly.log` - Monthly reports
