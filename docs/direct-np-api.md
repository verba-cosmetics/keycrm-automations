# Direct Nova Poshta API — read-only prototype

**This PR is not a production shipping integration.** It provides a webhook receiver and a strict eligibility test only. No TTNs or tags are created; no CRM writes are sent.

Conditions: order status `ПОВНА ОПЛАТА`; SKU `BHCCD`, exactly 1 item and no other products; `Нова Пошта Кальчук` service; no TTN; domestic Nova Poshta *branch* delivery still needs explicit verification.

- Source: keyCRM order status change action `Send HTTP request` (send order ID only).
- Target: future HTTPS Cloudflare Worker URL; authorization header `Bearer <WEBHOOK_TOKEN>`.
- Worker independently fetches order from keyCRM and checks conditions.
- Code is intentionally fail-closed when the live keyCRM schema differs.
- Run tests locally with `node --test tests/direct_np_worker.test.mjs`.

## Blockers before real TTN creation

1. Confirm live keyCRM schema, specifically product SKU/quantity, status, shipping identifiers, tracking code and receiver warehouse.
2. Obtain Nova Poshta API key **in Cloudflare secrets**, never GitHub source, and sender identity/warehouse/contact references.
3. Verify the exact Nova Poshta InternetDocument.save request payload with a controlled test; the action creates a real delivery document.
4. Confirm a **documented and tested** method to write the NP tracking number into keyCRM. Public keyCRM API lists `PUT /order/{orderId}` but does not list a distinct create-shipment operation. Inserting a number as an external TTN may not allow printing within keyCRM.
5. Before enabling any write: persistent idempotency lock, webhook authenticity, **global lifetime quota of 3** (not 3 per invocation), order recheck, retries, rollback/reconciliation, explicit manual approval.
6. Disable the old tag workflow and any generic shipment triggers to prevent double-creation.

## Security

Repository is public. Never store API credentials, personally identifiable order data or shipment examples in commits, issues, logs or tests. This code has no deployment configuration and no cron; creating a PR does not expose a webhook or run it.

References: https://docs.keycrm.app/ , https://novaposhta.ua/en/for-business/cooperation/integration/ , https://help.keycrm.app/en/integrations-with-delivery-services/adding-ttn-is-not-created-in-keycrm
