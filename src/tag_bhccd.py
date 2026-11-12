"""Conservative single-cream tagger for keyCRM. No shipping is created here."""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://openapi.keycrm.app/v1"
SKU = "BHCCD"
STATUS_NAME = "ПОВНА ОПЛАТА"
DELIVERY_NAME = "Нова Пошта Кальчук"
TAG_NAME = "BHCCD_1PC"
MAX_MATCHES = 3  # Hard upper bound for a single workflow execution.


def records(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return payload["data"]
    raise ValueError("Unexpected API list response")


def unique_id(items, name):
    matches = [x.get("id") for x in items if isinstance(x, dict)
               and str(x.get("name", "")).strip().casefold() == name.casefold()]
    if len(matches) != 1 or not str(matches[0]).isdigit():
        raise ValueError(f"Expected exactly one configured CRM entry: {name}")
    return int(matches[0])


def sku_of(item):
    if not isinstance(item, dict):
        return None
    offer = item.get("offer")
    return item.get("sku") or (offer.get("sku") if isinstance(offer, dict) else None)


def one_cream(order):
    """Exactly one line, SKU BHCCD, quantity 1; no other products."""
    products = order.get("products")
    if not isinstance(products, list) or len(products) != 1:
        return False
    item = products[0]
    if not isinstance(item, dict) or str(sku_of(item) or "").strip() != SKU:
        return False
    try:
        return float(item["quantity"]) == 1
    except (KeyError, ValueError, TypeError):
        return False


def is_eligible(order, status_id, delivery_id, tag_id):
    if not isinstance(order, dict) or not one_cream(order):
        return False
    if str(order.get("status_id")) != str(status_id):
        return False
    shipping = order.get("shipping")
    if not isinstance(shipping, dict):
        return False
    if str(shipping.get("delivery_service_id")) != str(delivery_id):
        return False
    # Missing tracking fields are ambiguous: reject rather than risk duplicate shipping.
    if "tracking_code" not in shipping or shipping["tracking_code"] is None:
        return False
    if str(shipping["tracking_code"]).strip():
        return False
    tags = order.get("tags")
    if not isinstance(tags, list):
        return False
    if any(str(x.get("id")) == str(tag_id) for x in tags if isinstance(x, dict)):
        return False
    if not all(isinstance(x, dict) for x in tags):
        return False
    return True


class Client:
    def __init__(self, token):
        if not token:
            raise ValueError("KEYCRM_API_KEY is missing")
        self.token = token
        self.last_call = 0

    def call(self, path, params=None, method="GET"):
        since = time.monotonic() - self.last_call
        if since < 3.5:
            time.sleep(3.5 - since)
        query = "?" + urllib.parse.urlencode(params) if params else ""
        request = urllib.request.Request(API + path + query, method=method, headers={
            "Authorization": "Bearer " + self.token,
            "Accept": "application/json",
        })
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                body = response.read()
        except urllib.error.HTTPError as error:
            raise RuntimeError(f"keyCRM HTTP {error.code}: {method} {path}") from None
        finally:
            self.last_call = time.monotonic()
        return json.loads(body) if body else {}


def run():
    # Neither merely merging nor a scheduled workflow can mutate anything.
    enabled = os.getenv("AUTOMATION_ENABLED", "false").lower() == "true"
    dry_run = os.getenv("DRY_RUN", "true").lower() != "false"
    write_allowed = os.getenv("ENABLE_TAG_WRITES", "false").lower() == "true"
    if not enabled:
        print("Automation disabled; no API request made.")
        return
    client = Client(os.getenv("KEYCRM_API_KEY", ""))

    # Resolve IDs by exact names; do not guess numerical identifiers.
    status_id = unique_id(records(client.call("/order/status")), STATUS_NAME)
    delivery_id = unique_id(records(client.call("/order/delivery-service")), DELIVERY_NAME)
    tag_id = unique_id(records(client.call("/order/tag")), TAG_NAME)

    params = {"filter[status_id]": status_id, "limit": 20, "page": 1}
    orders = records(client.call("/order", params))
    if len(orders) > 20:
        raise ValueError("Unexpected page size")
    candidates = 0
    for order_summary in orders:
        order_id = order_summary.get("id") if isinstance(order_summary, dict) else None
        if not str(order_id or "").isdigit():
            continue
        payload = client.call(f"/order/{int(order_id)}", {"include": "products,tags"})
        order = payload.get("data", payload) if isinstance(payload, dict) else None
        if not is_eligible(order, status_id, delivery_id, tag_id):
            continue
        candidates += 1
        print(f"Eligible order ID: {order_id} (write suppressed: {dry_run or not write_allowed})")
        if not dry_run and write_allowed:
            client.call(f"/order/{int(order_id)}/tag/{tag_id}", method="POST")
            print(f"Tag added to order ID: {order_id}")
        if candidates >= MAX_MATCHES:
            print("Reached the hard limit of 3 matching orders; stopping.")
            break
    print(f"Scanned {len(orders)} of first page; eligible={candidates}; dry_run={dry_run}; writes_enabled={write_allowed}")


if __name__ == "__main__":
    run()
