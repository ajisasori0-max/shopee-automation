#!/usr/bin/env python3
"""
Shopee API Demo - Shows how to use the client for common operations.
Run this to explore your shop data and test APIs.
"""

from shopee_client import ShopeeClient
import json

# Initialize client (loads tokens automatically)
client = ShopeeClient(
    partner_id=1221616,
    partner_key="shpk4d6149704f516949617a70434a416a5a476e5349705473684b596a664c6f",
    shop_id=226682118,
    tokens_file="tokens.json",
    sandbox=True
)

print("=" * 60)
print("🦊 SHOPEE API DEMO")
print("=" * 60)

# 1. SHOP INFO
print("\n🏪 1. SHOP INFO")
print("-" * 40)
result = client.get_shop_info()
if result['ok']:
    shop = result['data']
    print(f"Name: {shop['shop_name']}")
    print(f"Region: {shop['region']}")
    print(f"Status: {shop['status']}")
else:
    print(f"Error: {result['data']}")

# 2. ADS - BALANCE & SETTINGS
print("\n💰 2. ADS - BALANCE & SETTINGS")
print("-" * 40)

result = client.get_ad_balance()
if result['ok']:
    balance = result['data'].get('response', {}).get('total_balance', 0)
    print(f"Ad Balance: {balance}")

result = client.get_ad_settings()
if result['ok']:
    settings = result['data'].get('response', {})
    print(f"Auto Top-up: {settings.get('top_up_toggle', False)}")
    print(f"Campaign Surge: {settings.get('campaign_surge', False)}")

# 3. ADS - PERFORMANCE (Last 7 days)
print("\n📊 3. ADS - PERFORMANCE (Last 7 days)")
print("-" * 40)

from datetime import datetime, timedelta
end_date = datetime.now().strftime('%Y-%m-%d')
start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

result = client.get_ad_performance_daily(start_date, end_date)
if result['ok']:
    perf = result['data'].get('response', {}).get('data_list', [])
    if perf:
        print(f"Found {len(perf)} days of data")
        for day in perf[:3]:  # Show first 3 days
            print(f"  {day.get('date')}: Spend={day.get('expenditure', 0)}, GMV={day.get('gmv', 0)}")
    else:
        print("No performance data (sandbox may not have historical data)")
else:
    print(f"No data or error: {result['data'].get('error', 'Unknown')}")

# 4. PRODUCT LIST
print("\n📦 4. PRODUCT LIST")
print("-" * 40)

result = client.get_product_list(page_size=10)
if result['ok']:
    items = result['data'].get('item', [])
    if items:
        print(f"Found {len(items)} products:")
        for item in items[:5]:  # Show first 5
            print(f"  • {item['item_name'][:30]}... (ID: {item['item_id']})")
    else:
        print("No products in shop.")
        print("💡 Tip: Create test products in Sandbox Seller Center first!")
        print("   https://seller.test-stable.shopee.co.id")
else:
    print(f"Error: {result['data'].get('error', 'Unknown')}")

# 5. EXAMPLE: How to use other APIs
print("\n📋 5. EXAMPLE CODE FOR YOUR APPS")
print("-" * 40)
print("""
# SELLER IN-HOUSE APP EXAMPLES:
# ------------------------------

# Update stock for item ID 12345:
# result = client.update_stock(item_id=12345, stock=100)

# Update price for item ID 12345:
# result = client.update_price(item_id=12345, price=50000)

# Get product details:
# result = client.get_product_detail(item_id=12345)

# ADS SERVICE APP EXAMPLES:
# -------------------------

# Get recommended keywords for a product:
# result = client.get_recommended_keywords(item_id=12345)

# Note: Create ad campaigns require more setup (product selection, 
# budget, ROAS targets). See Guide 19/20 for details.
""")

print("\n" + "=" * 60)
print("✅ DEMO COMPLETE!")
print("=" * 60)
print("\nNext steps:")
print("1. Create test products in Sandbox Seller Center")
print("2. Try: result = client.get_product_list()")
print("3. Try: result = client.update_stock(item_id=XXX, stock=100)")
