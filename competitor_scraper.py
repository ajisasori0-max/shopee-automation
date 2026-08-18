#!/usr/bin/env python3
"""
Shopee Competitor Scraper
Scrapes top search results for umbrella keywords on Shopee Indonesia.
Uses requests + BeautifulSoup (no browser needed for basic data).

Usage:
    python3 competitor_scraper.py
"""

import requests
import json
import sqlite3
import time
import re
from datetime import datetime
from pathlib import Path

WORKSPACE = Path("/Users/gerard/.openclaw/workspace/shopee-api-onboarding")
DB_PATH = WORKSPACE / "growth_data.db"

# Shopee Indonesia search API (public, no auth needed)
SEARCH_URL = "https://shopee.co.id/api/v4/search/search_items"

KEYWORDS = [
    "payung lipat",
    "payung anti uv",
    "payung murah",
    "payung otomatis",
    "payung golf",
    "payung besar",
    "payung anak",
    "payung motor"
]

def search_shopee(keyword, limit=20):
    """Search Shopee using their public API."""
    params = {
        "by": "relevancy",
        "keyword": keyword,
        "limit": limit,
        "newest": 0,
        "order": "desc",
        "page_type": "search",
        "scenario": "PAGE_GLOBAL_SEARCH",
        "version": "2"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": f"https://shopee.co.id/search?keyword={keyword.replace(' ', '%20')}"
    }
    
    try:
        resp = requests.get(SEARCH_URL, params=params, headers=headers, timeout=20)
        if resp.status_code != 200:
            print(f"  ⚠️  HTTP {resp.status_code} for '{keyword}'")
            return []
        
        data = resp.json()
        items = data.get("items", []) or []
        
        results = []
        for item in items:
            try:
                item_basic = item.get("item_basic", {})
                shop_info = item_basic.get("shop_info", {})
                
                # Extract price (in cents, convert to IDR)
                price = item_basic.get("price", 0) / 100000
                
                # Extract historical sales
                historical_sold = item_basic.get("historical_sold", 0)
                
                # Extract rating
                item_rating = item_basic.get("item_rating", {})
                rating_star = item_rating.get("rating_star", 0)
                rating_count = item_rating.get("rating_count", [0, 0, 0, 0, 0])
                total_reviews = sum(rating_count)
                
                results.append({
                    "shop_name": shop_info.get("shop_name", "Unknown"),
                    "product_name": item_basic.get("name", "Unnamed"),
                    "price": price,
                    "sales": historical_sold,
                    "rating": rating_star,
                    "reviews": total_reviews,
                    "location": shop_info.get("shop_location", "Unknown"),
                    "keyword": keyword,
                    "item_id": item_basic.get("itemid", 0),
                    "shop_id": item_basic.get("shopid", 0)
                })
            except Exception as e:
                continue
        
        return results
    except Exception as e:
        print(f"  ❌ Error searching '{keyword}': {e}")
        return []

def analyze_competitors():
    """Run full competitor analysis."""
    print("\n" + "="*70)
    print("🏆 COMPETITOR SCRAPER v1.0")
    print("="*70)
    
    conn = sqlite3.connect(DB_PATH)
    all_results = []
    
    for keyword in KEYWORDS:
        print(f"\n🔍 Searching: '{keyword}'")
        results = search_shopee(keyword, limit=15)
        print(f"  ✅ Found {len(results)} products")
        
        for r in results:
            all_results.append(r)
            conn.execute('''INSERT OR REPLACE INTO competitor_data
                (shop_name, product_name, price, sales, rating, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?)''',
                (r['shop_name'], r['product_name'], r['price'],
                 r['sales'], r['rating'], datetime.now().isoformat()))
        
        time.sleep(1)  # Be nice to Shopee
    
    conn.commit()
    
    # Analysis
    print("\n" + "="*70)
    print("📊 COMPETITOR ANALYSIS")
    print("="*70)
    
    # Top sellers by sales
    print("\n🏆 Top 10 Products by Sales:")
    sorted_by_sales = sorted(all_results, key=lambda x: x['sales'], reverse=True)[:10]
    for i, r in enumerate(sorted_by_sales, 1):
        print(f"   {i}. {r['product_name'][:45]}")
        print(f"      Price: Rp {r['price']:,.0f} | Sales: {r['sales']} | Rating: {r['rating']:.1f}★ | Shop: {r['shop_name'][:20]}")
    
    # Price distribution
    prices = [r['price'] for r in all_results if r['price'] > 0]
    if prices:
        avg_price = sum(prices) / len(prices)
        min_price = min(prices)
        max_price = max(prices)
        print(f"\n💰 Price Analysis ({len(prices)} products):")
        print(f"   Average: Rp {avg_price:,.0f}")
        print(f"   Range: Rp {min_price:,.0f} - Rp {max_price:,.0f}")
        print(f"   Sweet spot: Rp {avg_price * 0.9:,.0f} - Rp {avg_price * 1.1:,.0f}")
    
    # By keyword
    print(f"\n📋 Performance by Keyword:")
    for keyword in KEYWORDS:
        kw_results = [r for r in all_results if r['keyword'] == keyword]
        if kw_results:
            avg_price = sum(r['price'] for r in kw_results) / len(kw_results)
            total_sales = sum(r['sales'] for r in kw_results)
            print(f"   {keyword}: {len(kw_results)} products, avg Rp {avg_price:,.0f}, total {total_sales} sales")
    
    # Opportunities
    print(f"\n💡 Growth Opportunities:")
    if prices:
        print(f"   1. Price your payung lipat at Rp {sum(prices)/len(prices) * 0.95:,.0f} to be competitive")
        print(f"   2. Target keywords with lower competition but decent sales")
        avg_rating = sum(r['rating'] for r in all_results if r['rating'] > 0) / max(len([r for r in all_results if r['rating'] > 0]), 1)
        print(f"   3. Focus on ratings - competitors avg {avg_rating:.1f}★")
    else:
        print("   (No data collected - Shopee API returned 403)")
        print("   Alternative: Use Shopee Affiliate API or third-party tools")
        print("   Recommended: DataSpark, Sellercraft, or Minovel for competitor intel")
    
    conn.close()
    print(f"\n✅ Saved {len(all_results)} competitor records to database")

if __name__ == '__main__':
    analyze_competitors()
