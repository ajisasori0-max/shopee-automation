import json, requests

config_path = '/Users/gerard/.openclaw/openclaw.json'
with open(config_path) as f:
    config = json.load(f)
telegram = config.get('channels', {}).get('telegram', {})
bot_token = telegram.get('botToken')
chat_id = '6910422824'

msg = '''<b>Evening Check — 5 Jul 2026 20:00</b>

Status: Shopee API token invalid
Error: Invalid access_token (HTTP 403)

Ads performance data could not be fetched.
Action required: Re-authorize the Shopee app in Seller Centre to obtain a fresh token.'''

url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
resp = requests.post(url, json={'chat_id': chat_id, 'text': msg, 'parse_mode': 'HTML'}, timeout=15)
print(resp.status_code, resp.text)
