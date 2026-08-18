# SHOPEE AUTOMATION SYSTEM — Complete Technical Guide
**Owner:** Gerard  
**Last Updated:** May 15, 2026  
**Purpose:** Full context for OpenClaw transfer/backup

---

## 1. PROJECT STRUCTURE

```
/Users/gerard/.openclaw/workspace/shopee-api-onboarding/
├── full_automation.py          # Main automation script (v3.10)
├── auto_optimizer.py           # ROAS auto-adjustment script
├── semi_auto_optimizer.py      # Semi-automatic optimization
├── database.py                 # SQLite database for tracking
├── tokens_production.json      # Shopee Seller API tokens
├── tokens_ads.json             # Shopee Ads API tokens
├── last_change.json            # Last optimization timestamp
├── boost_log.json              # Daily boost tracking
├── automation_logs.db          # SQLite log database
├── CRON_SETUP.md              # Cron configuration guide
├── logs/
│   ├── automation_YYYYMMDD.log # Daily execution logs
│   └── error_YYYYMMDD.log    # Error logs
├── docs/
│   ├── REPORT_STRATEGY.md     # Reporting strategy doc
│   └── ANALYSIS_5MONTH_HISTORY.md  # 5-month sales analysis
└── cron_optimizer.txt         # Cron job definitions
```

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

### Shopee Ads API
| Field | Value |
|-------|-------|
| Partner ID | `2030650` |
| Partner Key | `shpk596a6556535573774b4e7742454a4f566e42794c7549736c4c59594c6a69` |
| Shop ID | `1147948100` |
| Base URL | `https://partner.shopeemobile.com` |
| Token File | `tokens_ads.json` |

**Token Refresh:** Both tokens use refresh_token → access_token rotation. Refresh valid for 30 days.

---

## 3. AUTOMATION SCRIPTS

### 3.1 full_automation.py (v3.10)
**Purpose:** Main orchestrator — runs every 15 minutes via cron

**Functions:**
1. **Product Boost** — Every 4.1 hours, boosts 5 products
2. **Report Spam Fix** — v3.10: Only reports between 09:00-09:15 (fixed duplicate report bug)
3. **Token Refresh** — Auto-refreshes expired tokens
4. **API Call Tracking** — Logs all API interactions

**Key Config:**
```python
BOOST_COOLDOWN_MINUTES = 250  # 4 hours 10 minutes
BOOST_ITEMS_COUNT = 5        # 5 products per boost
REPORT_WINDOW = "09:00-09:15" # Only report in this window
```

**Cron Schedule:**
```bash
# System crontab (via crontab -e)
*/15 * * * * cd /Users/gerard/.openclaw/workspace/shopee-api-onboarding && /usr/local/bin/python3 full_automation.py >> logs/automation_$(date +\%Y\%m\%d).log 2>&1
```

### 3.2 auto_optimizer.py
**Purpose:** Automatically adjusts ad bids based on ROAS performance

**Logic:**
- Fetches campaign performance data
- Compares actual ROAS vs target ROAS
- Adjusts bids up/down by 10-15%
- Logs all changes to `last_change.json`

### 3.3 semi_auto_optimizer.py
**Purpose:** Manual review + auto-execution hybrid
- Generates recommendations
- Requires user approval before executing
- Safer for major changes

---

## 4. BOOST SYSTEM

### How It Works
1. Every 15 minutes, script checks: "Has it been >4.1 hours since last boost?"
2. If YES: Fetches 5 products with status NORMAL, calls boost API
3. If NO: Skips, logs "buffer remaining: X minutes"
4. Shopee allows **5 boosts every 4 hours per shop**

### Daily Boost Schedule (Ideal)
| Time | Action |
|------|--------|
| 00:00 | 1st boost (5 items) |
| 04:10 | 2nd boost (5 items) |
| 08:20 | 3rd boost (5 items) |
| 12:30 | 4th boost (5 items) |
| 16:40 | 5th boost (5 items) |
| 20:50 | 6th boost attempt → FAILS (daily limit: 5/shop) |

### Known Issue — DUPLICATE CRONS (FIXED May 7)
**Problem:** 4 duplicate cron jobs were running simultaneously, causing:
- Race conditions on boost_log.json
- Inconsistent cooldown tracking
- "Daily limit reached" errors at wrong times

**Fix Applied:**
- Disabled 3 duplicate OpenClaw cron jobs
- Kept only system crontab (`*/15 * * * *`)
- All 4 cron jobs now disabled in OpenClaw cron system

**Current Status:** ✅ Only 1 instance running

---

## 5. ADS / ROAS SYSTEM

### API Endpoint
```
GET /api/v2/ads/get_all_cpc_ads_daily_performance
```

### Recent ROAS Performance
| Date | ROAS | Spend | GMV | Orders |
|------|------|-------|-----|--------|
| May 4 | 3.23x | 361k | 1.17M | 22 |
| May 5 | 3.12x | 364k | 1.14M | 21 |
| May 6 | **1.32x** | 189k | 249k | 5 |
| May 7 | *Data unavailable* | | | |

### Root Cause of May 6 Crash
1. **Duplicate cron conflict** — Reduced organic boosts
2. **6x target too high** — Algorithm never hits target, enters penalty mode
3. **Quality score degradation** — From March late delivery penalty (13% → 6%)

### Recommended Fix
```
Campaign targets: Lower from 6.0x → 3.5x temporarily
New creatives: Upload 2 new videos
Monitor: 48 hours without touching
```

---

## 6. CRON JOBS (OpenClaw)

### Currently Disabled (May 4 onwards)
| Job ID | Name | Status | Reason |
|--------|------|--------|--------|
| 4cfa03f3 | shopee-boost-1 | ❌ Disabled | Duplicate |
| b2d0cf68 | shopee-boost-2 | ❌ Disabled | Duplicate |
| 4ef7f3e0 | shopee-boost-3 | ❌ Disabled | Duplicate + rate limit |

### Currently Active
| Job | Schedule | Status |
|-----|----------|--------|
| System crontab | */15 * * * * | ✅ Active |
| morning-checkin | 06:40 daily | ✅ Active |
| ken-morning-research | 08:35 daily | ❌ Failing delivery |
| ken-daily | 19:30 daily | ❌ Failing delivery |
| nightly-document-clear | 23:00 daily | ✅ Active |

---

## 7. DATABASE SCHEMA

### SQLite Tables (automation_logs.db)
```sql
-- api_calls: Tracks all API interactions
CREATE TABLE api_calls (
    id INTEGER PRIMARY KEY,
    timestamp TEXT,
    endpoint TEXT,
    status TEXT,
    response_time_ms INTEGER
);

-- boosts: Tracks product boost history
CREATE TABLE boosts (
    id INTEGER PRIMARY KEY,
    timestamp TEXT,
    item_id TEXT,
    success BOOLEAN
);

-- roas_history: Daily ROAS snapshots
CREATE TABLE roas_history (
    id INTEGER PRIMARY KEY,
    date TEXT,
    roas REAL,
    spend REAL,
    gmv REAL,
    orders INTEGER
);
```

---

## 8. TOKEN MANAGEMENT

### Token Files
- `tokens_production.json` — Seller API (product management, boosts)
- `tokens_ads.json` — Ads API (campaigns, ROAS tracking)

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
- access_token: ~4 hours
- refresh_token: 30 days

---

## 9. CURRENT ISSUES & FIXES

### Issue 1: Duplicate Crons (FIXED)
- **Status:** ✅ Resolved May 7
- **Impact:** Boost system now stable

### Issue 2: ROAS Crash (DIAGNOSED, AWAITING FIX)
- **Status:** ⏳ Need user to adjust campaign targets
- **Impact:** Losing money on ads (1.32x vs break-even ~2.5x)

### Issue 3: Ken Delivery Failures
- **Status:** ❌ 8+ consecutive failures
- **Impact:** Finance briefs not reaching user
- **Note:** Main session (Sara) delivers successfully

### Issue 4: Report Spam (FIXED in v3.10)
- **Status:** ✅ Fixed
- **Fix:** Changed from `if hour == 9` to `if hour == 9 and minute < 15`

---

## 10. FILE PATHS & QUICK COMMANDS

### Check Boost Log
```bash
cd /Users/gerard/.openclaw/workspace/shopee-api-onboarding
cat boost_log.json
```

### Check Today's Automation Log
```bash
cd /Users/gerard/.openclaw/workspace/shopee-api-onboarding/logs
cat automation_$(date +%Y%m%d).log | tail -50
```

### Manual Token Refresh
```bash
cd /Users/gerard/.openclaw/workspace/shopee-api-onboarding
python3 -c "import full_automation; full_automation.refresh_tokens()"
```

### Force Boost
```bash
cd /Users/gerard/.openclaw/workspace/shopee-api-onboarding
python3 -c "import full_automation; full_automation.boost_products()"
```

---

## 11. SHOPEE SHOP CONTEXT

### Business Info
- **Store Type:** Umbrella products + FMCG agency
- **Monthly Revenue:** ~8-9M IDR (as of Apr 27)
- **Ad Spend:** ~350-400k/day
- **Target ROAS:** 6.0x (currently unachievable)
- **Actual ROAS:** 3.1-3.2x (healthy), crashed to 1.32x May 6

### Pending Tasks (Stalled)
1. Lower ad campaign targets from 6x → 3.5x
2. Upload 2 new ad creatives
3. Check item 24347685929 stock status
4. Shopee Live flash sale execution

### Brother's Role
- Handles fulfillment (packing, shipping)
- Face-to-face communication
- User manages marketing/ads only

---

## 12. SECURITY NOTES

### API Keys
- Partner keys are hardcoded in scripts
- Token files contain live access credentials
- **Do not share tokens_*.json publicly**

### Safe to Share
- This document ✅
- Script logic ✅
- Log analysis ✅
- ROAS data ✅

### Keep Private
- `tokens_production.json` ❌
- `tokens_ads.json` ❌
- Partner keys (already in scripts) ⚠️

---

## 13. HOW TO TRANSFER TO NEW OPENCLAW

### Step 1: Copy Workspace
```bash
rsync -av /Users/gerard/.openclaw/workspace/shopee-api-onboarding/ \
  ~/shopee-backup/
```

### Step 2: Preserve Tokens
- Copy `tokens_production.json`
- Copy `tokens_ads.json`
- Refresh both tokens before transfer (get new 30-day refresh tokens)

### Step 3: Set Up Cron
```bash
# Add to crontab
crontab -e
# Add: */15 * * * * cd /path/to/shopee-api-onboarding && python3 full_automation.py >> logs/automation_$(date +\%Y\%m\%d).log 2>&1
```

### Step 4: Install Dependencies
```bash
pip install requests python-dotenv
```

### Step 5: Test
```bash
python3 full_automation.py
# Check logs: cat logs/automation_$(date +%Y%m%d).log
```

---

## 14. CONTACT / OWNER INFO

- **Owner:** Gerard
- **Location:** BSD, Jakarta, Indonesia
- **Timezone:** Asia/Jakarta (GMT+7)
- **Business:** Shopee Seller + Agency
- **Assistant:** Sara (OpenClaw)

---

*End of guide. Generated May 15, 2026.*
