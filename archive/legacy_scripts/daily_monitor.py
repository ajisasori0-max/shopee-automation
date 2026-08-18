#!/usr/bin/env python3
"""
Shopee Daily Monitor v2.0
=========================
Comprehensive daily analytics: sales, ROAS, CPC, CTR, CPA, trends, campaigns.
Runs every morning at 8 AM.
Tries live Shopee API; falls back to historical database if API is unavailable.
Sends a Telegram summary after running.
"""

import requests
import hmac
import hashlib
import time
import json
import sqlite3
import os
import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path("/Users/gerard/.openclaw/workspace/shopee-api-onboarding")
DB_PATH = WORKSPACE / "growth_data.db"
REPORT_PATH = WORKSPACE / "daily_reports"
REPORT_PATH.mkdir(exist_ok=True)

from commerceos.platform.shopee_config import (
    get_seller_credentials,
    get_ads_credentials,
    get_telegram_credentials,
)

_seller = get_seller_credentials()
_ads = get_ads_credentials()
_telegram = get_telegram_credentials()

PARTNER_ID_SELLER = _seller["partner_id"]
PARTNER_KEY_SELLER = _seller["partner_key"]
PARTNER_ID_ADS = _ads["partner_id"]
PARTNER_KEY_ADS = _ads["partner_key"]
SHOP_ID = _seller["shop_id"]
BASE_URL = "https://partner.shopeemobile.com"
CHAT_ID = _telegram["chat_id"]


def send_telegram(message):
    """Send a Telegram message using the configured bot token."""
    try:
        bot_token = _telegram["bot_token"]
        if not bot_token:
            print("❌ Telegram bot token not found")
            return False
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code == 200:
            print("✅ Telegram summary sent")
            return True
        else:
            print(f"❌ Telegram error: {resp.text}")
            return False
    except Exception as e:
        print(f"❌ Telegram send failed: {e}")
        return False


class ShopeeAPI:
    def __init__(self, partner_id, partner_key, tokens_file):
        self.partner_id = partner_id
        self.partner_key = partner_key
        # Token management is centralized in token_manager.py via the
        # commerceos.platform.tokens provider. We only read a fresh access token
        # here; we never refresh or write token files ourselves.
        from commerceos.platform.tokens import app_name_for_partner_id, get_access_token
        self._app_name = app_name_for_partner_id(partner_id)
        self.access_token = get_access_token(self._app_name)
        self.tokens_file = WORKSPACE / tokens_file
        self._load_tokens_metadata()

    def _load_tokens_metadata(self):
        """Load non-secret metadata only (refresh logic is centralized)."""
        with open(self.tokens_file) as f:
            data = json.load(f)
            self.refresh_token = data.get("refresh_token", "")
            self.expire_time = time.time() + data.get("expire_in", 14400)

    def _refresh_if_needed(self, force=False):
        """DEPRECATED: Central token manager handles refresh.

        Kept for compatibility with callers, but the actual refresh is delegated
        to commerceos.platform.tokens.get_access_token on next request.
        """
        from commerceos.platform.tokens import get_access_token
        self.access_token = get_access_token(self._app_name)

    def _refresh(self):
        """DEPRECATED: Central token manager handles refresh."""
        self._refresh_if_needed(force=True)

    def _sign(self, path, ts):
        base = f"{self.partner_id}{path}{ts}{self.access_token}{SHOP_ID}"
        return hmac.new(self.partner_key.encode(), base.encode(), hashlib.sha256).hexdigest()

    def request(self, path, params=None, method="GET", body=None, _retried=False):
        self._refresh_if_needed()
        ts = int(time.time())
        sign = self._sign(path, ts)
        url = f"{BASE_URL}{path}"
        default = {
            "partner_id": self.partner_id,
            "timestamp": ts,
            "sign": sign,
            "access_token": self.access_token,
            "shop_id": SHOP_ID,
        }
        if params:
            default.update(params)
        try:
            if method == "POST":
                resp = requests.post(url, params=default, json=body, timeout=15)
            else:
                resp = requests.get(url, params=default, timeout=15)
            data = resp.json()
            # Retry once on auth error in case token was stale
            if not _retried and data.get("error") in ("invalid_acceess_token", "invalid_access_token", "error_auth"):
                print(f"  ⚠️  Auth error on {path}, forcing refresh and retrying...")
                self._refresh_if_needed(force=True)
                return self.request(path, params, method, body, _retried=True)
            return data
        except Exception as e:
            return {"error": str(e)}


def get_live_daily_performance(ads_api, days=14):
    end = datetime.now()
    start = end - timedelta(days=days)
    data = ads_api.request(
        "/api/v2/ads/get_all_cpc_ads_daily_performance",
        {"start_date": start.strftime("%d-%m-%Y"), "end_date": end.strftime("%d-%m-%Y")},
    )
    return data.get("response", [])


def get_live_campaigns(ads_api):
    data = ads_api.request(
        "/api/v2/ads/get_product_level_campaign_id_list",
        {"ad_type": "all", "offset": 0, "limit": 100},
    )
    if "response" in data and "campaign_list" in data["response"]:
        return list(data["response"]["campaign_list"])
    return []


def get_live_campaign_details(ads_api, campaign_id):
    data = ads_api.request(
        "/api/v2/ads/get_product_level_campaign_setting_info",
        {"campaign_id_list": str(campaign_id), "info_type_list": "1"},
    )
    if "response" in data and "campaign_list" in data["response"]:
        return data["response"]["campaign_list"][0]
    return None


def get_fallback_daily_data(days=14):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT date, spend, gmv, roas, orders, clicks, impressions, ctr
        FROM daily_performance
        ORDER BY date DESC
        LIMIT ?
    """,
        (days,),
    )
    rows = c.fetchall()
    conn.close()
    daily_data = []
    for row in rows:
        daily_data.append(
            {
                "date": row[0],
                "expense": row[1] or 0,
                "direct_gmv": row[2] or 0,
                "roas": row[3] or 0,
                "direct_order": row[4] or 0,
                "orders": row[4] or 0,
                "clicks": row[5] or 0,
                "impression": row[6] or 0,
                "views": row[6] or 0,
                "ctr": row[7] or 0,
            }
        )
    return daily_data


def calculate_metrics(daily_data):
    if not daily_data:
        return None
    total_spend = sum(d.get("expense", 0) for d in daily_data)
    total_gmv = sum(d.get("direct_gmv", 0) for d in daily_data)
    total_orders = sum(d.get("direct_order", 0) or d.get("orders", 0) for d in daily_data)
    total_clicks = sum(d.get("clicks", 0) for d in daily_data)
    total_impressions = sum(d.get("impression", 0) for d in daily_data)
    days = len(daily_data)
    metrics = {
        "days": days,
        "total_spend": total_spend,
        "total_gmv": total_gmv,
        "total_orders": total_orders,
        "total_clicks": total_clicks,
        "total_impressions": total_impressions,
        "avg_daily_spend": total_spend / days,
        "avg_daily_gmv": total_gmv / days,
        "avg_daily_orders": total_orders / days,
        "roas": total_gmv / total_spend if total_spend > 0 else 0,
        "ctr": (total_clicks / total_impressions * 100) if total_impressions > 0 else 0,
        "cpc": total_spend / total_clicks if total_clicks > 0 else 0,
        "cpa": total_spend / total_orders if total_orders > 0 else 0,
        "aov": total_gmv / total_orders if total_orders > 0 else 0,
        "cpm": (total_spend / total_impressions * 1000) if total_impressions > 0 else 0,
        "conversion_rate": (total_orders / total_clicks * 100) if total_clicks > 0 else 0,
    }
    if days >= 14:
        last_7 = daily_data[-7:]
        prev_7 = daily_data[-14:-7]
        metrics["last_7_spend"] = sum(d.get("expense", 0) for d in last_7)
        metrics["last_7_gmv"] = sum(d.get("direct_gmv", 0) for d in last_7)
        metrics["last_7_roas"] = metrics["last_7_gmv"] / metrics["last_7_spend"] if metrics["last_7_spend"] > 0 else 0
        metrics["last_7_orders"] = sum(d.get("direct_order", 0) or d.get("orders", 0) for d in last_7)
        metrics["prev_7_spend"] = sum(d.get("expense", 0) for d in prev_7)
        metrics["prev_7_gmv"] = sum(d.get("direct_gmv", 0) for d in prev_7)
        metrics["prev_7_roas"] = metrics["prev_7_gmv"] / metrics["prev_7_spend"] if metrics["prev_7_spend"] > 0 else 0
        metrics["prev_7_orders"] = sum(d.get("direct_order", 0) or d.get("orders", 0) for d in prev_7)
        metrics["roas_change"] = metrics["last_7_roas"] - metrics["prev_7_roas"]
        metrics["spend_change"] = metrics["last_7_spend"] - metrics["prev_7_spend"]
        metrics["orders_change"] = metrics["last_7_orders"] - metrics["prev_7_orders"]
    return metrics


def store_daily_data(conn, daily_data):
    c = conn.cursor()
    for day in daily_data:
        date_str = day.get("date", "")
        if not date_str:
            continue
        spend = day.get("expense", 0)
        gmv = day.get("direct_gmv", 0)
        orders = day.get("direct_order", 0) or day.get("orders", 0)
        clicks = day.get("clicks", 0)
        impressions = day.get("impression", 0)
        views = day.get("views", 0)
        roas = gmv / spend if spend > 0 else 0
        ctr = (clicks / impressions * 100) if impressions > 0 else 0
        c.execute(
            """INSERT OR REPLACE INTO daily_performance
            (date, spend, gmv, roas, orders, clicks, impressions, ctr, season)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (date_str, spend, gmv, roas, orders, clicks, impressions, ctr, "daily_monitor"),
        )
    conn.commit()


def format_daily_breakdown(daily_data):
    lines = []
    lines.append(f"\n   {'Date':<12} {'Spend':>10} {'GMV':>10} {'ROAS':>6} {'Orders':>7} {'CTR':>6}")
    lines.append("   " + "-" * 60)
    for d in daily_data:
        spend = d.get("expense", 0) or d.get("spend", 0)
        gmv = d.get("direct_gmv", 0) or d.get("gmv", 0)
        roas = d.get("roas", 0)
        orders = d.get("direct_order", 0) or d.get("orders", 0)
        ctr = d.get("ctr", 0)
        lines.append(f"   {d.get('date',''):<12} Rp {spend:>7,.0f} Rp {gmv:>7,.0f} {roas:>5.2f}x {orders:>6} {ctr:>5.2f}%")
    return "\n".join(lines)


def generate_report(metrics, campaigns, today_str, live_mode=False):
    report = []
    report.append("=" * 70)
    report.append(f"📊 DAILY MONITOR REPORT — {today_str}")
    if not live_mode:
        report.append("⚠️  FALLBACK MODE: API tokens expired or returned no data; using historical database")
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

    if "last_7_roas" in metrics:
        report.append("\n📈 7-DAY TREND (Last 7 vs Previous 7)")
        report.append(f"   ROAS:   {metrics['last_7_roas']:.2f}x vs {metrics['prev_7_roas']:.2f}x ({metrics['roas_change']:+.2f}x)")
        report.append(f"   Spend:  Rp {metrics['last_7_spend']:,.0f} vs Rp {metrics['prev_7_spend']:,.0f} ({metrics['spend_change']:+,.0f})")
        report.append(f"   Orders: {metrics['last_7_orders']} vs {metrics['prev_7_orders']} ({metrics['orders_change']:+})")
        if metrics["roas_change"] > 0.5:
            report.append("   ✅ ROAS IMPROVING")
        elif metrics["roas_change"] < -0.5:
            report.append("   ⚠️  ROAS DECLINING")
        else:
            report.append("   ✓ ROAS STABLE")

    total_budget = 0
    if campaigns:
        report.append(f"\n📋 ACTIVE CAMPAIGNS ({len(campaigns)})")
        for camp in campaigns:
            detail = camp.get("detail", {})
            common = detail.get("common_info", {}) if detail else {}
            budget = common.get("campaign_budget", 0)
            status = common.get("campaign_status", "unknown")
            name = common.get("ad_name", "Unnamed")
            if status == "ongoing":
                total_budget += budget
                report.append(f"   ✅ {name[:40]:<40} Rp {budget:>8,}")
        report.append(f"   {'':>40} Rp {total_budget:>8,} TOTAL")
    else:
        report.append("\n📋 ACTIVE CAMPAIGNS: No live campaign data available")

    report.append("\n🚦 STATUS")
    if metrics["roas"] >= 4.5:
        report.append("   ✅ ROAS ABOVE FLOOR (4.5x)")
    elif metrics["roas"] >= 4.0:
        report.append("   ⚠️  ROAS BELOW FLOOR (4.5x) — Monitor closely")
    else:
        report.append("   🚨 EMERGENCY: ROAS BELOW 4.0x — Consider budget cut")

    if not live_mode:
        report.append("\n🔧 TECHNICAL ALERT")
        report.append("   ❌ API tokens expired or no live data returned")
        report.append("   ❌ Manual OAuth re-authorization may be required")
        report.append("   ℹ️  Report generated from historical database (growth_data.db)")

    report.append("\n" + "=" * 70)
    return "\n".join(report)


def generate_telegram_summary(metrics, campaigns, today_str, live_mode=False):
    total_budget = 0
    ongoing = 0
    for camp in campaigns:
        detail = camp.get("detail", {})
        common = detail.get("common_info", {}) if detail else {}
        if common.get("campaign_status") == "ongoing":
            ongoing += 1
            total_budget += common.get("campaign_budget", 0)

    trend_symbol = "✅" if metrics.get("roas_change", 0) > 0.5 else ("🚨" if metrics.get("roas_change", 0) < -0.5 else "⚠️")
    status_symbol = "✅" if metrics["roas"] >= 4.5 else ("⚠️" if metrics["roas"] >= 4.0 else "🚨")

    msg = f"""🎯 <b>Shopee Daily Monitor — {today_str}</b>

<b>🎯 KEY METRICS (14d avg)</b>
💰 ROAS: {metrics['roas']:.2f}x {status_symbol}
💸 Daily Spend: Rp {metrics['avg_daily_spend']:,.0f}
🛒 Daily Orders: {metrics['avg_daily_orders']:.1f}
📊 CTR: {metrics['ctr']:.2f}%
💵 CPC: Rp {metrics['cpc']:,.0f}
🎯 CPA: Rp {metrics['cpa']:,.0f}
📦 AOV: Rp {metrics['aov']:,.0f}
🔄 Conv Rate: {metrics['conversion_rate']:.2f}%

<b>📈 7-DAY TREND</b>
{trend_symbol} ROAS: {metrics['last_7_roas']:.2f}x vs {metrics['prev_7_roas']:.2f}x ({metrics['roas_change']:+.2f}x)
💸 Spend: Rp {metrics['last_7_spend']:,.0f} vs Rp {metrics['prev_7_spend']:,.0f} ({metrics['spend_change']:+,.0f})
🛒 Orders: {metrics['last_7_orders']} vs {metrics['prev_7_orders']} ({metrics['orders_change']:+})

<b>📋 CAMPAIGNS</b>
Active: {ongoing} | Total Budget: Rp {total_budget:,.0f}
"""
    if not campaigns:
        msg += "⚠️ No live campaign data (API fallback)\n"

    msg += f"\n<b>🚦 STATUS ALERT</b>\n{status_symbol} "
    if metrics["roas"] >= 4.5:
        msg += "ROAS above floor (4.5x)"
    elif metrics["roas"] >= 4.0:
        msg += "ROAS below floor (4.5x) — monitor closely"
    else:
        msg += "EMERGENCY: ROAS below 4.0x — consider budget cut"

    if not live_mode:
        msg += "\n\n⚠️ <b>API FALLBACK</b>: Live data unavailable; summary from historical database."

    return msg


def main():
    print("=" * 70)
    print("📊 SHOPEE DAILY MONITOR v2.0")
    print("=" * 70)

    live_mode = False
    daily_data = []
    campaigns = []

    try:
        print("\n📡 Trying live API...")
        ads_api = ShopeeAPI(PARTNER_ID_ADS, PARTNER_KEY_ADS, "tokens_ads.json")
        seller_api = ShopeeAPI(PARTNER_ID_SELLER, PARTNER_KEY_SELLER, "tokens_production.json")
        daily_data = get_live_daily_performance(ads_api, days=14)
        if daily_data:
            live_mode = True
            campaigns_list = get_live_campaigns(ads_api)
            for camp in campaigns_list:
                camp_id = camp.get("campaign_id")
                detail = get_live_campaign_details(ads_api, camp_id)
                campaigns.append({"id": camp_id, "detail": detail})
            conn = sqlite3.connect(DB_PATH)
            store_daily_data(conn, daily_data)
            conn.close()
            print(f"✅ Live data fetched: {len(daily_data)} days")
        else:
            print("⚠️  Live API returned no data; using fallback")
    except Exception as e:
        print(f"⚠️  Live API error: {e}; using fallback")

    if not daily_data:
        daily_data = get_fallback_daily_data(days=14)

    metrics = calculate_metrics(daily_data)
    if not metrics:
        print("❌ No data available")
        sys.exit(1)

    today_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    report = generate_report(metrics, campaigns, today_str, live_mode=live_mode)

    report_file = REPORT_PATH / f"report_{datetime.now().strftime('%Y%m%d')}.txt"
    with open(report_file, "w") as f:
        f.write(report)

    print(report)
    print(f"\n💾 Report saved: {report_file}")

    telegram_msg = generate_telegram_summary(metrics, campaigns, today_str, live_mode=live_mode)
    send_telegram(telegram_msg)


if __name__ == "__main__":
    main()
