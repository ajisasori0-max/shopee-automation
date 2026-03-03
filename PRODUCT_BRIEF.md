# PPMJ Ads - Shopee Automation Platform

## Product Overview

**PPMJ Ads** is an automation platform for Shopee sellers that provides:
- **Stock Monitoring**: Automated alerts when inventory runs low
- **Price Tracking**: Monitor price changes across all products
- **Ad Performance**: Track ROAS, spend, and campaign effectiveness
- **Order Management**: Monitor returns, cancellations, and issues
- **Growth Insights**: Daily recommendations for sales improvement

## Technical Architecture

### Backend (Python)
- `shopee_client.py`: API client with automatic token refresh
- `automation.py`: Core automation engine
- `shopee_monitor.py`: Scheduled task runner
- `monthly_report.py`: Financial reporting

### Frontend (Streamlit Dashboard)
- Real-time monitoring dashboard
- Visual status indicators
- Historical logs and reports

## Demo Credentials

**Dashboard URL:** [To be deployed on Streamlit Cloud]

**Test Account:**
- Username: `demo@ppmjads.com`
- Password: `ShopeeDemo2024!`

**Note:** This is a backend automation service. The dashboard provides visibility into automated processes that run via cron jobs every 4 hours.

## Features for Shopee Review

### 1. Stock Alert System
- Monitors all product variants
- Alerts at 105 (warning) and 101 (critical) stock levels
- Prevents duplicate alerts until stock changes

### 2. Ad Campaign Monitoring
- Tracks ad spend vs GMV
- Calculates ROAS automatically
- Alerts when balance is low

### 3. Order Issue Tracking
- Monitors returns and cancellations
- Tracks cancellation reasons
- Identifies problematic orders

### 4. Automated Reporting
- Daily summaries at 7 AM
- Monthly financial reports on the 29th
- Exportable JSON data

## API Integration Points

- ✅ `v2.shop.get_shop_info`
- ✅ `v2.product.get_item_list`
- ✅ `v2.product.get_item_base_info`
- ✅ `v2.product.get_model_list`
- ✅ `v2.product.update_stock`
- ✅ `v2.product.update_price`
- ✅ `v2.ads.get_total_balance`
- ✅ `v2.order.get_order_list`
- ✅ `v2.order.get_order_detail`

## Security

- OAuth 2.0 authentication with Shopee
- Automatic token refresh
- HMAC-SHA256 signature verification
- No credentials stored in code (uses .env files)

## Compliance

- Follows Shopee Open Platform TOS
- Respects rate limits
- Implements proper error handling
- Uses official API endpoints only

## Contact

Developer: Gerard
Email: [Your email]
Location: Indonesia

---

*This application is currently in sandbox testing mode awaiting production approval.*
