/**
 * keyCRM -> Cloudflare Worker -> (future) Nova Poshta API.
 * Read-only prototype: NEVER creates a shipment or updates a CRM order.
 * A verified order payload is mandatory; missing data is a rejection.
 */
export const CONFIG = Object.freeze({
  sku: "BHCCD",
  status: "ПОВНА ОПЛАТА",
  delivery: "Нова Пошта Кальчук",
});

function equal(a, b) {
  return String(a ?? "").trim().toLocaleLowerCase("uk") === String(b).trim().toLocaleLowerCase("uk");
}

export function qualifies(order, statusId, deliveryId) {
  if (!order || !Number.isInteger(Number(statusId)) || !Number.isInteger(Number(deliveryId))) return false;
  const products = order.products;
  if (!Array.isArray(products) || products.length !== 1) return false;
  const item = products[0];
  const sku = item?.sku ?? item?.offer?.sku;
  if (sku !== CONFIG.sku || Number(item?.quantity) !== 1) return false;
  if (String(order.status_id) !== String(statusId)) return false;
  if (String(order.shipping?.delivery_service_id) !== String(deliveryId)) return false;
  // Missing tracking is ambiguous, not proof of no TTN.
  if (!order.shipping || !Object.hasOwn(order.shipping, "tracking_code")) return false;
  if (order.shipping.tracking_code === null || String(order.shipping.tracking_code).trim() !== "") return false;
  return true;
}

function list(json) {
  const data = Array.isArray(json) ? json : json?.data;
  if (!Array.isArray(data)) throw new Error("Unexpected reference data");
  return data;
}

function resolveId(entries, name) {
  const matches = list(entries).filter((entry) => equal(entry?.name, name));
  if (matches.length !== 1 || !Number.isInteger(Number(matches[0].id))) throw new Error("Ambiguous CRM reference");
  return matches[0].id;
}

async function crmGet(env, path) {
  const response = await fetch("https://openapi.keycrm.app/v1" + path, {
    headers: {Authorization: "Bearer " + env.KEYCRM_API_KEY, Accept: "application/json"},
  });
  if (!response.ok) throw new Error("CRM request failed");
  return response.json();
}

function orderIdFrom(payload) {
  // Only a supported direct id or nested model.id. No guessing from other fields.
  const id = payload?.order_id ?? payload?.model?.id;
  return /^\d+$/.test(String(id ?? "")) ? String(id) : null;
}

export default {
  async fetch(request, env) {
    if (request.method !== "POST") return new Response("Method not allowed", {status: 405});
    const auth = request.headers.get("Authorization") ?? "";
    if (!env.WEBHOOK_TOKEN || auth !== "Bearer " + env.WEBHOOK_TOKEN) return new Response("Unauthorized", {status: 401});
    if (!env.KEYCRM_API_KEY) return new Response("Missing server configuration", {status: 503});
    let payload;
    try { payload = await request.json(); } catch { return new Response("Bad JSON", {status: 400}); }
    const id = orderIdFrom(payload);
    if (!id) return new Response("Missing order ID", {status: 400});
    try {
      const [statuses, services, rawOrder] = await Promise.all([
        crmGet(env, "/order/status"),
        crmGet(env, "/order/delivery-service"),
        crmGet(env, "/order/" + id + "?include=products"),
      ]);
      const order = rawOrder?.data ?? rawOrder;
      const match = qualifies(order, resolveId(statuses, CONFIG.status), resolveId(services, CONFIG.delivery));
      // Do not reveal order details or any buyer information.
      return Response.json({order_id: id, eligible: match, mode: "dry-run", shipment_created: false});
    } catch {
      return new Response("Validation failed; no changes made", {status: 422});
    }
  },
};
