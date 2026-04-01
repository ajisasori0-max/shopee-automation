# Shopee Ads API - Go Live Request

## Application Details

**Partner ID:** 2030653  
**Shop ID:** 1147948100  
**Shop Name:** Payung Murah Jakarta  
**Business Type:** E-commerce (Umbrella Products)  
**Current Status:** Production Shop API Approved ✅

---

## Requested Ads API Permissions

| API Endpoint | Purpose | Use Case |
|--------------|---------|----------|
| `/api/v2/ads/get_cpc_ad_list` | List campaigns | Monitor active/paused campaigns |
| `/api/v2/ads/get_campaign_details` | Campaign details | View budget, targeting, status |
| `/api/v2/ads/get_total_ad_performance` | Performance metrics | ROAS, spend, impressions, clicks |
| `/api/v2/ads/update_campaign` | Edit campaigns | Adjust budgets, pause/resume |
| `/api/v2/ads/create_campaign` | Create campaigns | Launch new GMV Max or Manual CPC |

---

## Business Justification

### Current Situation:
- Running GMV Max campaigns with inconsistent algorithm behavior
- Need automated monitoring and alerts
- Manual campaign management is time-consuming
- Want to build dashboard for real-time optimization

### Technical Implementation:
1. **Monitoring Dashboard:** Track campaign performance in real-time
2. **Automated Alerts:** Notify when ROAS drops below target
3. **Budget Optimization:** Auto-adjust based on performance
4. **A/B Testing:** Systematically test different campaign settings

### Expected Benefits:
- Reduce manual campaign management time by 70%
- Improve ROAS through data-driven optimization
- Faster response to market changes
- Better inventory planning based on ad performance

---

## Security & Compliance

- All API calls use HMAC-SHA256 signatures
- Tokens stored securely (encrypted at rest)
- No customer PII stored in our systems
- Rate limiting compliance: max 1000 requests/minute
- Webhook endpoint secured with signature verification

---

## Contact Information

**Developer Email:** [Your email]  
**Technical Contact:** [Your name/phone]  
**Business Contact:** [Brother's contact if needed]  
**Emergency Contact:** [Your phone]

---

## Supporting Documents

1. ✅ Shop API already approved (Partner ID: 2030653)
2. ✅ Production shop active (Shop ID: 1147948100)
3. ✅ 380+ product reviews, 4.8★ rating
4. ✅ Rp63M sales in 5 months
5. ✅ Dashboard deployed: https://shopee-automation-70ts.onrender.com

---

## Test Credentials (for Shopee Review)

**Test Shop:** Same production shop (we're not using sandbox for ads)  
**API Client:** Python requests with proper signature  
**Test Scenario:** Read campaign list, view performance metrics

---

## Additional Notes

We understand Ads API access requires additional scrutiny. We commit to:
- Using APIs responsibly within rate limits
- Not manipulating ad auctions unfairly
- Maintaining accurate campaign data
- Reporting any API errors promptly

Please approve our request to access Shopee Ads APIs for automated campaign management.

Best regards,  
**Payung Murah Jakarta Team**
