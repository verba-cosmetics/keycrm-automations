# Verba Cosmetics — keyCRM automations

## BHCCD pilot: one cream / full payment / Nova Poshta

The first rule detects orders containing **exactly one** product (SKU `BHCCD`, quantity 1), with status **ПОВНА ОПЛАТА**, service **Нова Пошта Кальчук**, no existing TTN, and no `BHCCD_1PC` tag. It may add **only** that tag; other tags are untouched. A GitHub Actions workflow checks up to **20 orders on the first page** every 10 minutes.

### Safe default

- `AUTOMATION_ENABLED` is **false** unless explicitly set to `true` (no API calls)
- `DRY_RUN` is **true** unless explicitly set to `false`
- `ENABLE_TAG_WRITES` is **false** unless explicitly set to `true`
- Both write settings must be set to allow any mutation. No shipment is ever created by this Python script.

GitHub repository Settings → Secrets and variables → Actions:

Secret: `KEYCRM_API_KEY` (never commit an API key; existing repo secrets do not transfer automatically).

Variables for initial trial: `AUTOMATION_ENABLED=true`, `DRY_RUN=true`, `ENABLE_TAG_WRITES=false`. Trigger a manual `workflow_dispatch`, inspect logs, and validate the field shapes before considering write mode. **If the key is absent, the run will fail without changing CRM.**

The script resolves the IDs of the status, delivery service, and tag by their exact names through the API. Create `BHCCD_1PC` in keyCRM first; if names are missing/ambiguous, script stops rather than guessing.

### Later, configure keyCRM shipment trigger

Do **not** activate until a test confirms tagging and template behavior. Configure in keyCRM:

- Event: order status changed → **ПОВНА ОПЛАТА**
- Execute after **30 minutes**
- Conditions (AND): status includes **ПОВНА ОПЛАТА**; delivery service includes **Нова Пошта Кальчук**; tags include **BHCCD_1PC**; tracking code **does not exist**
- Action: **Automatically create shipment** with the validated packaging template and **no cash on delivery**

keyCRM's built-in automatic shipment supports Nova Poshta **branch delivery**. The 30-minute delay is not guaranteed to accommodate delayed GitHub Actions runs. Add reconciliation before production.

### Known limitations

Pilot only: first page / 20 orders; no full pagination. Actual keyCRM payload fields for `products`, `tags`, and `shipping.tracking_code` require verification from a real, **redacted** sample before enabling writes. If required fields are absent, eligibility fails closed. No buyer details are logged.

Tests: `python -m unittest discover -s tests -v`.

References: https://docs.keycrm.app/ and https://help.keycrm.app/uk/process-automation-api-and-more/avutomation-in-keycrm
