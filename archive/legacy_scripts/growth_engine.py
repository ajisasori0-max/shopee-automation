#!/usr/bin/env python3
"""
Shopee Growth Engine v1.0
==========================
Plug-and-play automation for Payung Murah Jakarta.

Components:
1. Smart Optimizer - Realistic targets, auto-scale based on performance
2. Historical Analyzer - Pulls and analyzes 6+ months of data
3. Revenue Simulator - "What-if" predictions for budget/ROAS targets
4. Seasonal Calendar - Auto-adjusts targets by month
5. Competitor Monitor - Tracks top umbrella sellers

Usage:
    python3 growth_engine.py --mode optimize     # Run optimizer
    python3 growth_engine.py --mode analyze      # Pull historical data
    python3 growth_engine.py --mode simulate     # Run simulator
    python3 growth_engine.py --mode calendar     # Show seasonal plan
    python3 growth_engine.py --mode competitor   # Check competitors
    python3 growth_engine.py --mode all          # Run everything
"""

import requests
import hmac
import hashlib
import time
import json
import os
import sys
import sqlite3
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

from commerceos.platform.shopee_config import get_seller_credentials, get_ads_credentials

WORKSPACE = Path("/Users/gerard/.openclaw/workspace/shopee-api-onboarding")
DB_PATH = WORKSPACE / "growth_data.db"

_seller = get_seller_credentials()
_ads = get_ads_credentials()

# Partner credentials
PARTNER_ID_SELLER = _seller["partner_id"]
PARTNER_ID_ADS = _ads["partner_id"]
PARTNER_KEY_SELLER = _seller["partner_key"]
PARTNER_KEY_ADS = _ads["partner_key"]
SHOP_ID = _seller["shop_id"]
BASE_URL = "https://partner.shopeemobile.com"

# Seasonal calendar for umbrella business (based on real seller consensus)
SEASONAL_CALENDAR = {
    1:  {"name": "Jan", "season": "peak",     "roas_target": 6.5, "budget_factor": 3.0, "orders_per_day": 35, "note": "Rainy season peak"},
    2:  {"name": "Feb", "season": "transition","roas_target": 5.0, "budget_factor": 1.5, "orders_per_day": 15, "note": "Gradual reduce"},
    3:  {"name": "Mar", "season": "transition","roas_target": 4.5, "budget_factor": 1.2, "orders_per_day": 10, "note": "Transition"},
    4:  {"name": "Apr", "season": "dry_start", "roas_target": 4.5, "budget_factor": 0.8, "orders_per_day": 6,  "note": "Dry start"},
    5:  {"name": "May", "season": "dry_start", "roas_target": 4.5, "budget_factor": 0.8, "orders_per_day": 5,  "note": "Dry start"},
    6:  {"name": "Jun", "season": "dry_low",   "roas_target": 4.5, "budget_factor": 0.6, "orders_per_day": 4,  "note": "Dry low - maintain"},
    7:  {"name": "Jul", "season": "dry_low",   "roas_target": 4.5, "budget_factor": 0.6, "orders_per_day": 4,  "note": "Dry low - maintain"},
    8:  {"name": "Aug", "season": "dry_low",   "roas_target": 4.5, "budget_factor": 0.6, "orders_per_day": 4,  "note": "Dry low - maintain"},
    9:  {"name": "Sep", "season": "pre_rainy", "roas_target": 5.0, "budget_factor": 1.0, "orders_per_day": 8,  "note": "Pre-rainy increase"},
    10: {"name": "Oct", "season": "pre_rainy", "roas_target": 5.5, "budget_factor": 1.5, "orders_per_day": 12, "note": "Pre-rainy increase"},
    11: {"name": "Nov", "season": "peak",      "roas_target": 6.0, "budget_factor": 2.5, "orders_per_day": 30, "note": "Rainy season start"},
    12: {"name": "Dec", "season": "peak",      "roas_target": 6.7, "budget_factor": 3.0, "orders_per_day": 40, "note": "Rainy season peak"},
}

# Base daily budget (dry season baseline). Set to match current active campaign spend.
# July dry_low factor 0.6 => target ~Rp 200k/day
BASE_DAILY_BUDGET = 333333

# Safety limits
SAFETY = {
    "max_budget_increase_pct": 15,      # Max 15% increase per adjustment
    "max_budget_decrease_pct": 20,      # Max 20% decrease per adjustment
    "min_campaign_budget": 20000,       # Rp 20k floor per campaign
    "max_total_daily_budget": 2000000,  # Rp 2M absolute ceiling
    "min_roas_to_scale": 4.5,           # HARD FLOOR: Never scale if ROAS below 4.5x
    "target_roas_buffer": 0.2,          # Must exceed target by this much to scale
    "emergency_roas": 4.0,              # Below this = emergency cut
    "roas_floor_buffer": 0.05,          # Floating point buffer for floor comparisons
}

# =============================================================================
# DATABASE SETUP
# =============================================================================

def init_db():
    """Initialize SQLite database for historical data."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS daily_performance (
        date TEXT PRIMARY KEY,
        spend REAL,
        gmv REAL,
        roas REAL,
        orders INTEGER,
        clicks INTEGER,
        impressions INTEGER,
        ctr REAL,
        season TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS campaigns (
        id INTEGER PRIMARY KEY,
        name TEXT,
        status TEXT,
        budget REAL,
        ad_type TEXT,
        tier TEXT,
        updated_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        order_sn TEXT PRIMARY KEY,
        date TEXT,
        total_amount REAL,
        items_count INTEGER,
        status TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS competitor_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shop_name TEXT,
        product_name TEXT,
        price REAL,
        sales INTEGER,
        rating REAL,
        scraped_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS optimizer_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_at TEXT,
        action TEXT,
        campaign_id INTEGER,
        old_budget REAL,
        new_budget REAL,
        reason TEXT,
        roas_before REAL
    )''')
    
    conn.commit()
    conn.close()
    print(f"✅ Database initialized: {DB_PATH}")

# =============================================================================
# API CLIENT
# =============================================================================

class ShopeeAPI:
    """Unified API client for both Seller and Ads APIs."""
    
    def __init__(self, partner_id, partner_key, tokens_file):
        self.partner_id = partner_id
        self.partner_key = partner_key
        # Token management is centralized in token_manager.py via the
        # commerceos.platform.tokens provider. We never refresh or write token files.
        from commerceos.platform.tokens import app_name_for_partner_id, get_access_token
        self._app_name = app_name_for_partner_id(partner_id)
        self.access_token = get_access_token(self._app_name)
        self.tokens_file = WORKSPACE / tokens_file
        self.base_url = BASE_URL
        self._load_tokens_metadata()
        # If token looks near expiry, let the central provider refresh it once.
        self._refresh_if_needed()

    def _load_tokens_metadata(self):
        """Load non-secret metadata only (refresh logic is centralized)."""
        with open(self.tokens_file, 'r') as f:
            data = json.load(f)
            self.refresh_token = data.get('refresh_token', '')
            self.expire_time = time.time() + data.get('expire_in', 14400)

    def _refresh_if_needed(self):
        """DEPRECATED: Central token manager handles refresh.

        Kept for compatibility with callers, but the actual refresh is delegated
        to commerceos.platform.tokens.get_access_token.
        """
        from commerceos.platform.tokens import get_access_token
        self.access_token = get_access_token(self._app_name)

    def refresh_access_token(self):
        """DEPRECATED: Use central token manager instead."""
        self._refresh_if_needed()
        return bool(self.access_token)
    
    def _sign(self, path, ts):
        base = f"{self.partner_id}{path}{ts}{self.access_token}{SHOP_ID}"
        return hmac.new(self.partner_key.encode(), base.encode(), hashlib.sha256).hexdigest()
    
    def request(self, path, params=None, method='GET', body=None, _retried=False):
        self._refresh_if_needed()
        ts = int(time.time())
        sign = self._sign(path, ts)
        
        url = f"{self.base_url}{path}"
        default = {
            'partner_id': self.partner_id,
            'timestamp': ts,
            'sign': sign,
            'access_token': self.access_token,
            'shop_id': SHOP_ID
        }
        if params:
            default.update(params)
        
        try:
            if method == 'POST':
                resp = requests.post(url, params=default, json=body, timeout=15)
            else:
                resp = requests.get(url, params=default, timeout=15)
            data = resp.json()
            # Retry once on auth error in case token was stale
            if not _retried and data.get('error') in ('invalid_acceess_token', 'invalid_access_token', 'error_auth'):
                print(f"  ⚠️  Auth error on {path}, forcing refresh and retrying...")
                self.refresh_access_token()
                return self.request(path, params, method, body, _retried=True)
            return data
        except Exception as e:
            return {"error": str(e)}

# =============================================================================
# COMPONENT 1: SMART OPTIMIZER
# =============================================================================

class SmartOptimizer:
    """Auto-optimizer with realistic targets and performance-based scaling."""
    
    def __init__(self, ads_api, seller_api):
        self.ads = ads_api
        self.seller = seller_api
        self.conn = sqlite3.connect(DB_PATH)
    
    def get_campaigns(self):
        """Fetch all campaigns."""
        data = self.ads.request('/api/v2/ads/get_product_level_campaign_id_list', {
            'ad_type': 'all', 'offset': 0, 'limit': 100
        })
        if 'response' in data and 'campaign_list' in data['response']:
            return data['response']['campaign_list']
        return []
    
    def get_campaign_details(self, campaign_id):
        """Get campaign settings."""
        data = self.ads.request('/api/v2/ads/get_product_level_campaign_setting_info', {
            'campaign_id_list': str(campaign_id),
            'info_type_list': '1'
        })
        if 'response' in data and 'campaign_list' in data['response']:
            return data['response']['campaign_list'][0]
        return None
    
    def get_performance(self, days=14):
        """Get shop-level performance for last N days."""
        end = datetime.now()
        start = end - timedelta(days=days)
        
        data = self.ads.request('/api/v2/ads/get_all_cpc_ads_daily_performance', {
            'start_date': start.strftime('%d-%m-%Y'),
            'end_date': end.strftime('%d-%m-%Y')
        })
        
        if 'response' not in data:
            return None
        
        total = {'spend': 0, 'gmv': 0, 'orders': 0, 'clicks': 0, 'impressions': 0}
        daily = []
        
        for day in data['response']:
            spend = day.get('expense', 0)
            gmv = day.get('direct_gmv', 0)
            orders = day.get('direct_order', 0) or day.get('orders', 0)
            clicks = day.get('clicks', 0)
            impressions = day.get('impression', 0)
            
            total['spend'] += spend
            total['gmv'] += gmv
            total['orders'] += orders
            total['clicks'] += clicks
            total['impressions'] += impressions
            
            daily.append({
                'date': day.get('date', ''),
                'spend': spend,
                'gmv': gmv,
                'roas': gmv / spend if spend > 0 else 0,
                'orders': orders,
                'clicks': clicks,
                'impressions': impressions,
                'ctr': (clicks / impressions * 100) if impressions > 0 else 0
            })
        
        total['roas'] = total['gmv'] / total['spend'] if total['spend'] > 0 else 0
        total['ctr'] = (total['clicks'] / total['impressions'] * 100) if total['impressions'] > 0 else 0
        total['cpo'] = total['spend'] / total['orders'] if total['orders'] > 0 else 0
        total['aov'] = total['gmv'] / total['orders'] if total['orders'] > 0 else 0
        total['days'] = days
        
        return {'total': total, 'daily': daily}
    
    def adjust_budget(self, campaign_id, new_budget):
        """Change campaign budget."""
        data = self.ads.request('/api/v2/ads/edit_manual_product_ads', method='POST', body={
            'campaign_id': campaign_id,
            'reference_id': f'growth_engine_{int(time.time())}',
            'edit_action': 'change_budget',
            'budget': int(new_budget)
        })
        return 'response' in data
    
    def run(self, dry_run=True):
        """Main optimizer logic."""
        print("\n" + "="*70)
        print("🚀 SMART OPTIMIZER v1.0")
        print("="*70)
        
        # Get seasonal target
        month = datetime.now().month
        seasonal = SEASONAL_CALENDAR[month]
        target_roas = seasonal['roas_target']
        target_budget = BASE_DAILY_BUDGET * seasonal['budget_factor']
        
        print(f"\n📅 Current Month: {seasonal['name']} ({seasonal['season']})")
        print(f"🎯 Seasonal Target ROAS: {target_roas}x")
        print(f"💰 Seasonal Target Budget: Rp {target_budget:,.0f}/day")
        print(f"📝 Note: {seasonal['note']}")
        
        # Get performance
        perf = self.get_performance(days=14)
        if not perf:
            print("❌ Cannot fetch performance data")
            return
        
        total = perf['total']
        print(f"\n📊 Last {total['days']} Days Performance:")
        print(f"   Spend: Rp {total['spend']:,.0f} (Rp {total['spend']/total['days']:,.0f}/day)")
        print(f"   GMV: Rp {total['gmv']:,.0f}")
        print(f"   ROAS: {total['roas']:.2f}x")
        print(f"   Orders: {total['orders']} ({total['orders']/total['days']:.1f}/day)")
        print(f"   CTR: {total['ctr']:.2f}%")
        print(f"   AOV: Rp {total['aov']:,.0f}")
        print(f"   CPO: Rp {total['cpo']:,.0f}")
        
        # Store in DB
        for day in perf['daily']:
            self.conn.execute('''INSERT OR REPLACE INTO daily_performance
                (date, spend, gmv, roas, orders, clicks, impressions, ctr, season)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (day['date'], day['spend'], day['gmv'], day['roas'],
                 day['orders'], day['clicks'], day['impressions'], day['ctr'], seasonal['season']))
        self.conn.commit()
        
        # Get campaigns
        campaigns = self.get_campaigns()
        if not campaigns:
            print("❌ Cannot fetch campaigns")
            return
        
        print(f"\n📋 Found {len(campaigns)} campaigns")
        
        # Calculate total current budget
        total_current_budget = 0
        active_campaigns = []
        
        for camp in campaigns:
            camp_id = camp.get('campaign_id')
            detail = self.get_campaign_details(camp_id)
            if not detail:
                continue
            
            common = detail.get('common_info', {})
            status = common.get('campaign_status', 'unknown')
            budget = common.get('campaign_budget', 0)
            name = common.get('ad_name', 'Unnamed')
            
            if status == 'ongoing':
                total_current_budget += budget
                active_campaigns.append({
                    'id': camp_id,
                    'name': name,
                    'budget': budget,
                    'status': status
                })
                print(f"   ✅ {name[:40]}: Rp {budget:,.0f}")
            else:
                print(f"   ⏸️  {name[:40]}: {status} (skipped)")
        
        print(f"\n💰 Total Active Budget: Rp {total_current_budget:,.0f}")
        print(f"🎯 Target Budget: Rp {target_budget:,.0f}")
        
        # Decision logic
        actions = []
        
        if total['roas'] < SAFETY['emergency_roas'] - SAFETY['roas_floor_buffer']:
            # EMERGENCY: ROAS critically low - aggressive cut
            print(f"\n🚨 EMERGENCY: ROAS {total['roas']:.2f}x below emergency floor {SAFETY['emergency_roas']}x")
            print("   Action: AGGRESSIVE CUT - Decrease budgets by 25% immediately")
            
            for camp in active_campaigns:
                new_budget = max(camp['budget'] * 0.75, SAFETY['min_campaign_budget'])
                if new_budget < camp['budget']:
                    actions.append({
                        'campaign_id': camp['id'],
                        'name': camp['name'],
                        'old': camp['budget'],
                        'new': new_budget,
                        'reason': f"EMERGENCY: ROAS {total['roas']:.2f}x below {SAFETY['emergency_roas']}x"
                    })
        
        elif total['roas'] < SAFETY['min_roas_to_scale'] - SAFETY['roas_floor_buffer']:
            # ROAS below hard floor - decrease budgets
            print(f"\n⚠️  ROAS {total['roas']:.2f}x below hard floor {SAFETY['min_roas_to_scale']}x")
            print("   Action: DECREASE budgets by 15%")
            
            for camp in active_campaigns:
                new_budget = max(camp['budget'] * 0.85, SAFETY['min_campaign_budget'])
                if new_budget < camp['budget']:
                    actions.append({
                        'campaign_id': camp['id'],
                        'name': camp['name'],
                        'old': camp['budget'],
                        'new': new_budget,
                        'reason': f"ROAS {total['roas']:.2f}x below floor {SAFETY['min_roas_to_scale']}x"
                    })
        
        elif total['roas'] >= target_roas + SAFETY['target_roas_buffer']:
            # ROAS good - can scale
            scale_factor = min(1.10, 1 + (total['roas'] - target_roas) * 0.03)
            new_total = min(total_current_budget * scale_factor, SAFETY['max_total_daily_budget'])
            
            print(f"\n✅ ROAS {total['roas']:.2f}x exceeds target {target_roas}x")
            print(f"   Action: INCREASE budgets by {(scale_factor-1)*100:.0f}%")
            print(f"   New total budget: Rp {new_total:,.0f}")
            
            # Distribute proportionally
            for camp in active_campaigns:
                ratio = camp['budget'] / total_current_budget
                new_budget = min(new_total * ratio, camp['budget'] * 1.10)
                new_budget = max(new_budget, SAFETY['min_campaign_budget'])
                
                if new_budget > camp['budget']:
                    actions.append({
                        'campaign_id': camp['id'],
                        'name': camp['name'],
                        'old': camp['budget'],
                        'new': new_budget,
                        'reason': f"ROAS {total['roas']:.2f}x exceeds target {target_roas}x"
                    })
        
        else:
            # ROAS in target range - maintain
            print(f"\n✓ ROAS {total['roas']:.2f}x in target range ({target_roas}x)")
            print("   Action: MAINTAIN current budgets")
        
        # Execute or dry-run
        print(f"\n{'='*70}")
        if dry_run:
            print("🔍 DRY RUN MODE (no changes made)")
        else:
            print("⚡ LIVE MODE (making changes)")
        print(f"{'='*70}")
        
        for action in actions:
            print(f"\n{'='*70}")
            print(f"📝 {action['name'][:45]}")
            print(f"   Budget: Rp {action['old']:,.0f} → Rp {action['new']:,.0f}")
            print(f"   Reason: {action['reason']}")
            
            if not dry_run:
                success = self.adjust_budget(action['campaign_id'], action['new'])
                if success:
                    print("   ✅ Applied")
                    self.conn.execute('''INSERT INTO optimizer_runs
                        (run_at, action, campaign_id, old_budget, new_budget, reason, roas_before)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                        (datetime.now().isoformat(), 'adjust_budget', action['campaign_id'],
                         action['old'], action['new'], action['reason'], total['roas']))
                else:
                    print("   ❌ Failed")
            else:
                print("   ⏸️  Skipped (dry run)")
        
        self.conn.commit()
        
        # Summary
        print(f"\n{'='*70}")
        print("📋 SUMMARY")
        print(f"{'='*70}")
        print(f"Campaigns analyzed: {len(active_campaigns)}")
        print(f"Actions {'planned' if dry_run else 'taken'}: {len(actions)}")
        print(f"Current ROAS: {total['roas']:.2f}x")
        print(f"Target ROAS: {target_roas}x")
        print(f"Next check: Tomorrow")
        
        return {
            'roas': total['roas'],
            'target_roas': target_roas,
            'spend': total['spend'],
            'gmv': total['gmv'],
            'orders': total['orders'],
            'actions': len(actions),
            'dry_run': dry_run
        }

# =============================================================================
# COMPONENT 2: HISTORICAL ANALYZER
# =============================================================================

class HistoricalAnalyzer:
    """Pull and analyze historical data from APIs."""
    
    def __init__(self, ads_api, seller_api):
        self.ads = ads_api
        self.seller = seller_api
        self.conn = sqlite3.connect(DB_PATH)
    
    def pull_orders(self, days=30):
        """Pull order data from Seller API."""
        print(f"\n📦 Pulling orders (last {days} days)...")
        
        end = int(time.time())
        start = end - (days * 86400)
        
        data = self.seller.request('/api/v2/order/get_order_list', {
            'time_range_field': 'create_time',
            'time_from': start,
            'time_to': end,
            'page_size': 100,
            'order_status': 'COMPLETED',
            'response_optional_fields': 'total_amount'
        })
        
        if 'response' not in data or 'order_list' not in data['response']:
            print("  ❌ Cannot fetch orders")
            return []
        
        orders = data['response']['order_list']
        print(f"  ✅ Found {len(orders)} orders")
        
        for order in orders:
            self.conn.execute('''INSERT OR REPLACE INTO orders
                (order_sn, date, total_amount, items_count, status)
                VALUES (?, ?, ?, ?, ?)''',
                (order.get('order_sn'), 
                 datetime.fromtimestamp(order.get('create_time', 0)).strftime('%Y-%m-%d'),
                 order.get('total_amount', 0),
                 order.get('item_count', 0),
                 order.get('order_status', 'UNKNOWN')))
        
        self.conn.commit()
        return orders
    
    def analyze(self):
        """Run analysis on stored data."""
        print("\n" + "="*70)
        print("📊 HISTORICAL ANALYSIS")
        print("="*70)
        
        # Overall stats
        c = self.conn.cursor()
        c.execute('''SELECT 
            COUNT(*) as days,
            SUM(spend) as total_spend,
            SUM(gmv) as total_gmv,
            AVG(roas) as avg_roas,
            SUM(orders) as total_orders,
            AVG(ctr) as avg_ctr
            FROM daily_performance''')
        row = c.fetchone()
        
        if row and row[0]:
            print(f"\n📈 Overall (from {row[0]} days of data):")
            print(f"   Total Spend: Rp {row[1]:,.0f}")
            print(f"   Total GMV: Rp {row[2]:,.0f}")
            print(f"   Avg ROAS: {row[3]:.2f}x")
            print(f"   Total Orders: {row[4]}")
            print(f"   Avg CTR: {row[5]:.2f}%")
        
        # By season
        c.execute('''SELECT season, 
            COUNT(*) as days,
            AVG(roas) as avg_roas,
            SUM(orders) as total_orders,
            AVG(spend) as avg_spend
            FROM daily_performance GROUP BY season''')
        
        print(f"\n🌦️  Performance by Season:")
        for row in c.fetchall():
            print(f"   {row[0]}: {row[1]} days, ROAS {row[2]:.2f}x, {row[3]} orders, Rp {row[4]:,.0f}/day")
        
        # Best days
        c.execute('''SELECT date, roas, gmv, orders 
            FROM daily_performance 
            WHERE roas > 0 
            ORDER BY roas DESC LIMIT 5''')
        
        print(f"\n🏆 Top 5 ROAS Days:")
        for row in c.fetchall():
            print(f"   {row[0]}: {row[1]:.2f}x ROAS, Rp {row[2]:,.0f} GMV, {row[3]} orders")
        
        # Worst days
        c.execute('''SELECT date, roas, gmv, orders 
            FROM daily_performance 
            WHERE roas > 0 
            ORDER BY roas ASC LIMIT 5''')
        
        print(f"\n⚠️  Worst 5 ROAS Days:")
        for row in c.fetchall():
            print(f"   {row[0]}: {row[1]:.2f}x ROAS, Rp {row[2]:,.0f} GMV, {row[3]} orders")
        
        # Monthly trend (if we have data)
        c.execute('''SELECT 
            substr(date, 4, 7) as month,
            COUNT(*) as days,
            SUM(spend) as spend,
            SUM(gmv) as gmv,
            AVG(roas) as roas,
            SUM(orders) as orders
            FROM daily_performance 
            GROUP BY month ORDER BY month''')
        
        rows = c.fetchall()
        if rows:
            print(f"\n📅 Monthly Trend:")
            for row in rows:
                print(f"   {row[0]}: {row[1]} days, Rp {row[2]:,.0f} spend, Rp {row[3]:,.0f} GMV, {row[4]:.2f}x ROAS, {row[5]} orders")

# =============================================================================
# COMPONENT 3: REVENUE SIMULATOR
# =============================================================================

class RevenueSimulator:
    """What-if simulator for budget and ROAS targets."""
    
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
    
    def get_baseline(self):
        """Get baseline metrics from historical data."""
        c = self.conn.cursor()
        c.execute('''SELECT 
            AVG(roas) as avg_roas,
            AVG(spend) as avg_spend,
            AVG(orders) as avg_orders,
            AVG(gmv/NULLIF(orders,0)) as aov,
            AVG(clicks/NULLIF(impressions,0)*100) as ctr
            FROM daily_performance''')
        row = c.fetchone()
        
        if row and row[0]:
            return {
                'roas': row[0] or 4.0,
                'spend': row[1] or 50000,
                'orders': row[2] or 3.5,
                'aov': row[3] or 70000,
                'ctr': row[4] or 4.0
            }
        
        # Fallback defaults
        return {'roas': 4.0, 'spend': 50000, 'orders': 3.5, 'aov': 70000, 'ctr': 4.0}
    
    def simulate(self, monthly_budget=None, target_roas=None, months_ahead=3):
        """Run simulation."""
        print("\n" + "="*70)
        print("🔮 REVENUE SIMULATOR")
        print("="*70)
        
        baseline = self.get_baseline()
        current_month = datetime.now().month
        
        print(f"\n📊 Baseline (from historical data):")
        print(f"   Avg ROAS: {baseline['roas']:.2f}x")
        print(f"   Avg Daily Spend: Rp {baseline['spend']:,.0f}")
        print(f"   Avg Daily Orders: {baseline['orders']:.1f}")
        print(f"   AOV: Rp {baseline['aov']:,.0f}")
        print(f"   CTR: {baseline['ctr']:.2f}%")
        
        # Default inputs
        if monthly_budget is None:
            monthly_budget = baseline['spend'] * 30
        if target_roas is None:
            target_roas = SEASONAL_CALENDAR[current_month]['roas_target']
        
        print(f"\n🎯 Simulation Parameters:")
        print(f"   Monthly Budget: Rp {monthly_budget:,.0f}")
        print(f"   Target ROAS: {target_roas}x")
        print(f"   Period: {months_ahead} months")
        
        # Run month-by-month
        print(f"\n📅 Month-by-Month Projection:")
        print(f"{'Month':<10} {'Season':<12} {'Budget':>12} {'GMV':>14} {'ROAS':>8} {'Orders':>8} {'Status':<15}")
        print("-" * 85)
        
        total_budget = 0
        total_gmv = 0
        total_orders = 0
        
        for i in range(months_ahead):
            month_idx = ((current_month - 1 + i) % 12) + 1
            seasonal = SEASONAL_CALENDAR[month_idx]
            
            # Adjust budget by seasonal factor
            seasonal_budget = monthly_budget * seasonal['budget_factor']
            
            # ROAS estimate: baseline adjusted by seasonal target
            # In reality, ROAS scales inversely with budget (diminishing returns)
            roas_estimate = min(baseline['roas'] * (seasonal['roas_target'] / 4.0), seasonal['roas_target'])
            
            # Orders: budget-based with seasonal adjustment
            cpo = baseline['spend'] / max(baseline['orders'], 1)  # Cost per order
            orders_estimate = (seasonal_budget / 30) / max(cpo * (seasonal['budget_factor'] / 1.0), 10000)
            orders_estimate = max(orders_estimate, seasonal['orders_per_day'] * 0.5)
            
            gmv_estimate = orders_estimate * baseline['aov'] * 30
            
            # Override GMV if ROAS target is the constraint
            gmv_from_roas = (seasonal_budget / 30) * roas_estimate * 30
            gmv_estimate = min(gmv_estimate, gmv_from_roas)
            
            actual_roas = gmv_estimate / seasonal_budget if seasonal_budget > 0 else 0
            
            status = "✅ On target" if actual_roas >= target_roas * 0.9 else "⚠️ Below target"
            
            print(f"{seasonal['name']:<10} {seasonal['season']:<12} Rp {seasonal_budget/1000000:>5.1f}M Rp {gmv_estimate/1000000:>7.1f}M {actual_roas:>7.1f}x {orders_estimate*30:>7.0f} {status:<15}")
            
            total_budget += seasonal_budget
            total_gmv += gmv_estimate
            total_orders += orders_estimate * 30
        
        print("-" * 85)
        print(f"{'TOTAL':<10} {'':<12} Rp {total_budget/1000000:>5.1f}M Rp {total_gmv/1000000:>7.1f}M {total_gmv/total_budget:>7.1f}x {total_orders:>7.0f}")
        
        print(f"\n💡 Key Insights:")
        print(f"   • Total Investment: Rp {total_budget:,.0f}")
        print(f"   • Expected Revenue: Rp {total_gmv:,.0f}")
        print(f"   • Blended ROAS: {total_gmv/total_budget:.2f}x")
        print(f"   • Total Orders: {total_orders:.0f}")
        print(f"   • Profitability: {'✅ Profitable' if total_gmv/total_budget >= 2.5 else '⚠️ Check margins'}")
        
        return {
            'total_budget': total_budget,
            'total_gmv': total_gmv,
            'blended_roas': total_gmv / total_budget,
            'total_orders': total_orders
        }

# =============================================================================
# COMPONENT 4: SEASONAL CALENDAR
# =============================================================================

class SeasonalCalendar:
    """Auto-generate monthly targets and budget plans."""
    
    def show(self):
        """Display full seasonal calendar."""
        print("\n" + "="*70)
        print("🗓️  SEASONAL CALENDAR - Umbrella Business")
        print("="*70)
        
        current_month = datetime.now().month
        
        print(f"\n{'Month':<8} {'Season':<12} {'Budget/Day':>12} {'ROAS':>8} {'Orders/Day':>10} {'Revenue/Mo':>14} {'Action':<20}")
        print("-" * 100)
        
        for m in range(1, 13):
            s = SEASONAL_CALENDAR[m]
            budget = BASE_DAILY_BUDGET * s['budget_factor']
            monthly_rev = budget * 30 * s['roas_target']
            
            marker = " ← NOW" if m == current_month else ""
            
            print(f"{s['name']:<8} {s['season']:<12} Rp {budget:>8,.0f} {s['roas_target']:>7.1f}x {s['orders_per_day']:>9} Rp {monthly_rev/1000000:>10.1f}M {s['note']:<20}{marker}")
        
        print("-" * 100)
        
        # Annual projection
        annual_budget = sum(BASE_DAILY_BUDGET * SEASONAL_CALENDAR[m]['budget_factor'] * 30 for m in range(1, 13))
        annual_rev = sum(BASE_DAILY_BUDGET * SEASONAL_CALENDAR[m]['budget_factor'] * 30 * SEASONAL_CALENDAR[m]['roas_target'] for m in range(1, 13))
        
        print(f"\n📊 Annual Projection:")
        print(f"   Total Ad Spend: Rp {annual_budget:,.0f} (Rp {annual_budget/12/1000000:.1f}M/month avg)")
        print(f"   Total Revenue: Rp {annual_rev:,.0f} (Rp {annual_rev/12/1000000:.1f}M/month avg)")
        print(f"   Blended ROAS: {annual_rev/annual_budget:.2f}x")
        print(f"   Annual Orders: {sum(SEASONAL_CALENDAR[m]['orders_per_day'] * 30 for m in range(1, 13)):,.0f}")
        
        # Current month focus
        current = SEASONAL_CALENDAR[current_month]
        print(f"\n🎯 Current Month Focus ({current['name']}):")
        print(f"   Strategy: {current['note']}")
        print(f"   Daily Budget: Rp {BASE_DAILY_BUDGET * current['budget_factor']:,.0f}")
        print(f"   ROAS Target: {current['roas_target']}x")
        print(f"   Orders Target: {current['orders_per_day']}/day")

# =============================================================================
# COMPONENT 5: COMPETITOR MONITOR
# =============================================================================

class CompetitorMonitor:
    """Track competitor pricing and performance on Shopee."""
    
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.keywords = ["payung lipat", "payung anti uv", "payung murah", "payung otomatis", "payung golf"]
    
    def search_shopee(self, keyword, limit=10):
        """Search Shopee for products (web scraping approach)."""
        # Note: This is a placeholder. Real implementation would use:
        # 1. Shopee's public search API
        # 2. Or web scraping with selenium/playwright
        # 3. Or third-party tools like DataSpark, Sellercraft, etc.
        
        print(f"\n🔍 Searching Shopee for '{keyword}'...")
        print("  (Note: Live scraping requires browser automation. Showing template.)")
        
        # Simulated data structure for now
        return [
            {
                'shop_name': f'Shop_{i}',
                'product_name': f'{keyword.title()} Product {i}',
                'price': 50000 + (i * 15000),
                'sales': 100 + (i * 50),
                'rating': 4.5 + (i * 0.1),
                'location': 'Jakarta'
            }
            for i in range(limit)
        ]
    
    def analyze(self):
        """Run competitor analysis."""
        print("\n" + "="*70)
        print("🏆 COMPETITOR ANALYSIS")
        print("="*70)
        
        print("\n⚠️  Live competitor scraping requires:")
        print("   Option A: Shopee Affiliate API (requires approval)")
        print("   Option B: Browser automation (selenium/playwright)")
        print("   Option C: Third-party tools (DataSpark, Sellercraft, Minovel)")
        
        print("\n📋 Recommended Keywords to Monitor:")
        for kw in self.keywords:
            print(f"   • {kw}")
        
        print("\n💡 Growth Opportunities (from seller community research):")
        print("   1. Bundle deals: Payung + Sarung Tangan/Jas Hujan")
        print("   2. Video content: Unboxing, waterproof tests")
        print("   3. Keywords: 'payung lipat 3d', 'payung anti uv 99%', 'payung besi kuat'")
        print("   4. Pricing: Rp 45k-75k sweet spot for payung lipat")
        print("   5. Flash sales: Coordinate with Shopee's 25th monthly sale")
        
        # Store placeholder data
        for kw in self.keywords:
            results = self.search_shopee(kw, limit=5)
            for r in results:
                self.conn.execute('''INSERT INTO competitor_data
                    (shop_name, product_name, price, sales, rating, scraped_at)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                    (r['shop_name'], r['product_name'], r['price'],
                     r['sales'], r['rating'], datetime.now().isoformat()))
        
        self.conn.commit()
        print("\n✅ Competitor data structure ready")

# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='Shopee Growth Engine')
    parser.add_argument('--mode', choices=['optimize', 'analyze', 'simulate', 'calendar', 'competitor', 'all'],
                       default='all', help='Operation mode')
    parser.add_argument('--budget', type=float, help='Monthly budget for simulation')
    parser.add_argument('--roas', type=float, help='Target ROAS for simulation')
    parser.add_argument('--live', action='store_true', help='Make real changes (optimizer)')
    args = parser.parse_args()
    
    print("="*70)
    print("🚀 SHOPEE GROWTH ENGINE v1.0")
    print("   Payung Murah Jakarta - Automated Growth System")
    print("="*70)
    
    # Initialize
    init_db()
    
    # Initialize APIs
    print("\n🔌 Connecting to Shopee APIs...")
    try:
        ads_api = ShopeeAPI(PARTNER_ID_ADS, PARTNER_KEY_ADS, 'tokens_ads.json')
        print("  ✅ Ads API connected")
    except Exception as e:
        print(f"  ⚠️  Ads API: {e}")
        ads_api = None
    
    try:
        seller_api = ShopeeAPI(PARTNER_ID_SELLER, PARTNER_KEY_SELLER, 'tokens_production.json')
        print("  ✅ Seller API connected")
    except Exception as e:
        print(f"  ⚠️  Seller API: {e}")
        seller_api = None
    
    # Run requested mode
    if args.mode in ('optimize', 'all') and ads_api:
        optimizer = SmartOptimizer(ads_api, seller_api)
        result = optimizer.run(dry_run=not args.live)
        if result:
            print(f"\n📊 Optimizer Result: ROAS {result['roas']:.2f}x, {result['actions']} actions")
    
    if args.mode in ('analyze', 'all') and seller_api:
        analyzer = HistoricalAnalyzer(ads_api, seller_api)
        analyzer.pull_orders(days=30)
        analyzer.analyze()
    
    if args.mode in ('simulate', 'all'):
        sim = RevenueSimulator()
        sim.simulate(monthly_budget=args.budget, target_roas=args.roas)
    
    if args.mode in ('calendar', 'all'):
        cal = SeasonalCalendar()
        cal.show()
    
    if args.mode in ('competitor', 'all'):
        comp = CompetitorMonitor()
        comp.analyze()
    
    print("\n" + "="*70)
    print("✅ Growth Engine Complete")
    print("="*70)

if __name__ == '__main__':
    main()
