#!/usr/bin/env python3
"""Exchange OAuth codes for both Seller and Ads tokens."""
import requests, hmac, hashlib, time, json

CODES = [
    "7a4a6f7574675a5742686f6e6447754c",
    "7656706a5a46647250656d696d6a4b73",
]

APPS = [
    {
        "name": "SELLER",
        "file": "tokens_production.json",
        "partner_id": 2030653,
        "partner_key": "shpk44444e634d6668466c5073776b45646454774a7975706d47497063526453",
    },
    {
        "name": "ADS",
        "file": "tokens_ads.json",
        "partner_id": 2030650,
        "partner_key": "shpk596a6556535573774b4e7742454a4f566e42794c7549736c4c59594c6a69",
    },
]

SHOP_ID = 1147948100
BASE_URL = "https://partner.shopeemobile.com"

results = []

for app in APPS:
    partner_id = app["partner_id"]
    partner_key = app["partner_key"]
    path = "/api/v2/auth/token/get"
    ts = int(time.time())
    base = f"{partner_id}{path}{ts}"
    sign = hmac.new(partner_key.encode(), base.encode(), hashlib.sha256).hexdigest()
    url = f"{BASE_URL}{path}?partner_id={partner_id}&timestamp={ts}&sign={sign}"

    for code in CODES:
        body = {"code": code, "shop_id": SHOP_ID, "partner_id": partner_id}
        try:
            resp = requests.post(url, json=body, timeout=60)
            data = resp.json()
        except Exception as e:
            results.append({"app": app["name"], "code": code, "error": str(e)})
            continue

        if resp.status_code == 200 and "access_token" in data:
            # Save token file
            out = {
                "partner_id": partner_id,
                "shop_id": SHOP_ID,
                "access_token": data["access_token"],
                "refresh_token": data["refresh_token"],
                "expire_in": data.get("expire_in", 14400),
                "request_id": data.get("request_id", ""),
            }
            with open(app["file"], "w") as f:
                json.dump(out, f, indent=2)
            results.append({
                "app": app["name"],
                "code": code,
                "status": "saved",
                "expires_in": data.get("expire_in", 14400),
            })
            break
        else:
            results.append({
                "app": app["name"],
                "code": code,
                "status": "failed",
                "response": data,
            })

print(json.dumps(results, indent=2))
