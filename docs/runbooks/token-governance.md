# Token Governance Runbook

**Project:** CommerceOS Shopee Integration  
**Owner:** token_manager.py (single authority)  
**Public API:** `commerceos.platform.tokens.get_access_token(app_name)`

---

## 1. Token Lifecycle

### What we have
- **Production app** — Shopee Seller API (orders, products, inventory)
  - Partner ID: `2030653`
  - Token file: `tokens_production.json`
  - Access token lifetime: ~4 hours
  - Refresh token lifetime: 30 days
- **Ads app** — Shopee Ads API (campaigns, performance)
  - Partner ID: `2030650`
  - Token file: `tokens_ads.json`
  - Access token lifetime: ~4 hours
  - Refresh token lifetime: 30 days

### Single authority
Only `token_manager.py` may:
- Read token files
- Call Shopee's `/api/v2/auth/access_token/get` refresh endpoint
- Write to `tokens_production.json` or `tokens_ads.json`
- Exchange auth codes via `/api/v2/auth/token/get`

Every other module/script must call:

```python
from commerceos.platform.tokens import get_access_token
access_token = get_access_token('production')  # or 'ads'
```

### Why this matters
Shopee only allows **one active refresh token per app-shop**. If two scripts refresh independently, the second refresh invalidates the first refresh token. This causes a death spiral where tokens expire within hours.

---

## 2. Refresh Ownership

### Automatic refresh
- `token_manager.py --health` refreshes expired access tokens automatically.
- `token_manager.py --refresh` force-refreshes both apps.
- `scripts/live_resync.py` force-refreshes via the central provider before sync.
- Legacy scripts (`daily_monitor.py`, `growth_engine.py`, optimizers) now delegate refresh to `commerceos.platform.tokens`.

### Manual refresh
Only run this if you know the access tokens are stale:

```bash
cd /Users/gerard/.openclaw/workspace/shopee-api-onboarding
source .venv/bin/activate
python3 token_manager.py --refresh
```

### Health check
```bash
python3 token_manager.py --health
```

Expected output:
```json
{
  "production": {
    "status": "healthy",
    "access_token_valid": true,
    "refresh_token_days_remaining": 30,
    "needs_reauth": false
  },
  "ads": {
    "status": "healthy",
    "access_token_valid": true,
    "refresh_token_days_remaining": 30,
    "needs_reauth": false
  }
}
```

---

## 3. Recovery After Re-authorization

### When re-auth is needed
- `needs_reauth: true`
- `refresh_token_expired` error
- `error_shop_refresh_token` from Shopee

### Steps
1. Generate auth URL for the app:
   ```bash
   python3 generate_auth_url.py
   ```
2. Open the URL for the failing app in your browser.
3. Authorize the app in Shopee Seller Center.
4. Copy the `code=` value from the redirect URL.
5. Exchange it:
   ```bash
   python3 token_manager.py --exchange production <code>
   python3 token_manager.py --exchange ads <code>
   ```
6. Verify health:
   ```bash
   python3 token_manager.py --health
   ```

---

## 4. Emergency Rollback

If the central token provider breaks and operations need to resume immediately:

1. Pause all cron jobs:
   ```bash
   hermes cron pause shopee-token-health
   hermes cron pause shopee-daily-monitor
   hermes cron pause shopee-midday-check
   hermes cron pause shopee-evening-check
   hermes cron pause shopee-growth-engine
   ```
2. Restore token files from `archive/tokens_backup/` if available.
3. Run manual refresh:
   ```bash
   python3 token_manager.py --refresh
   ```
4. If that fails, re-authorize both apps (see section 3).

---

## 5. Monitoring Checklist

After any token-related change, verify:

- [ ] `python3 token_manager.py --health` shows both apps healthy.
- [ ] `refresh_token_days_remaining` is > 25.
- [ ] `access_token_valid` is true.
- [ ] `FULL_RESYNC=1 python3 scripts/live_resync.py` completes without auth errors.
- [ ] `python3 scripts/refresh_kpis.py` completes successfully.
- [ ] `python3 scripts/verify_kpis.py` shows `temporary: false` and all sources fresh.
- [ ] No `ALERT_*_reauth_needed.txt` files appear.
- [ ] Regression tests pass:
  ```bash
  python3 -m pytest tests/unit/test_token_governance.py -v
  ```

---

## 6. Known Shopee Limitations

1. **Single active refresh token.** Re-authorizing the same app twice in a row invalidates the previous refresh token. Always finish one app before starting the other, and verify the first before moving on.
2. **Access tokens last ~4 hours.** Automated jobs that run every 6 hours must refresh via the central provider before API calls.
3. **Refresh tokens last ~30 days.** The health check warns at day 25.
4. **`invalid_acceess_token` typo.** Shopee returns `invalid_acceess_token` (double `e`). Code handles both spellings.
5. **Ads and production are separate apps.** They have different partner IDs and different token files. One can be healthy while the other is expired.

---

## 7. Development Rules

### Forbidden in any non-`token_manager.py` file
- Calling `/api/v2/auth/access_token/get` directly
- Writing to `tokens_production.json` or `tokens_ads.json`
- Implementing `_save_tokens()` or similar token persistence
- Forcing a refresh except through `get_access_token(app_name, force_refresh=True)`

### Allowed
- Reading token files for display/metadata only
- Calling `get_access_token('production')` or `get_access_token('ads')`
- Calling `token_manager.py --exchange` from CLI or UI

### Enforcement
The regression test `tests/unit/test_token_governance.py` scans the repository for forbidden patterns and fails the build if any are found.

```bash
python3 -m pytest tests/unit/test_token_governance.py -v
```

---

## 8. Cron Jobs and Token Usage

| Job | Schedule | Token Source | Status |
|-----|----------|--------------|--------|
| shopee-token-health | every 6h | token_manager.py | active |
| shopee-daily-monitor | 08:00 | central provider via daily_monitor.py | active |
| shopee-midday-check | 14:00 | central provider via wrapper | active |
| shopee-evening-check | 20:00 | central provider via wrapper | active |
| shopee-growth-engine | 09:00 | central provider via growth_engine.py | active |

All cron jobs were paused during consolidation and resumed in phases. The 24-hour stability observation begins after the final job is resumed.

---

## 9. Contact / Escalation

If token health fails and re-auth does not fix it:
1. Check Shopee Seller Center → Open Platform → App List for app status.
2. Verify the redirect URI matches `https://shopee-automation-70ts.onrender.com`.
3. Check that no archived script was accidentally run.
4. Re-run the full verification sequence in section 5.
5. If still failing, the app credentials may have been revoked in Shopee — generate new partner credentials.
