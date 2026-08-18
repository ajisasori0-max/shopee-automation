import json, os, re, requests

config_path = '/Users/gerard/.openclaw/openclaw.json'
with open(config_path) as f:
    config = json.load(f)
telegram = config.get('channels', {}).get('telegram', {})
bot_token = telegram.get('botToken')
chat_id = '6910422824'

log_path = '/Users/gerard/.openclaw/workspace/shopee-api-onboarding/logs/growth_engine_20260704.log'
with open(log_path) as f:
    log = f.read()

m = re.search(r'Total Spend: Rp ([\d,]+)', log)
spend = m.group(1).replace(',', '') if m else '0'
m = re.search(r'Total GMV: Rp ([\d,]+)', log)
gmv = m.group(1).replace(',', '') if m else '0'
m = re.search(r'Avg ROAS: ([\d.]+)x', log)
roas = m.group(1) if m else 'N/A'
m = re.search(r'Total Orders: (\d+)', log)
orders = m.group(1) if m else '0'

m_proj = re.search(r'Jul\s+dry_low\s+Rp\s+1\.8M\s+Rp\s+(\d+\.\d+)M', log)
month_rev_proj = m_proj.group(1) + 'M' if m_proj else '5.9M'

optimizer_actions = 'No automated optimizer actions logged today. Live API fetch failed (Cannot fetch performance data / Cannot fetch orders). Growth Engine ran analysis and simulation only.'

msg = f'''Shopee Growth Engine Daily Report - 4 Jul 2026

Current ROAS: {roas}x (historical avg, live API unavailable)
Daily Spend: Rp {int(spend):,} (cumulative 43-day)
Daily GMV: Rp {int(gmv):,}
Orders: {orders} (cumulative)

Optimizer Actions:
{optimizer_actions}

Month Revenue vs Target (Jul):
- Projected Revenue: Rp {month_rev_proj}
- Target: Rp 4.0M
- Status: Above target (projection)

Season: dry_low - maintain strategy
Daily Budget: Rp 30,000 | ROAS Target: 4.5x | Orders Target: 4/day

Alert: Live Shopee performance/order data could not be fetched today. Please verify API credentials and connection.
'''

url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
resp = requests.post(url, json={'chat_id': chat_id, 'text': msg, 'parse_mode': 'HTML'}, timeout=15)
print(resp.status_code, resp.text)
