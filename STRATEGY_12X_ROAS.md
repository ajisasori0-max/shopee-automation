# 🎯 12x ROAS + 500k Daily Spend Strategy
## Comprehensive Research & Action Plan

---

## 📊 CURRENT STATE ANALYSIS

**Your 5 Active Campaigns:**
| Campaign ID | Name | Current Budget | Status |
|-------------|------|----------------|--------|
| 452411592 | PAYUNG LIPAT PREMIUM METALIK | Rp 101,000 | ongoing |
| 447589870 | CAP KAPAL PAYUNG LIPAT PREMIUM | Rp 200,000 | ongoing |
| 445446513 | PAYUNG LIPAT ANTI UV PREMIUM | Rp 250,000 | ongoing |
| 445311693 | PAYUNG OTOMATIS PREMIUM 3D | Rp 150,000 | ongoing |
| 445335702 | CAP KAPAL PAYUNG GOLF SILVER | Rp 100,000 | ongoing |

**Total Current Daily Budget:** Rp 801,000 ( spread across 5 campaigns)
**Target:** Rp 2,500,000 (500k per campaign)
**Current ROAS:** ~2-5x (estimated)
**Target ROAS:** 12x

---

## ⚠️ CRITICAL INSIGHT: THE ROAS-VOLUME TRADE-OFF

**From Shopee Official Documentation:**

> "When sellers set a high ROAS target, GMV Max will become more selective to focus on efficiency. As it prioritizes performance efficiency over volume, GMV Max will **inadvertently limit spend**, thereby limiting potential GMV."

> "Example: When Seller sets ROAS target of 14 vs average achieved ROAS of 10, GMV Max becomes more selective... **volume will be affected**"

### 🎯 THE MATH:
- **12x ROAS** = Very selective, limited volume
- **500k daily spend** = High volume requirement
- **These are OPPOSING goals**

### ✅ SOLUTION: Staged Approach

| Stage | ROAS Target | Daily Budget | Focus |
|-------|-------------|--------------|-------|
| **1. Foundation** | 4-5x | 200-300k | Optimize existing |
| **2. Scale** | 6-8x | 400-500k | Increase budget gradually |
| **3. Peak** | 10-12x | 500k+ | Maximum efficiency |

---

## 🚀 STRATEGY ROADMAP TO 12x ROAS

### PHASE 1: FOUNDATION (Week 1-2) — Target: 4-5x ROAS

**1. Product Optimization (CRITICAL)**
- ✅ High-quality images (9 slots)
- ✅ Complete product attributes
- ✅ Competitive pricing vs competitors
- ✅ 4.7+ star rating minimum
- ✅ Fast chat response (under 1 hour)

**2. Campaign Restructuring**
```
Current: 5 campaigns, 100-250k each
New: 3 campaign tiers
```

**Tier 1 — Hero Products (2 campaigns)**
- Budget: Rp 200k/day each
- Target ROAS: 5x initially
- Products: Top 2 best sellers

**Tier 2 — Growth Products (2 campaigns)**
- Budget: Rp 100k/day each  
- Target ROAS: 4x initially
- Products: Potential bestsellers

**Tier 3 — Testing (1 campaign)**
- Budget: Rp 50k/day
- Target ROAS: 3x
- Products: New/experimental

**3. GMV Max Configuration**
- Use **GMV Max Custom ROAS** (not Auto Bidding)
- Start with **conservative ROAS targets** (4-5x)
- Wait 7 days for Learning Phase (NO CHANGES)

---

### PHASE 2: OPTIMIZATION (Week 3-4) — Target: 6-8x ROAS

**1. ROAS Target Escalation (Max 20% increase per adjustment)**
```
Week 3: Increase ROAS target 5x → 6x (+20%)
Week 4: Increase ROAS target 6x → 7-8x
```

**2. Budget Scaling (Only for campaigns achieving target)**
```
If ROAS > Target: Increase budget 10-20%
If ROAS < Target: Decrease budget or pause
```

**3. Auto Budget Increase Feature**
- Enable in Seller Center → Shopee Ads → Auto Budget Increase
- Set increase rate: 20-50%
- Max 2-3 increases per day
- Only for campaigns hitting ROAS targets

---

### PHASE 3: PEAK PERFORMANCE (Week 5-8) — Target: 10-12x ROAS

**1. Aggressive ROAS Targets**
- Scale to 10x, then 12x
- Monitor volume drop-off carefully
- Accept lower volume at higher efficiency

**2. Campaign Consolidation**
- Kill underperformers (< 8x ROAS)
- Reallocate budget to winners
- Focus on 2-3 hero campaigns

**3. Advanced Tactics**
- **Dayparting**: Increase bids during peak hours (12-2pm, 8-10pm)
- **Audience refinement**: Narrow targeting to highest-converting segments
- **Keyword optimization**: Remove waste, double down on converters

---

## 🛠️ IMPLEMENTATION: AUTO-OPTIMIZER SETTINGS

Update `auto_optimizer.py` with these settings:

```python
# PHASE 1: Foundation (Week 1-2)
MIN_ROAS = 4.0          # Minimum acceptable
TARGET_ROAS = 5.0       # Starting target
ROAS_ADJUST_STEP = 0.2  # Max 20% change per day

# Daily Budget Tiers
HERO_BUDGET = 200000    # Rp 200k
GROWTH_BUDGET = 100000  # Rp 100k
TEST_BUDGET = 50000     # Rp 50k

# Auto Actions
AUTO_ADJUST_ENABLED = True
PAUSE_IF_ROAS_BELOW = 3.5      # Pause if below 3.5x
INCREASE_BUDGET_IF_ROAS_ABOVE = 6.0  # Scale winners
BUDGET_INCREASE_PCT = 0.15     # +15% for winners
```

```python
# PHASE 2: Scale (Week 3-4)
MIN_ROAS = 6.0
TARGET_ROAS = 8.0
# Same other settings
```

```python
# PHASE 3: Peak (Week 5+)
MIN_ROAS = 10.0
TARGET_ROAS = 12.0
MAX_DAILY_BUDGET = 500000  # Cap at 500k per campaign
```

---

## 📋 KEY TACTICS FROM RESEARCH

### 1. The 7-Day Rule
**NEVER make changes during first 7 days (Learning Phase)**
- System is exploring optimal bid ranges
- Performance will fluctuate wildly
- Wait for stabilization before optimizing

### 2. The 20% Rule
**Never adjust ROAS target more than 20% at once**
- Too aggressive = performance crash
- Max 1-2 adjustments per day
- Let system re-learn after each change

### 3. The Budget-ROAS Balance
```
High Budget + Low ROAS Target = High Volume, Lower Efficiency
Low Budget + High ROAS Target = Low Volume, High Efficiency

Goal: Find the sweet spot for YOUR products
```

### 4. Auto Budget Increase Strategy
**Enable in Seller Center:**
- Increase rate: 20-50%
- Max frequency: 2-3x/day
- Condition: Only if actual ROAS > target ROAS
- Reset daily to original budget

### 5. Product Quality Prerequisites
**MUST have these before scaling:**
- ⭐ 4.7+ star rating
- 📸 9 high-quality images
- ✍️ Complete, keyword-rich descriptions
- 💬 < 1 hour chat response time
- 📦 Fast shipping (same day preferred)
- 🏷️ Competitive pricing (within 10% of market)

---

## ⚡ QUICK WINS (Implement Today)

### 1. Enable Auto Budget Increase
```
Seller Center → Marketing → Shopee Ads → Auto Budget Increase
Budget Increase Rate: 30%
Daily Increase Frequency: 2 times
Apply to: Product Ads (GMV Max)
```

### 2. Restructure Campaigns
```
Campaign 1 (Hero): 452411592 or 445446513
- Budget: 200k → Target ROAS: 5x

Campaign 2 (Hero): 447589870 or 445311693  
- Budget: 200k → Target ROAS: 5x

Campaign 3 (Growth): 445335702
- Budget: 100k → Target ROAS: 4x

Pause/delete: Least performing campaign
```

### 3. Set Up Monitoring
- Run auto_optimizer.py daily at 9am
- Check reports/ folder for daily summaries
- Manual check in Seller Center every 3 days

---

## 📊 EXPECTED TIMELINE

| Week | ROAS | Budget/Campaign | Key Actions |
|------|------|-----------------|-------------|
| 1 | 4-5x | 200k | Launch, NO CHANGES |
| 2 | 4-5x | 200k | Learning phase ends |
| 3 | 6-7x | 250k | Increase ROAS target 20% |
| 4 | 7-8x | 300k | Scale winning campaigns |
| 5 | 9-10x | 400k | Aggressive optimization |
| 6 | 11-12x | 500k | Peak performance mode |
| 7+ | 12x+ | 500k | Maintain & monitor |

---

## 🎯 SUCCESS METRICS

**Daily Tracking:**
- ROAS per campaign
- Spend vs budget
- CTR (target: >2%)
- Conversion rate

**Weekly Review:**
- 7-day rolling ROAS
- Budget efficiency
- Campaign pauses/launches
- Product performance

**Red Flags (Stop & Fix):**
- ROAS drops below 3x for 3+ days
- CTR below 1%
- Spend > budget with 0 sales
- Product rating drops below 4.5

---

## ⚠️ RISKS & MITIGATION

| Risk | Mitigation |
|------|------------|
| Volume drops at 12x ROAS | Accept lower volume, focus on margin |
| Budget burn without sales | Strict pause rules (ROAS < 3.5x) |
| Algorithm learning takes too long | Wait full 7 days, no exceptions |
| Competition increases | Monitor competitor pricing weekly |
| Product quality issues | Maintain 4.7+ rating, fast response |

---

## 🚀 FINAL RECOMMENDATION

**12x ROAS is achievable BUT requires:**
1. ⏰ **Patience** — 6-8 week timeline minimum
2. 🔧 **Product excellence** — 4.7+ stars, complete listings
3. 💰 **Budget discipline** — Stage increases, don't rush
4. 📊 **Daily monitoring** — Automated + manual checks
5. 🎯 **Ruthless optimization** — Kill underperformers fast

**Start TODAY with Phase 1.**

Do not skip steps. Do not rush. The algorithm needs time to learn.

---

**Want me to:**
- A) Update auto_optimizer.py with Phase 1 settings?
- B) Create detailed product optimization checklist?
- C) Build competitor price monitoring system?
- D) Set up automated daily reporting?

🦊