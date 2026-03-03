# Shopee Open API Onboarding Package

> **For:** Gerard (Solo Entrepreneur, Indonesia)
> **Goal:** Get first working API call within 30 minutes
> **Last Updated:** 2025-02-25

---

## 📋 What You Have vs What You Need

### ✅ What You Should Already Have (From Shopee Developer Portal)

After registering at https://open.shopee.com, you should have:

| Credential | Format | Where to Find |
|------------|--------|---------------|
| **Partner ID** | Numeric (e.g., `123456`) | Developer Portal → App Details |
| **Partner Key** | Long string (e.g., `a1b2c3d4...`) | Developer Portal → App Details (click "Show") |
| **Shop ID** | Numeric (e.g., `789012`) | Seller Center → Settings → Shop Settings |

### 🔧 What We'll Create Today

- `access_token` - Temporary token (4-hour lifetime)
- `refresh_token` - Long-lived token (30-day lifetime)
- Test script to verify connectivity

---

## 🚀 Quick Start (Get First API Call in 5 Steps)

### Step 1: Fill in Your Credentials

Copy `.env.example` to `.env` and fill in your actual credentials:

```bash
cp .env.example .env
```

Edit `.env` with your real values:
```bash
SHOPEE_PARTNER_ID=123456          # Your actual Partner ID
SHOPEE_PARTNER_KEY=your_key_here  # Your actual Partner Key  
SHOPEE_SHOP_ID=789012             # Your actual Shop ID
SHOPEE_REGION=id                  # 'id' for Indonesia
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Generate Authorization URL

Run the auth helper to get your authorization URL:

```bash
python auth_helper.py
```

This will output a URL like:
```
https://partner.shopeemobile.com/api/v2/shop/auth_partner?
  partner_id=123456
  &redirect_uri=http://localhost:8080/callback
  &timestamp=...
  &sign=...
```

### Step 4: Authorize Your Shop

1. **Copy** the URL from Step 3
2. **Paste** into your browser
3. **Log in** with your Shopee Seller account
4. **Authorize** the app to access your shop
5. **Copy** the `code` parameter from the redirect URL

### Step 5: Exchange Code for Tokens

Run the token exchange:

```bash
python get_token.py --code YOUR_AUTH_CODE
```

This will save your tokens to `.env`:
```bash
SHOPEE_ACCESS_TOKEN=abc123...
SHOPEE_REFRESH_TOKEN=xyz789...
```

### 🎉 Step 6: Test Your First API Call

```bash
python test_connection.py
```

If successful, you'll see your shop info:
```json
{
  "shop_name": "Gerard's Store",
  "shop_id": 789012,
  "country": "ID",
  "status": "active"
}
```

---

## 📁 Files in This Package

| File | Purpose |
|------|---------|
| `.env.example` | Template for your credentials |
| `requirements.txt` | Python dependencies |
| `auth_helper.py` | Generate authorization URLs |
| `get_token.py` | Exchange auth code for tokens |
| `test_connection.py` | Verify API connectivity |
| `shopee_client.py` | Reusable API client class |
| `quick_examples.py` | Common operations (orders, products, stock) |
| `ONBOARDING.md` | This file - start here! |
| `API_REFERENCE.md` | Quick reference for common endpoints |

---

## 🔑 Understanding the Auth Flow

```
┌─────────────────────────────────────────────────────────────┐
│  SHOPEE API AUTHENTICATION FLOW                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. YOUR APP                    SHOPEE SERVERS              │
│     │                               │                       │
│     │── Generate auth URL ─────────>│                       │
│     │   (signed with partner_key)   │                       │
│     │                               │                       │
│     │<──────── Redirect ────────────│                       │
│     │   (seller logs in & approves) │                       │
│     │                               │                       │
│  2. │<──────── Callback ────────────│                       │
│     │   (with auth code)            │                       │
│     │                               │                       │
│     │── Exchange code for tokens ──>│                       │
│     │                               │                       │
│     │<──────── Tokens ──────────────│                       │
│     │   (access_token + refresh_token)                      │
│     │                               │                       │
│  3. │── API calls with token ──────>│                       │
│     │   (access_token lasts 4hrs)   │                       │
│     │                               │                       │
│     │<──────── Data ────────────────│                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Token Lifetimes

| Token | Lifetime | Purpose |
|-------|----------|---------|
| `access_token` | 4 hours | Make API calls |
| `refresh_token` | 30 days | Get new access_token |

**Important:** The refresh_token also refreshes when you get a new access_token. Store it!

---

## 🎯 First Priority Endpoints

As a solo seller, start with these:

### 1. Orders (Most Important)
```python
# Get new orders
GET /api/v2/order/get_order_list

# Get order details
GET /api/v2/order/get_order_detail

# Mark as ready to ship
POST /api/v2/order/rts
```

### 2. Products/Inventory
```python
# List your products
GET /api/v2/product/get_item_list

# Update stock
POST /api/v2/product/update_stock

# Update price
POST /api/v2/product/update_price
```

### 3. Logistics
```python
# Get shipping channels
GET /api/v2/logistics/get_channel_list

# Get tracking number
GET /api/v2/logistics/get_tracking_number
```

---

## 🔄 Token Refresh (Important!)

Since access_token expires every 4 hours, you need to refresh it:

```python
python refresh_token.py
```

Or use the auto-refresh in `shopee_client.py`:

```python
from shopee_client import ShopeeClient

client = ShopeeClient(auto_refresh=True)
# Will automatically refresh token when needed
```

---

## 🛡️ Security Checklist

- [ ] `.env` file is in `.gitignore` (NEVER commit credentials!)
- [ ] `partner_key` is never logged or printed
- [ ] Tokens are stored securely (not in code)
- [ ] Webhook endpoints use HTTPS
- [ ] Rate limits are respected

---

## 🆘 Troubleshooting

### "Invalid signature" error
- Check your `partner_key` is correct
- Verify system clock is accurate (NTP synced)
- Ensure signature is generated with correct parameters

### "Auth failed" error
- Token may be expired - run `refresh_token.py`
- Shop may not be authorized - re-run auth flow
- Partner ID may be incorrect

### "Shop not found" error
- Verify `shop_id` is correct
- Shop may be in different region
- Check shop is active

### Rate limit errors (429)
- Add delays between requests
- Implement exponential backoff
- Check `X-RateLimit-Reset` header

---

## 📚 Next Steps After Onboarding

1. **Set up webhooks** for real-time order notifications
2. **Build inventory sync** to prevent overselling
3. **Automate order processing** workflow
4. **Create dashboards** for sales analytics

See `quick_examples.py` for code samples of these use cases.

---

## 📞 Support Resources

- **Shopee Developer Portal:** https://open.shopee.com
- **API Documentation:** https://open.shopee.com/documents?version=2
- **This Package Issues:** Check comments in each script

---

**Ready to start?** Go to Step 1 above and fill in your credentials!
