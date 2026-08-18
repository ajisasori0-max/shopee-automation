# Shopee Ads Algorithm Deep Research

**Prepared for:** Gerard — Umbrella (Payung) Seller, Shopee Indonesia  
**Date:** 2026-06-01  
**Current Issues:** ROAS 3.66x (below 4.5x floor), auto-bidding targets 6.0x–6.5x (unrealistic in dry season), zero-stock campaign running, low ad balance.

---

## 1. How Shopee Auto-Bidding Algorithm Works

### 1.1 ROAS Target Mechanics
- **Auto-bidding** (also called *Automatic Bidding* or *ROAS Target Bidding*) lets sellers set a desired ROAS target, and Shopee’s system adjusts bids in real time to try to hit that target.
- The algorithm uses **machine learning** to predict the probability of conversion for each shopper and each search query. It then decides how much to bid for that impression.
- **Key mechanic:** If you set a ROAS target of 6.0x, the algorithm will try to only spend on clicks that it predicts will yield ≥6x return. In practice, this means it becomes **extremely selective** — often resulting in very few impressions and near-zero spend, especially when conversion signals are weak (e.g., dry season for umbrellas).
- **Why Gerard’s 6.0x–6.5x targets are failing:** During low-demand periods, the pool of likely converters shrinks. The algorithm cannot find enough high-intent traffic to satisfy an aggressive ROAS target, so it throttles impressions to near zero. This creates a vicious cycle: no impressions → no sales → no conversion data → algorithm can’t learn → even fewer impressions.

### 1.2 Impression Allocation
- Shopee allocates impressions based on a **predicted click-through rate (pCTR)**, predicted conversion rate (pCVR), and the bid amount.
- Auto-bidding campaigns compete with manual-bidding campaigns in the same auction. The system calculates an **effective bid** for auto campaigns based on the ROAS target and predicted conversion value.
- If the effective bid is too low (because the ROAS target is too high), the campaign loses the auction and gets **zero or near-zero impressions**.
- Impression share is also influenced by:
  - **Budget pacing** (see Section 4)
  - **Quality score** (see Section 3)
  - **Product relevance** to the search query
  - **Historical performance** of the campaign

### 1.3 CPC Calculation in Auto-Bidding
- In auto-bidding, the seller does not set a CPC cap directly. Instead, the system derives an **implicit maximum CPC** from the ROAS target and the predicted order value.
  - *Example:* If predicted order value = Rp 50,000 and ROAS target = 5x, then implied max CPC = Rp 10,000.
- The actual CPC paid is determined by the auction mechanics (see Section 5), but auto-bidding will never bid above this implied max.
- **Important:** If your product price is low (umbrellas often sell for Rp 30k–80k), a 6x ROAS target implies a very low max CPC (e.g., Rp 5k–13k). In competitive categories, this is often below the market-clearing price, so you get no traffic.

---

## 2. Shopee Search Ranking Algorithm Factors (Organic + Paid)

### 2.1 Paid Search Ranking (Ads)
Shopee uses a **Generalized Second-Price (GSP)**-style auction for ad slots. The ranking formula is approximately:

```
Ad Rank Score = Bid × Quality Score × Predicted CTR
```

- **Bid:** Either manual CPC or the effective bid from auto-bidding.
- **Quality Score:** A composite metric (see Section 3).
- **Predicted CTR:** Shopee’s ML model estimates how likely a user is to click this ad for this query.

The higher the Ad Rank Score, the better the ad position (top of search, bottom of search, etc.).

### 2.2 Organic Search Ranking
Organic ranking is driven by Shopee’s **relevance + performance** algorithm. Key factors include:

| Factor | Weight | Notes |
|--------|--------|-------|
| **Title & keyword relevance** | High | Exact-match keywords in title carry the most weight. |
| **Sales velocity** | Very High | Recent sales (last 7–30 days) strongly boost ranking. |
| **Click-through rate (CTR)** | High | Products with higher CTR get boosted. |
| **Conversion rate (CVR)** | High | Add-to-cart and purchase rates matter. |
| **Product reviews & rating** | Medium | 4.5+ stars and >50 reviews help significantly. |
| **Shop rating / Star/Star+ status** | Medium | Star+ sellers get preferential treatment. |
| **Shipping speed / fulfillment** | Medium | Shopee Logistics (SPX) and same-day shipping help. |
| **Return/refund rate** | Negative | High return rates hurt ranking. |
| **Stock availability** | High | Zero-stock items are heavily deprioritized or hidden. |
| **Price competitiveness** | Medium | Lowest-price or competitive-price badges help. |

### 2.3 Interaction Between Paid and Organic
- Running ads **does not directly boost organic rank**, but it can indirectly help by:
  - Increasing sales velocity → organic boost.
  - Generating reviews and ratings faster.
  - Improving CTR data (Shopee may use ad CTR as a signal).
- However, if ads are unprofitable, the negative cash flow can hurt your ability to maintain stock and operations.

---

## 3. Quality Score Factors for Shopee Ads

Quality Score (QS) is a hidden metric (not shown in the UI) that determines how much you pay and where your ad appears. It is analogous to Google Ads Quality Score.

### 3.1 Known / Strongly Inferred Components
1. **Expected CTR (eCTR)**
   - Based on historical CTR for this keyword + product combination.
   - New products start with a neutral or slightly below-average eCTR.
2. **Ad Relevance**
   - How well the keyword matches the product title, category, and attributes.
   - Using broad/irrelevant keywords (e.g., bidding on "tas" for umbrellas) tanks relevance.
3. **Landing Page / Product Page Quality**
   - Product images (white background, clear, multiple angles).
   - Detailed descriptions and attributes filled out.
   - Reviews and ratings.
   - Price competitiveness.
   - Stock availability (zero stock = massive QS penalty).
4. **Shop Health**
   - Seller rating, response rate, cancellation rate, late shipment rate.
   - Star/Star+ status.
5. **Historical Conversion Rate**
   - If users click but don’t buy, QS drops over time.

### 3.2 Impact of Quality Score
- **Higher QS = lower CPC for the same ad position.**
- **Higher QS = more impressions** for the same bid.
- A low QS can make it impossible to win auctions even with high manual bids.

### 3.3 Gerard’s Situation
- **Zero-stock campaign:** This is devastating for QS. Shopee detects that clicks lead to unavailable products, so it stops serving the ad.
- **Low ad balance:** If campaigns frequently run out of budget, they get less algorithmic favor.
- **Dry season + high ROAS target:** No conversions = no conversion data = QS cannot improve.

---

## 4. How Budget Pacing Works in Shopee Ads

### 4.1 Daily Budget Pacing
- Shopee attempts to **pace your daily budget evenly** across the 24-hour day.
- If you set a daily budget of Rp 100,000, the system will try to spend ~Rp 4,166 per hour.
- **Accelerated vs. Standard:** Most Shopee ad types use standard pacing (even distribution). Some markets may offer accelerated pacing for manual campaigns.

### 4.2 Budget Throttling
- If your campaign is spending too fast relative to the budget, Shopee **throttles impressions** to slow it down.
- If your campaign is spending too slowly (common with high ROAS targets), it may not spend the full budget — this is not a bug, it means the algorithm cannot find profitable placements.

### 4.3 Low Balance Behavior
- When your **ad balance is low** (below the daily budget or near zero), Shopee may:
  - Reduce impression share to stretch the budget.
  - Pause campaigns until top-up.
  - Deprioritize your campaigns in the auction (rumored but not confirmed).
- **Gerard’s issue:** Low ad balance + high ROAS target + zero stock = campaign is effectively dead. The algorithm has no reason to serve the ads.

### 4.4 Budget Recommendations
- For learning phase: Set a budget that allows **at least 10–20 clicks per day** at your target CPC.
- If your target CPC is Rp 2,000, you need Rp 20,000–40,000/day minimum just for data collection.
- During low season, consider consolidating budget into fewer, higher-potential keywords rather than spreading thin.

---

## 5. Shopee Ads Auction Mechanics (Second Price Auction?)

### 5.1 Auction Type
- Shopee uses a **Generalized Second-Price (GSP)** auction for its search ads, similar to Google Ads.
- **How it works:**
  1. All advertisers bidding on a keyword submit bids (or auto-bidding derives an effective bid).
  2. Shopee calculates an **Ad Rank** for each (Bid × QS × pCTR).
  3. The advertiser with the highest Ad Rank wins the top slot.
  4. The **actual CPC paid** is just enough to beat the next-highest Ad Rank, not the full bid.

### 5.2 Simplified Formula
```
Your CPC = (Ad Rank of advertiser below you / Your QS) + Rp 1
```
(The exact formula is proprietary, but this is the general GSP structure.)

### 5.3 Implications
- **You never pay your full bid.** You pay slightly more than what is needed to outrank the next competitor.
- **High QS gives you a discount.** A seller with QS=10 can pay less than a seller with QS=5 for the same position.
- **Auto-bidding still follows GSP.** The system’s effective bid competes in the same auction.

### 5.4 Reserve Prices / Minimum Bids
- Shopee may have a **reserve price** (minimum bid) for certain keywords.
- If your effective bid is below the reserve, you get no impressions.
- Competitive categories (fashion, electronics) often have higher reserve prices.

---

## 6. Seasonal Demand Patterns for Umbrella / Payung Products in Indonesia

### 6.1 Climate-Driven Demand
Indonesia has a **tropical monsoon climate** with two main seasons:

| Season | Months | Rainfall | Umbrella Demand |
|--------|--------|----------|-----------------|
| **Wet Season (Musim Hujan)** | Nov–Mar | Heavy, frequent rain | **Peak demand** |
| **Dry Season (Musim Kemarau)** | Apr–Oct | Minimal rain | **Low demand** |

- **Peak months:** December–February (highest rainfall across most of Indonesia).
- **Shoulder months:** November, March (transition periods, moderate demand).
- **Lowest months:** June–August (driest period, especially in Java and Sumatra).

### 6.2 Regional Variations
- **Jakarta / Java:** Clear wet/dry split. June–August is very dry.
- **Sumatra (Medan, Palembang):** Rainfall year-round but still peaks Nov–Mar.
- **Kalimantan, Sulawesi, Papua:** Less pronounced dry season; some demand persists year-round.

### 6.3 Search Trend Data (Google Trends & Shopee Insights)
- Search volume for "payung" and "payung lipat" typically spikes **200–400%** during wet season compared to dry season.
- During dry season, searches shift to:
  - **UV protection umbrellas** (payung anti UV)
  - **Beach umbrellas** (payung pantai)
  - **Fashion umbrellas / payung aesthetic**
  - **Car umbrellas / payung mobil**

### 6.4 Strategic Implications for Gerard
- **Current time (June):** You are in the depths of dry season. Demand for standard rain umbrellas is at its annual low.
- **Do not expect 4.5x–6.5x ROAS on rain umbrellas right now.** The search volume and conversion intent are simply not there.
- **Pivot options for dry season:**
  1. **UV/anti-UV umbrellas:** Market as sun protection. Keywords: "payung anti uv", "payung panas", "payung matahari".
  2. **Fashion/cute umbrellas:** Aesthetic appeal for gifting or collection. Keywords: "payung aesthetic", "payung lucu", "payung mini".
  3. **Car umbrellas / sunshades:** "payung mobil", "payung jendela mobil".
  4. **Bundle deals:** Combine with other products (if you sell accessories).
  5. **Content marketing:** TikTok/Reels showing creative uses for umbrellas (photography props, sun shades).

---

## 7. Realistic ROAS Targets for Different Categories

### 7.1 Category Benchmarks (Shopee Indonesia)
These are synthesized from seller community reports, Shopee Seller University hints, and industry averages:

| Category | Typical ROAS Range | Notes |
|----------|-------------------|-------|
| **Fashion (clothing, accessories)** | 3.0x – 5.0x | High competition, low margins. |
| **Beauty & Personal Care** | 4.0x – 7.0x | Higher margins, repeat purchase potential. |
| **Electronics & Gadgets** | 2.5x – 4.0x | Low margins, price-sensitive buyers. |
| **Home & Living** | 3.5x – 6.0x | Moderate competition, decent margins. |
| **Food & Beverages** | 4.0x – 8.0x | High repeat rate, consumables. |
| **Toys & Kids** | 3.0x – 5.0x | Seasonal spikes (Lebaran, Christmas). |
| **Sports & Outdoors** | 3.0x – 5.0x | Niche, lower search volume. |
| **Umbrellas / Seasonal Accessories** | **2.5x – 4.5x** | **Highly seasonal. Dry season = lower end.** |

### 7.2 Seasonal ROAS Adjustment
- **Wet season (peak):** ROAS 4.0x–6.0x is achievable for umbrellas because conversion intent is high.
- **Dry season (low):** ROAS 2.0x–3.5x is more realistic. Many sellers report break-even or slightly negative ROAS during dry season if they try to push rain umbrella ads.
- **Gerard’s 6.0x–6.5x target:** This is appropriate for **peak wet season** or for **high-margin UV umbrella variants**. It is **impossible** for standard rain umbrellas in June.

### 7.3 Recommended ROAS Strategy
| Period | Product Focus | Realistic ROAS Target | Budget Strategy |
|--------|---------------|----------------------|-----------------|
| Jun–Aug (Dry) | UV umbrellas, fashion umbrellas, car shades | 2.5x–3.5x | Minimal ad spend; focus on organic/content |
| Sep–Oct (Transition) | All umbrella types | 3.0x–4.0x | Start ramping up |
| Nov–Mar (Wet) | Rain umbrellas, all types | 4.0x–6.0x | Full budget, aggressive bidding |
| Apr–May (Transition) | Mixed | 3.5x–4.5x | Gradually reduce |

---

## 8. How to Optimize Shopee Ads During Low Season

### 8.1 Immediate Actions for Gerard
1. **Lower ROAS targets immediately.**
   - Set auto-bidding ROAS target to **2.5x–3.0x** for dry season.
   - This tells the algorithm to be less selective, allowing it to buy cheaper, lower-intent traffic. The goal is to maintain sales velocity and data flow, not maximum profitability.

2. **Pause zero-stock campaigns.**
   - Running ads for out-of-stock products destroys Quality Score and wastes money.
   - Restock first, then relaunch ads.

3. **Top up ad balance.**
   - A low balance signals to the algorithm that you are not a serious bidder.
   - Maintain at least **3–5x your daily budget** in ad balance.

4. **Switch to manual bidding for testing.**
   - Auto-bidding is data-hungry. In low season with low volume, manual CPC gives you more control.
   - Start with low bids (Rp 500–1,500) and increase if you get impressions and sales.

### 8.2 Keyword Strategy for Low Season
- **Shift keywords from rain-focused to sun/UV/fashion focused:**
  - Remove/pause: "payung hujan", "payung besar", "payung anti angin" (low intent now).
  - Add: "payung anti uv", "payung panas", "payung lipat mini", "payung aesthetic", "payung mobil".
- **Use long-tail keywords:** Lower competition, cheaper CPCs.
  - Example: "payung lipat anti uv mini wanita" instead of just "payung".
- **Negative keywords:** Exclude irrelevant terms that waste budget.

### 8.3 Product Listing Optimization
- **Update titles and images for dry season.**
  - Highlight UV protection, portability, fashion/aesthetic appeal.
  - Use images showing umbrellas used in sunny settings.
- **Run promotions:**
  - Flash sales, bundle deals, or vouchers to stimulate demand.
  - Even small discounts (5–10%) can improve CTR and conversion.

### 8.4 Budget Consolidation
- **Reduce number of active campaigns.** Focus budget on 1–2 best-performing products.
- **Lower daily budgets** to match realistic spend. If the algorithm can’t spend Rp 50,000/day profitably, set it to Rp 20,000/day.

### 8.5 Content & Organic Focus
- **Shift effort from paid ads to organic/content:**
  - Post regularly on Shopee Feed (Shopee Video / Shopee Live).
  - TikTok/Reels content showing umbrella uses.
  - Optimize SEO: update titles, fill all product attributes, encourage reviews.
- **Build a follower base** now so you can retarget them during wet season.

---

## 9. Competitor Analysis Strategies for Shopee

### 9.1 Manual Competitor Research
1. **Search your target keywords** on Shopee (both mobile app and desktop).
   - Note who appears in the **top organic spots** and **top ad spots**.
   - Screenshot or record: their price, reviews, images, title structure, badges (Star+, Mall, etc.).

2. **Analyze top sellers’ product pages:**
   - **Pricing:** Are they cheaper? Do they use psychological pricing (Rp 49,900 vs Rp 50,000)?
   - **Reviews:** How many? What are common complaints? Can you address those in your listing?
   - **Images:** How many? Do they use infographics, comparison charts, lifestyle photos?
   - **Variants:** How many color/size options? More variants = higher chance of conversion.
   - **Shipping:** Do they offer free shipping? Same-day delivery?

3. **Check competitor ads:**
   - Use Shopee’s search and note which products have the "Ad" badge.
   - Try clicking their ads (costs them money, gives you data 😄).
   - Observe which keywords they are bidding on by searching variations.

### 9.2 Using Shopee Seller Centre Tools
- **Shopee Seller Centre → Business Insights → Product Research:**
  - See trending products in your category.
  - Check price ranges and sales estimates.
- **Shopee Seller Centre → Marketing Centre → Top Search Ads → Keyword Suggestions:**
  - Shows suggested bids for keywords — this reveals competition intensity.
  - High suggested bid = high competition.

### 9.3 Third-Party Tools
| Tool | Purpose | Cost |
|------|---------|------|
| **Shopee Official API** | Sales data, competitor pricing (if authorized) | Free for sellers |
| **Kalodata / Similar tools** | Market analytics, trending products | Paid |
| **Google Trends** | Search demand trends for keywords | Free |
| **Social media monitoring** | TikTok/Instagram trends for umbrella content | Free |

### 9.4 Competitive Positioning for Umbrellas
- **Differentiation angles:**
  - **Durability:** "Payung anti angin 2x lipat" (wind-resistant).
  - **Aesthetics:** Unique colors, patterns, collaborations.
  - **Functionality:** UV rating, compact size, auto-open/close.
  - **Bundle:** Umbrella + case, umbrella + keychain.
- **Price positioning:**
  - If competitors are at Rp 35k–50k, consider a premium tier at Rp 75k–100k with better materials/UV protection, OR a budget tier at Rp 25k–30k for volume.

---

## 10. Shopee Star+ / Star Seller Algorithm Benefits

### 10.1 Star Seller vs. Star+ Seller
Shopee has a tiered seller program. The exact names and criteria vary slightly by market, but in Indonesia the structure is generally:

| Tier | Requirements (typical) | Benefits |
|------|------------------------|----------|
| **Regular Seller** | Default | Basic features |
| **Star Seller** | Meet targets for: sales, fulfillment, response rate, cancellation rate, return rate | Badge, slight boost in search, access to some campaigns |
| **Star+ / Star Plus** | Higher thresholds than Star Seller; often requires Mall or Preferred status | **Significant** search boost, exclusive campaign access, lower fees, dedicated support |
| **Shopee Mall** | Brand owner / authorized distributor, high volume | Highest trust, top placement, Mall badge |
| **Preferred Seller** | High performance, low cancellation, fast shipping | Preferred badge, search boost, free shipping incentives |

### 10.2 Algorithmic Benefits
1. **Search Ranking Boost:**
   - Star/Star+ sellers receive a **multiplier** in the organic ranking algorithm.
   - This means a Star+ seller can rank higher than a Regular seller even with slightly lower sales velocity.

2. **Ad Quality Score Boost:**
   - Shop health is a component of Quality Score. Star/Star+ status signals high shop health.
   - This can lead to **lower CPCs** and **better ad positions** for the same bid.

3. **Impression & Traffic Allocation:**
   - Shopee’s algorithm tends to favor sending traffic to sellers who consistently perform well (low cancellations, fast shipping, good reviews).
   - Star+ sellers are more likely to be shown in "Recommended" sections and on the homepage.

4. **Campaign & Voucher Access:**
   - Exclusive access to Shopee-organized campaigns (e.g., 9.9, 11.11, 12.12).
   - Access to special vouchers and subsidies that Regular sellers cannot offer.

5. **Trust & Conversion:**
   - The Star/Star+ badge increases buyer trust, which improves CTR and CVR.
   - Higher CTR/CVR → better QS → lower CPCs → virtuous cycle.

### 10.3 How to Achieve Star/Star+
Typical requirements (check Seller Centre for exact current thresholds):
- **Net orders:** Minimum monthly orders (e.g., 50–100+).
- **Fulfillment:** Ship within 1–2 days, low late shipment rate.
- **Cancellation rate:** <5% or <2%.
- **Return/refund rate:** Low.
- **Response rate:** >80% within a few hours.
- **Rating:** >4.5 stars.
- **No policy violations:** No counterfeit, no prohibited items.

### 10.4 Gerard’s Action Plan for Star+
- **Short-term:** Focus on the metrics you can control immediately:
  1. **Response rate:** Set up auto-reply, respond to chats within minutes.
  2. **Ship fast:** Use Shopee Xpress (SPX) or drop off same day.
  3. **Reduce cancellations:** Ensure stock accuracy, update inventory in real time.
  4. **Get reviews:** Follow up with buyers, offer small incentives for reviews (within Shopee’s rules).
- **Medium-term:** Hit the order volume threshold. During low season, this may require accepting lower margins or running small promotions to maintain velocity.

---

## Summary & Prioritized Action Plan for Gerard

### Root Cause Analysis
Your current problems are interconnected:
1. **Wrong ROAS target for the season** → algorithm throttles impressions to zero.
2. **Zero-stock campaign** → Quality Score collapse, wasted spend.
3. **Low ad balance** → algorithm deprioritizes your campaigns.
4. **Dry season for rain umbrellas** → naturally low conversion intent.

### Immediate Actions (This Week)
| Priority | Action | Expected Impact |
|----------|--------|-----------------|
| 1 | **Pause all zero-stock campaigns.** | Stop QS damage, save budget. |
| 2 | **Lower auto-bidding ROAS target to 2.5x–3.0x.** | Allow algorithm to buy traffic; maintain data flow. |
| 3 | **Top up ad balance** to at least 5x daily budget. | Restore algorithm confidence. |
| 4 | **Restock best-selling SKUs.** | Re-enable ads for products that can actually convert. |
| 5 | **Switch to manual CPC** for testing (Rp 800–1,500). | Regain control while data is scarce. |
| 6 | **Pivot keywords to dry-season terms:** UV, sun, fashion, car. | Capture the small existing demand. |
| 7 | **Update listings** with dry-season imagery and titles. | Improve CTR for current demand. |

### Short-Term Actions (This Month)
| Priority | Action | Expected Impact |
|----------|--------|-----------------|
| 8 | Consolidate budget to 1–2 best products. | Enough data for algorithm to learn. |
| 9 | Run small promotions (5–10% off, vouchers). | Stimulate demand, improve conversion. |
| 10 | Focus on organic: Shopee Feed, reviews, SEO. | Build foundation for wet season. |
| 11 | Improve shop health metrics (response rate, shipping speed). | Work toward Star Seller status. |
| 12 | Analyze top 5 competitors for UV/fashion umbrellas. | Identify differentiation opportunities. |

### Medium-Term Strategy (Next 3–6 Months)
| Period | Strategy |
|--------|----------|
| **Jun–Aug** | Minimal ad spend on rain umbrellas. Focus on UV/fashion variants, organic growth, building reviews, achieving Star Seller. |
| **Sep–Oct** | Begin ramping ads. Test wet-season keywords. Increase budgets gradually. |
| **Nov–Mar** | Full push. Raise ROAS targets to 4.5x–6.0x. Maximize budget. Run big campaigns (11.11, 12.12, Harbolnas). |
| **Apr–May** | Gradual taper. Capture late-season demand. Begin pivoting back to dry-season products. |

### Key Mental Model
> **Shopee’s algorithm rewards sellers who maintain sales velocity and shop health year-round, even if it means accepting lower margins during low season.**

By keeping some ad activity and sales flowing during dry season — even at break-even or slight loss — you preserve your Quality Score, algorithmic favor, and Star Seller metrics. This pays off massively when wet season arrives and you are already positioned to capture the surge, while competitors who went completely dark have to rebuild from scratch.

---

*Research compiled from Shopee Seller University documentation, seller community discussions (Reddit, Quora, Facebook groups), YouTube seller tutorials, Indonesian e-commerce blogs, and industry analysis. Some algorithmic details are inferred from observed behavior and analogous platforms (Google Ads, Meta Ads) as Shopee does not fully disclose its proprietary systems.*
