# 🚀 Multi-Platform Ecommerce Growth Plan
## Gerard | Payung Murah Jakarta | Generated: June 2026

---

## 📊 CURRENT STATE

| Platform | Status | Monthly GMV | ROAS | Automation |
|----------|--------|-------------|------|------------|
| **Shopee** | ✅ Live | ~Rp 8-9M | 3.9x | ✅ Full (cron + optimizer) |
| **Lazada** | ❌ Not started | - | - | - |
| **Tokopedia** | ❌ Not started | - | - | - |
| **TikTok Shop** | ❌ Not started | - | - | - |
| **Meta Ads** | ❌ Not started | - | - | - |

**Current Shopee:** Shop ID 1147948100, 6 campaigns, ~Rp 1.15M/day ad spend
**Existing infra:** Python automation, SQLite DB, cron jobs, Hermes agents

---

## 🎯 PHASE 1: LAZADA (Month 1-2) — Lowest Hanging Fruit

### Why Lazada First?
- Same Alibaba ecosystem, similar seller backend
- Less competition than Shopee in some categories
- Cross-platform inventory sync possible
- Same target audience (Indonesia urban)

### Setup Checklist
| Step | Action | Owner | Timeline |
|------|--------|-------|----------|
| 1 | Register Lazada Seller account | Gerard | Week 1 |
| 2 | Apply for Lazada Open Platform API | Gerard | Week 1-2 |
| 3 | List top 10 SKUs (manual or bulk) | Gerard | Week 2 |
| 4 | Build Lazada API client (mirror Shopee structure) | Hermes | Week 2-3 |
| 5 | Set up Lazada ads automation | Hermes | Week 3-4 |
| 6 | Sync inventory Shopee ↔ Lazada | Hermes | Month 2 |

### Lazada API Access
- **Lazada Open Platform**: https://open.lazada.com/
- **Docs**: https://open.lazada.com/doc/doc.htm
- **Key APIs**: Product, Order, Finance, Seller, Logistics
- **Auth**: OAuth 2.0 (similar to Shopee)

### Automation Deliverables
```
lazada_client.py      # API wrapper (mirror shopee_client.py)
lazada_monitor.py     # Daily checks (stock, orders, ads)
lazada_optimizer.py   # Ad bid/budget automation
inventory_sync.py     # Cross-platform stock sync
```

---

## 🎯 PHASE 2: TIKTOK SHOP (Month 2-3) — Content + Commerce

### Why TikTok Shop?
- Fastest growing ecommerce in SEA
- Content-driven discovery (not search-driven like Shopee)
- Lower CPC, higher impulse purchases
- Perfect for umbrella visual demos

### Setup Checklist
| Step | Action | Owner | Timeline |
|------|--------|-------|----------|
| 1 | Register TikTok Shop Seller | Gerard | Week 1 |
| 2 | Apply for TikTok Shop API | Gerard | Week 1-2 |
| 3 | Create 10 product videos (AI-assisted) | Hermes | Week 2-3 |
| 4 | Set up TikTok Shop ads (Product Shopping Ads) | Hermes | Week 3-4 |
| 5 | Build TikTok API client | Hermes | Week 3-4 |
| 6 | Automate video content pipeline | Hermes | Month 3 |

### TikTok Shop API
- **Developer Portal**: https://seller.tiktok.com/
- **Docs**: https://partner.tiktokshop.com/doc/page/262731
- **Key APIs**: Product, Order, Fulfillment, Promotion
- **Auth**: App-based OAuth

### Content Automation Pipeline
```
PRODUCT_PHOTOS → AI_VIDEO_GENERATOR → TIKTOK_UPLOAD → ADS_BOOST
     ↑                                                              |
     └──────────── PERFORMANCE_DATA ← ANALYTICS ←┘
```

**Tools:**
- CapCut API (batch video creation)
- Canva API (thumbnails, overlays)
- HeyGen / D-ID (AI presenter — optional)
- TikTok Creative Center (trending sounds)

---

## 🎯 PHASE 3: META ADS (Month 3-4) — Off-Platform Traffic

### Why Meta Ads?
- Drive traffic to Shopee/Lazada/TikTok stores
- Retargeting website visitors
- Lookalike audiences from existing customers
- Higher AOV customers than platform-native

### Setup Checklist
| Step | Action | Owner | Timeline |
|------|--------|-------|----------|
| 1 | Create Meta Business Manager | Gerard | Week 1 |
| 2 | Set up Meta Pixel on store pages | Hermes | Week 1 |
| 3 | Connect Meta Catalog (product feed) | Hermes | Week 2 |
| 4 | Build Meta Ads API client | Hermes | Week 2-3 |
| 5 | Launch Advantage+ Shopping Campaign | Hermes | Week 3 |
| 6 | Automate creative rotation | Hermes | Month 4 |

### Meta Marketing API
- **Docs**: https://developers.facebook.com/docs/marketing-apis/
- **Key APIs**: Campaign, AdSet, Ad, Creative, Insights
- **Auth**: OAuth + System User token
- **Rate limits**: 200 calls/hour/app

### Automation Deliverables
```
meta_client.py         # Marketing API wrapper
meta_optimizer.py      # Budget/audience auto-adjust
creative_rotator.py    # A/B test ads automatically
pixel_tracker.py       # Conversion event tracking
```

---

## 🎯 PHASE 4: TOKOPEDIA (Month 4-5) — Market Coverage

### Why Tokopedia Last?
- Now part of TikTok (post-merger)
- API access more restricted
- Similar to Shopee, less incremental value
- Good for completeness, not priority

### Setup Checklist
| Step | Action | Owner | Timeline |
|------|--------|-------|----------|
| 1 | Register Tokopedia seller | Gerard | Week 1 |
| 2 | Request API access (if available) | Gerard | Week 1-2 |
| 3 | List products manually | Gerard | Week 2 |
| 4 | Build Tokopedia client (if API available) | Hermes | Week 3-4 |

---

## 🤖 HERMES AUTOMATION ARCHITECTURE

### Current State (Shopee Only)
```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Cron Jobs  │────▶│  Python API  │────▶│  Shopee API │
│  (4x daily) │     │   Clients    │     │             │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  SQLite DB   │
                    │  growth_data │
                    └──────────────┘
```

### Future State (Multi-Platform)
```
┌─────────────────────────────────────────────────────────┐
│                    HERMES GATEWAY                        │
│              (Telegram + Cron Scheduler)                 │
└─────────────────────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │  Shopee    │  │   Lazada   │  │  TikTok    │
    │  Agent     │  │   Agent    │  │  Agent     │
    └────────────┘  └────────────┘  └────────────┘
           │               │               │
           └───────────────┼───────────────┘
                           ▼
                    ┌──────────────┐
                    │  Unified DB  │
                    │  ecommerce   │
                    └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Meta Ads    │
                    │  (retarget)  │
                    └──────────────┘
```

### New Automation Modules

| Module | Purpose | Trigger |
|--------|---------|---------|
| `unified_client.py` | Abstract API layer for all platforms | All jobs |
| `inventory_sync.py` | Cross-platform stock management | Every 15 min |
| `pricing_engine.py` | Dynamic pricing by platform | Every 4 hours |
| `content_pipeline.py` | AI video/image generation | Daily |
| `ad_unified.py` | Multi-platform ad optimization | Every 4 hours |
| `reporting.py` | Consolidated P&L dashboard | Daily 8 AM |

---

## 📱 CONTENT CREATION AUTOMATION

### Video Pipeline (TikTok + Reels)
```
INPUT: Product photos + specs + price
  │
  ▼
┌─────────────────┐
│  AI Script Gen  │  ← GPT-4 / Claude (hooks, CTA)
└─────────────────┘
  │
  ▼
┌─────────────────┐
│  CapCut Batch   │  ← Auto-edit with trending template
└─────────────────┘
  │
  ▼
┌─────────────────┐
│  Auto-upload    │  ← TikTok API + Meta Content API
└─────────────────┘
  │
  ▼
┌─────────────────┐
│  Performance    │  ← Track views → sales
│  Feedback Loop  │
└─────────────────┘
```

### Image Pipeline (Shopee + Lazada + Meta)
```
INPUT: Product photo (white background)
  │
  ▼
┌─────────────────┐
│  AI Background  │  ← Scene generation (rain, outdoor, etc)
└─────────────────┘
  │
  ▼
┌─────────────────┐
│  Auto-resize    │  ← Platform-specific dimensions
└─────────────────┘
  │
  ▼
┌─────────────────┐
│  Text overlay   │  ← Price, promo, CTA in Indonesian
└─────────────────┘
  │
  ▼
┌─────────────────┐
│  A/B test       │  ← Upload 3 variants, auto-pick winner
└─────────────────┘
```

**AI Tools for Content:**
- **Video**: CapCut API, RunwayML, Pika Labs
- **Images**: Midjourney API, DALL-E 3, Canva API
- **Copy**: Claude/GPT-4 (Indonesian marketing copy)
- **Voice**: ElevenLabs (Indonesian voiceover)

---

## 💰 FINANCIAL PROJECTIONS

### Conservative Scenario (6 months)
| Platform | Month 1 | Month 3 | Month 6 |
|----------|---------|---------|---------|
| Shopee | Rp 9M | Rp 12M | Rp 15M |
| Lazada | Rp 0 | Rp 3M | Rp 6M |
| TikTok | Rp 0 | Rp 2M | Rp 5M |
| Meta Ads | Rp 0 | Rp 1M | Rp 3M |
| **Total** | **Rp 9M** | **Rp 18M** | **Rp 29M** |

### Ad Spend Budget
| Phase | Monthly Ad Spend | Expected ROAS |
|-------|-----------------|---------------|
| Month 1-2 (Lazada setup) | Rp 2M | 3-4x |
| Month 2-3 (TikTok launch) | Rp 3.5M | 2-3x (growth phase) |
| Month 3-4 (Meta + scale) | Rp 5M | 3-4x blended |
| Month 5-6 (optimize) | Rp 6M | 4-5x blended |

---

## ⚙️ TECHNICAL IMPLEMENTATION

### Week 1-2: Foundation
```bash
# 1. Create new workspace
cd ~/.openclaw/workspace
mkdir multi-platform-growth
cd multi-platform-growth

# 2. Reuse Shopee auth pattern
cp ../shopee-api-onboarding/auth_helper.py .
cp ../shopee-api-onboarding/shopee_client.py .

# 3. Create platform clients
mkdir -p platforms/{shopee,lazada,tiktok,meta}
touch platforms/__init__.py
```

### Week 3-4: Lazada Integration
```python
# platforms/lazada/client.py
class LazadaClient:
    """Mirror of ShopeeClient with Lazada endpoints"""
    BASE_URL = "https://api.lazada.co.id/rest"
    
    def get_products(self): ...
    def update_stock(self, sku, qty): ...
    def get_orders(self): ...
    def get_ads_report(self): ...
```

### Month 2: TikTok + Content
```python
# content_pipeline/generate_video.py
from hermes_tools import terminal

def create_product_video(product_id, template="trending_1"):
    # 1. Get product data
    product = db.get_product(product_id)
    
    # 2. Generate script
    script = ai.generate_script(product, hook_style="problem_agitation")
    
    # 3. Create video via CapCut API
    video_url = capcut.create(
        images=product.images,
        script=script,
        template=template,
        duration=15  # seconds
    )
    
    # 4. Upload to TikTok
    tiktok.upload(video_url, caption=script.caption)
    
    # 5. Log for tracking
    db.log_content(product_id, video_url, platform="tiktok")
```

### Month 3: Meta Ads
```python
# platforms/meta/client.py
class MetaAdsClient:
    """Facebook Marketing API wrapper"""
    
    def create_campaign(self, objective="SALES", ...): ...
    def create_adset(self, targeting, budget, ...): ...
    def create_ad(self, creative, ...): ...
    def get_insights(self, date_preset="last_7d"): ...
```

---

## 📋 IMMEDIATE NEXT STEPS

### This Week (You)
| # | Action | Time |
|---|--------|------|
| 1 | Register Lazada seller account | 30 min |
| 2 | Apply for Lazada Open Platform | 15 min |
| 3 | Take inventory: list top 20 SKUs for multi-platform | 1 hour |
| 4 | Set aside Rp 2M for Lazada launch ad budget | - |

### This Week (Hermes)
| # | Action | Time |
|---|--------|------|
| 1 | Scaffold Lazada API client | 2 hours |
| 2 | Build unified inventory sync module | 3 hours |
| 3 | Set up new cron jobs for Lazada monitoring | 1 hour |

---

## 🔄 HERMES CRON SCHEDULE (Future)

```
08:00  unified_daily_report    # All platforms P&L
09:00  lazada_optimizer        # Bid/budget adjust
10:00  tiktok_content_queue    # Generate today's videos
12:00  inventory_sync          # Cross-platform stock check
14:00  meta_ads_optimizer      # Audience/budget adjust
16:00  pricing_engine          # Dynamic price adjust
20:00  evening_check           # Orders, issues, next-day prep
```

---

## 🎯 SUCCESS METRICS

| Month | Platforms | Monthly GMV | Total ROAS | Automated Content |
|-------|-----------|-------------|------------|-------------------|
| 1 | 2 (S+L) | Rp 10M | 3.5x | 0 |
| 2 | 2 (S+L) | Rp 14M | 3.8x | 5 videos |
| 3 | 3 (S+L+T) | Rp 20M | 3.5x | 15 videos |
| 4 | 4 (S+L+T+M) | Rp 25M | 3.8x | 30 videos |
| 5 | 4 | Rp 28M | 4.2x | 45 videos |
| 6 | 4 | Rp 32M | 4.5x | 60 videos |

**Year 1 Target: Rp 400M GMV across 4 platforms**

---

*Plan generated by Hermes Agent | Review and approve to begin Phase 1*
