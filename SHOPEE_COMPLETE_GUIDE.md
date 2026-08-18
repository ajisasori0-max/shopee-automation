# SHOPEE API ONBOARDING — COMPLETE DOCUMENTATION
**Owner:** Gerard  
**Created by:** Sara (OpenClaw)  
**Last Updated:** May 22, 2026  
**Purpose:** Complete technical reference for Shopee automation system

---

## TABLE OF CONTENTS

1. [Project Overview](#1-project-overview)
2. [API Credentials](#2-api-credentials)
3. [Project Structure](#3-project-structure)
4. [Automation Scripts](#4-automation-scripts)
5. [Database Schema](#5-database-schema)
6. [Cron Configuration](#6-cron-configuration)
7. [Token Management](#7-token-management)
8. [Boost System](#8-boost-system)
9. [ROAS Tracking](#9-roas-tracking)
10. [Historical Performance](#10-historical-performance)
11. [Known Issues & Fixes](#11-known-issues--fixes)
12. [Transfer Instructions](#12-transfer-instructions)

---

## 1. PROJECT OVERVIEW

This project automates Shopee store operations using the official Shopee Partner API. It handles product boosting, ad optimization, and daily performance tracking.

**What it does:**
- Automatically boosts 5 products every 4.1 hours (max allowed by Shopee)
- Tracks ROAS (Return on Ad Spend) daily
- Auto-adjusts ad bids based on performance
- Sends daily reports with sales data
- Manages API token refresh automatically

**Current Status:**
- ⚠️ Boost system: Fixed (duplicate crons resolved May 7)
- ⚠️ ROAS: Crashed to 1.32x (May 6), fix guide delivered, awaiting user action
- ✅ Token refresh: Working
- ✅ Daily reports: Working (fixed spam bug in v3.10)

---

## 2. API CREDENTIALS

### Shopee Seller API (Production)
| Field | Value |
|-------|-------|
| Partner ID | `2030653` |
| Partner Key | `shpk44444e634d6668466c5073776b45646454774a7975706d47497063526453` |
| Shop ID | `1147948100` |
| Base URL | `https://partner.shopeemobile.com` |
| Token File | `tokens_production.json` |
| Permissions | Product management, order management, shop info |

### Shopee Ads API
| Field | Value |
|-------|-------|
| Partner ID | `2030650` |
| Partner Key | `shpk596a6556535573774b4e7742454a4f566e42794c7549736c4c59594c6a69` |
| Shop ID | `1147948100` |
| Base URL | `https://partner.shopeemobile.com` |
| Token File | `tokens_ads.json` |
| Permissions | Campaign management, performance data, ad analytics |

### Security Notes
- **Never commit token files to git**
- **Never share partner keys publicly**
- **Refresh tokens valid for 30 days**
- **Access tokens valid for ~4 hours**

---

## 3. PROJECT STRUCTURE

```
shopee-api-onboarding/
├── full_automation.py          # Main automation script (v3.10)
├── auto_optimizer.py           # ROAS auto-adjustment
├── semi_auto_optimizer.py      # Semi-automatic optimization
├── database.py                 # SQLite tracking
├── tokens_production.json      # Seller API tokens (PRIVATE)
├── tokens_ads.json             # Ads API tokens (PRIVATE)
├── last_change.json            # Last optimization timestamp
├── boost_log.json              # Daily boost tracking
├── automation_logs.db          # SQLite log database
├── CRON_SETUP.md              # Cron configuration guide
├── cron_optimizer.txt         # Cron job definitions
├── cron_semi_auto.txt         # Semi-auto cron setup
├── cron_full_automation.txt   # Full automation cron setup
├── logs/
│   ├── automation_YYYYMMDD.log # Daily execution logs
│   └── error_YYYYMMDD.log      # Error logs
└── docs/
    ├── REPORT_STRATEGY.md       # Reporting strategy
    ├── ANALYSIS_5MONTH_HISTORY.md  # Historical analysis
    └── STRATEGY_12X_ROAS.md   # ROAS optimization strategy
```

---

## 4. AUTOMATION SCRIPTS

### 4.1 full_automation.py (v3.10)
**Purpose:** Main orchestrator — runs every 15 minutes

**Functions:**
1. **Product Boost** — Every 4.1 hours, boosts 5 products
2. **Report Spam Fix** — v3.10: Only reports between 09:00-09:15
3. **Token Refresh** — Auto-refreshes expired tokens
4. **API Call Tracking** — Logs all API interactions

**Key Config:**
```python
BOOST_COOLDOWN_MINUTES = 250  # 4 hours 10 minutes
BOOST_ITEMS_COUNT = 5         # 5 products per boost
REPORT_WINDOW = "09:00-09:15" # Only report in this window
```

**How Boost Works:**
1. Checks: "Has it been >4.1 hours since last boost?"
2. If YES: Fetches 5 products with status NORMAL, calls boost API
3. If NO: Skips, logs "buffer remaining: X minutes"
4. Shopee allows 5 boosts every 4 hours per shop

**Daily Boost Schedule (Ideal):**
| Time | Action |
|------|--------|
| 00:00 | 1st boost (5 items) |
| 04:10 | 2nd boost (5 items) |
| 08:20 | 3rd boost (5 items) |
| 12:30 | 4th boost (5 items) |
| 16:40 | 5th boost (5 items) |
| 20:50 | 6th attempt → FAILS (daily limit: 5/shop) |

### 4.2 auto_optimizer.py
**Purpose:** Automatically adjusts ad bids based on ROAS performance

**Logic:**
- Fetches campaign performance data
- Compares actual ROAS vs target ROAS
- Adjusts bids up/down by 10-15%
- Logs all changes to `last_change.json`

**Key Parameters:**
```python
ROAS_TARGET_MIN = 3.0    # Minimum acceptable ROAS
ROAS_TARGET_MAX = 6.0    # Maximum target ROAS
BID_ADJUSTMENT_STEP = 0.1  # 10% bid adjustment
```

### 4.3 semi_auto_optimizer.py
**Purpose:** Manual review + auto-execution hybrid
- Generates recommendations
- Requires user approval before executing
- Safer for major changes

**How it works:**
1. Analyzes all campaigns
2. Generates recommendation list
3. Shows: "Campaign X: Lower bid from 500 to 450 (ROAS: 2.1x)"
4. User approves/rejects each
5. Executes approved changes

---

## 5. DATABASE SCHEMA

### SQLite Tables (automation_logs.db)

```sql
-- api_calls: Tracks all API interactions
CREATE TABLE api_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    endpoint TEXT,
    status TEXT,
    response_time_ms INTEGER,
    error_message TEXT
);

-- boosts: Tracks product boost history
CREATE TABLE boosts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    item_id TEXT,
    item_name TEXT,
    success BOOLEAN,
    error_message TEXT
);

-- roas_history: Daily ROAS snapshots
CREATE TABLE roas_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    roas REAL,
    spend REAL,
    gmv REAL,
    orders INTEGER,
    clicks INTEGER,
    impressions INTEGER
);

-- campaigns: Campaign performance tracking
CREATE TABLE campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id TEXT,
    campaign_name TEXT,
    status TEXT,
    bid REAL,
    budget REAL,
    roas REAL,
    spend REAL,
    gmv REAL,
    orders INTEGER
);
```

---

## 6. CRON CONFIGURATION

### System Crontab (Active)
```bash
# Add via: crontab -e
*/15 * * * * cd /Users/gerard/.openclaw/workspace/shopee-api-onboarding && /usr/local/bin/python3 full_automation.py >> logs/automation_$(date +\%Y\%m\%d).log 2>&1
```

### OpenClaw Cron Jobs (Disabled)
| Job ID | Name | Status | Reason |
|--------|------|--------|--------|
| 4cfa03f3 | shopee-boost-1 | ❌ Disabled | Duplicate |
| b2d0cf68 | shopee-boost-2 | ❌ Disabled | Duplicate |
| 4ef7f3e0 | shopee-boost-3 | ❌ Disabled | Duplicate + rate limit |

**History:**
- **May 4-7:** 4 duplicate cron jobs running simultaneously
- **Problem:** Race conditions on `boost_log.json`, cooldown conflicts
- **Fix:** Disabled 3 duplicates, kept only system crontab
- **Result:** Boost system now stable

---

## 7. TOKEN MANAGEMENT

### Token Files
- `tokens_production.json` — Seller API (product management)
- `tokens_ads.json` — Ads API (campaign management)

### Refresh Flow
```
1. Check if access_token expired (401 error)
2. If expired: Call /api/v2/auth/access_token/get
   with refresh_token
3. Receive new access_token + refresh_token
4. Save to JSON file
5. Retry original request
```

### Token Expiry
- **access_token:** ~4 hours
- **refresh_token:** 30 days
- **Auto-refresh:** Handled by full_automation.py

---

## 8. BOOST SYSTEM

### How It Works
```python
def should_boost():
    last_boost = get_last_boost_time()
    time_since = now - last_boost
    return time_since > timedelta(minutes=250)  # 4h 10m

def boost_products():
    items = get_eligible_products(limit=5)
    for item in items:
        result = call_boost_api(item.id)
        log_boost_result(result)
```

### Eligible Products
- Status: NORMAL
- Stock: > 0
- Not already boosted in last 4 hours

### API Endpoint
```
POST /api/v2/product/boost_item
Body: {"item_id_list": [12345, 67890, ...]}
```

### Response
```json
{
  "response": {
    "success_list": {"item_id_list": [12345, 67890]},
    "failure_list": [
      {"item_id": 11111, "failed_reason": "reached shop's bump slot limit"}
    ]
  }
}
```

---

## 9. ROAS TRACKING

### API Endpoint
```
GET /api/v2/ads/get_all_cpc_ads_daily_performance
Params: start_date, end_date
```

### Recent Performance
| Date | ROAS | Spend | GMV | Orders |
|------|------|-------|-----|--------|
| May 4 | 3.23x | 361k | 1.17M | 22 |
| May 5 | 3.12x | 364k | 1.14M | 21 |
| May 6 | **1.32x** | 189k | 249k | 5 |
| May 7-21 | *Data unavailable* | | | |

### ROAS Crash Analysis (May 6)
**Symptoms:**
- ROAS dropped from 3.1x → 1.32x (-58%)
- Orders dropped from 21 → 5 (-76%)
- Spend dropped from 364k → 189k (-48%)

**Root Causes:**
1. **Duplicate cron conflict** (May 4-6) — Reduced organic boosts
2. **6x target too high** — Algorithm penalty mode
3. **March late delivery penalty** (13%→6%) still haunting quality score

**Recommended Fix:**
- Lower campaign targets from 6.0x → 3.5x
- Upload 2 new ad creatives
- Don't touch for 48 hours
- Let algorithm recalibrate

### Target ROAS Issues
- **User set:** 6.0x
- **Algorithm can deliver:** ~3.0-3.5x (current quality score)
- **Gap:** Algorithm trying and failing → penalty mode
- **Fix:** Temporarily accept 3.5x, let quality score recover, then gradually raise

---

## 10. HISTORICAL PERFORMANCE

### 5-Month Sales History (From ANALYSIS_5MONTH_HISTORY.md)

| Month | Orders | Revenue | Avg Order |
|-------|--------|---------|-----------|
| Jan 2026 | ~600 | 18M | 30k |
| Feb 2026 | ~450 | 12M | 27k |
| Mar 2026 | ~350 | 8M | 23k |
| Apr 2026 | ~280 | 6M | 21k |
| May 2026 | ~200 | 4M | 20k |

**Trend:** Declining 15-20% month-over-month
**Reason:** Late delivery penalty in March (13%→6%) → algorithm "memory" → reduced visibility

### Algorithm Recovery Pattern
1. **Penalty applied:** Late delivery >10%
2. **Orders drop:** 20/day → 3-4/day
3. **Ad spend drops:** 100k/day → 1k/day (quality score death spiral)
4. **Recovery time:** 2-3 weeks of perfect metrics
5. **Key action:** Lower ROAS target proactively during recovery

### Shop Health Metrics
| Metric | Status | Target |
|--------|--------|--------|
| Chat Response | ✅ Green | <1 hour |
| On-Time Shipping | ✅ Green | >95% |
| Cancellation Rate | ✅ Green | <2% |
| Return/Refund | ✅ Green | <1% |
| Product Rating | ✅ Green | >4.5 |

---

## 11. KNOWN ISSUES & FIXES

### Issue 1: Duplicate Crons (FIXED May 7)
- **Status:** ✅ Resolved
- **Impact:** Boost system stable
- **Fix:** Disabled 3 duplicate OpenClaw cron jobs

### Issue 2: ROAS Crash (DIAGNOSED, PENDING FIX)
- **Status:** ⏳ Awaiting user action
- **Impact:** Losing money on ads
- **Fix needed:** Lower targets 6x → 3.5x + new creatives

### Issue 3: Report Spam (FIXED in v3.10)
- **Status:** ✅ Resolved
- **Fix:** Changed from `if hour == 9` to `if hour == 9 and minute < 15`
- **Result:** Reports once per day, not 4x

### Issue 4: Token Expiry
- **Status:** ✅ Auto-handled
- **Fix:** Automatic refresh in full_automation.py

---

## 12. TRANSFER INSTRUCTIONS

### To Move to New OpenClaw

**Step 1: Copy Workspace**
```bash
rsync -av /Users/gerard/.openclaw/workspace/shopee-api-onboarding/ \
  ~/shopee-backup/
```

**Step 2: Preserve Tokens**
```bash
cp tokens_production.json tokens_ads.json ~/backup/
# Or refresh before transfer to get new 30-day refresh tokens
```

**Step 3: Set Up Cron**
```bash
crontab -e
# Add: */15 * * * * cd /path/to/shopee-api-onboarding && python3 full_automation.py >> logs/automation_$(date +\%Y\%m\%d).log 2>&1
```

**Step 4: Install Dependencies**
```bash
pip install requests python-dotenv
```

**Step 5: Test**
```bash
cd shopee-api-onboarding
python3 full_automation.py
# Check: cat logs/automation_$(date +%Y%m%d).log
```

### Security Checklist
- ✅ Safe to share: This document, script logic, log analysis
- ❌ Keep private: `tokens_production.json`, `tokens_ads.json`
- ⚠️ Protect: Partner keys (already in scripts)

---

## APPENDIX: KEY API ENDPOINTS

### Seller API
```
POST /api/v2/product/boost_item
GET  /api/v2/product/get_item_list
GET  /api/v2/product/get_item_detail
POST /api/v2/product/update_stock
```

### Ads API
```
GET  /api/v2/ads/get_campaign_list
GET  /api/v2/ads/get_all_cpc_ads_daily_performance
POST /api/v2/ads/update_bid
POST /api/v2/ads/update_campaign_status
```

### Auth API
```
POST /api/v2/auth/access_token/get
POST /api/v2/auth/refresh_token/get
```

---

## APPENDIX: SHOPIFY HEALTH CHECK

Run manually:
```bash
cd shopee-api-onboarding
python3 -c "
import full_automation
full_automation.check_shop_health()
"
```

Checks:
- Product listing status
- Stock levels
- Recent orders
- Pending shipments
- Customer messages

---

*End of Shopee API Onboarding Documentation*
*Generated May 22, 2026*
*Status: Operational, awaiting ROAS fix*
*Next action needed: User to lower ad campaign targets from 6x → 3.5x*
