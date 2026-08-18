import json, requests
from datetime import datetime

config_path = '/Users/gerard/.openclaw/openclaw.json'
with open(config_path) as f:
    config = json.load(f)
telegram = config.get('channels', {}).get('telegram', {})
bot_token = telegram.get('botToken')
chat_id = '6910422824'

# Load last-known morning report
with open('/Users/gerard/.openclaw/workspace/shopee-api-onboarding/reports/ads_report_20260719_090003.json') as f:
    morning = json.load(f)

s = morning['summary']
today = datetime.now().strftime('%d %b %Y')

msg = f'''<b>⚠️ Midday Check — {today} 14:00</b>

<b>Status:</b> ADS API token expired (refresh_token rejected by Shopee)

<b>Last known (this morning 09:00):</b>
ROAS: {s['roas']:.2f}x | Spend: Rp {s['total_spend']:,} | GMV: Rp {s['total_gmv']:,}
CTR: {s['ctr']:.2f}% | Campaigns: {s['campaigns_count']}

<b>Seller app:</b> ✅ Still working (product boost ran at 14:00, 5 items boosted)

<b>Action required:</b> Re-authorize the ADS app in Shopee Seller Centre to obtain a fresh refresh_token. The Seller app (partner 2030653) is unaffected.

Re-auth URL (ADS app):
https://partner.shopeemobile.com/api/v2/shop/auth_partner?partner_id=2030650&timestamp=1784445078&sign=27c8942cf66c7d885d8d48a2176669c39d018ce7b35e7d83345e4e03dfaf67cf&redirect=https%3A%2F%2Fshopee-automation-70ts.onrender.com'''

url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
resp = requests.post(url, json={'chat_id': chat_id, 'text': msg, 'parse_mode': 'HTML'}, timeout=15)
print(resp.status_code, resp.text[:300])
