#!/usr/bin/env python3
"""Generate comprehensive daily report from database fallback."""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path("/Users/gerard/.openclaw/workspace/shopee-api-onboarding")
DB_PATH = WORKSPACE / "growth_data.db"
REPORT_PATH = WORKSPACE / "daily_reports"
REPORT_PATH.mkdir(exist_ok=True)

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Get last 14 days of data
c.execute("""
    SELECT date, spend, gmv, roas, orders, clicks, impressions, ctr
    FROM daily_performance
    ORDER BY date DESC
    LIMIT 14
""")
rows = c.fetchall()

if not rows:
    print("No data in database")
    exit(1)

# Parse rows
daily_data = []
for row in rows:
    daily_data.append({
        'date': row[0],
        'spend': row[1] or 0,
        'gmv': row[2] or 0,
        'roas': row[3] or 0,
        'orders': row[4] or 0,
        'clicks': row[5] or 0,
        'impressions': row[6] or 0,
        'ctr': row[7] or 0,
    })

# Calculate metrics
total_spend = sum(d['spend'] for d in daily_data)
total_gmv = sum(d['gmv'] for d in daily_data)
total_orders = sum(d['orders'] for d in daily_data)
total_clicks = sum(d['clicks'] for d in daily_data)
total_impressions = sum(d['impressions'] for d in daily_data)
days = len(daily_data)

metrics = {
    'days': days,
    'total_spend': total_spend,
    'total_gmv': total_gmv,
    'total_orders': total_orders,
    'total_clicks': total_clicks,
    'total_impressions': total_impressions,
    'avg_daily_spend': total_spend / days,
    'avg_daily_gmv': total_gmv / days,
    'avg_daily_orders': total_orders / days,
    'roas': total_gmv / total_spend if total_spend > 0 else 0,
    'ctr': (total_clicks / total_impressions * 100) if total_impressions > 0 else 0,
    'cpc': total_spend / total_clicks if total_clicks > 0 else 0,
    'cpa': total_spend / total_orders if total_orders > 0 else 0,
    'aov': total_gmv / total_orders if total_orders > 0 else 0,
    'cpm': (total_spend / total_impressions * 1000) if total_impressions > 0 else 0,
    'conversion_rate': (total_orders / total_clicks * 100) if total_clicks > 0 else 0,
}

# 7-day comparison
if days >= 14:
    last_7 = daily_data[:7]
    prev_7 = daily_data[7:14]
    
    metrics['last_7_spend'] = sum(d['spend'] for d in last_7)
    metrics['last_7_gmv'] = sum(d['gmv'] for d in last_7)
    metrics['last_7_roas'] = metrics['last_7_gmv'] / metrics['last_7_spend'] if metrics['last_7_spend'] > 0 else 0
    metrics['last_7_orders'] = sum(d['orders'] for d in last_7)
    
    metrics['prev_7_spend'] = sum(d['spend'] for d in prev_7)
    metrics['prev_7_gmv'] = sum(d['gmv'] for d in prev_7)
    metrics['prev_7_roas'] = metrics['prev_7_gmv'] / metrics['prev_7_spend'] if metrics['prev_7_spend'] > 0 else 0
    metrics['prev_7_orders'] = sum(d['orders'] for d in prev_7)
    
    metrics['roas_change'] = metrics['last_7_roas'] - metrics['prev_7_roas']
    metrics['spend_change'] = metrics['last_7_spend'] - metrics['prev_7_spend']
    metrics['orders_change'] = metrics['last_7_orders'] - metrics['prev_7_orders']

# Generate report
report = []
report.append("=" * 70)
report.append(f"📊 DAILY MONITOR REPORT — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
report.append("⚠️  FALLBACK MODE: API tokens expired, using database historical data")
report.append("=" * 70)

report.append("\n🎯 KEY METRICS (Last 14 Days)")
report.append(f"   ROAS:        {metrics['roas']:.2f}x")
report.append(f"   Daily Spend: Rp {metrics['avg_daily_spend']:,.0f}")
report.append(f"   Daily GMV:   Rp {metrics['avg_daily_gmv']:,.0f}")
report.append(f"   Daily Orders: {metrics['avg_daily_orders']:.1f}")
report.append(f"   AOV:         Rp {metrics['aov']:,.0f}")
report.append(f"   CTR:         {metrics['ctr']:.2f}%")
report.append(f"   CPC:         Rp {metrics['cpc']:,.0f}")
report.append(f"   CPA:         Rp {metrics['cpa']:,.0f}")
report.append(f"   CPM:         Rp {metrics['cpm']:,.0f}")
report.append(f"   Conv Rate:   {metrics['conversion_rate']:.2f}%")

if 'last_7_roas' in metrics:
    report.append("\n📈 7-DAY TREND (Last 7 vs Previous 7)")
    report.append(f"   ROAS:   {metrics['last_7_roas']:.2f}x vs {metrics['prev_7_roas']:.2f}x ({metrics['roas_change']:+.2f}x)")
    report.append(f"   Spend:  Rp {metrics['last_7_spend']:,.0f} vs Rp {metrics['prev_7_spend']:,.0f} ({metrics['spend_change']:+,.0f})")
    report.append(f"   Orders: {metrics['last_7_orders']} vs {metrics['prev_7_orders']} ({metrics['orders_change']:+})")
    
    if metrics['roas_change'] > 0.5:
        report.append("   ✅ ROAS IMPROVING")
    elif metrics['roas_change'] < -0.5:
        report.append("   ⚠️  ROAS DECLINING")
    else:
        report.append("   ✓ ROAS STABLE")

# Daily breakdown
report.append("\n📅 DAILY BREAKDOWN (Last 14 Days)")
report.append(f"   {'Date':<12} {'Spend':>10} {'GMV':>10} {'ROAS':>6} {'Orders':>7} {'CTR':>6}")
report.append("   " + "-" * 60)
for d in daily_data:
    report.append(f"   {d['date']:<12} Rp {d['spend']:>7,.0f} Rp {d['gmv']:>7,.0f} {d['roas']:>5.2f}x {d['orders']:>6} {d['ctr']:>5.2f}%")

# Status
report.append("\n🚦 STATUS")
if metrics['roas'] >= 4.5:
    report.append("   ✅ ROAS ABOVE FLOOR (4.5x)")
elif metrics['roas'] >= 4.0:
    report.append("   ⚠️  ROAS BELOW FLOOR (4.5x) — Monitor closely")
else:
    report.append("   🚨 EMERGENCY: ROAS BELOW 4.0x — Consider budget cut")

report.append("\n🔧 TECHNICAL ALERT")
report.append("   ❌ API tokens expired — cannot fetch live campaign data")
report.append("   ❌ Manual OAuth re-authorization required")
report.append("   ℹ️  Report generated from historical database (growth_data.db)")
report.append("   ℹ️  Last live data: June 18, 2026 (ROAS 1.89x, EMERGENCY)")

report.append("\n" + "=" * 70)

report_text = "\n".join(report)
print(report_text)

# Save report
report_file = REPORT_PATH / f"report_{datetime.now().strftime('%Y%m%d')}.txt"
with open(report_file, 'w') as f:
    f.write(report_text)
print(f"\n💾 Report saved: {report_file}")

conn.close()
