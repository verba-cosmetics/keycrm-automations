import assert from "node:assert/strict";
import test from "node:test";
import {qualifies} from "../src/direct_np_worker.js";

function order(products = [{sku:"BHCCD",quantity:1}]) {
  return {status_id:2, products, shipping:{delivery_service_id:4, tracking_code:""}};
}
test("one cream matches", ()=>assert.equal(qualifies(order(),2,4),true));
test("multiple items rejected", ()=>assert.equal(qualifies(order([{sku:"BHCCD",quantity:1},{sku:"X",quantity:1}]),2,4),false));
test("quantity rejected", ()=>assert.equal(qualifies(order([{sku:"BHCCD",quantity:2}]),2,4),false));
test("other status and service rejected", ()=>{
  assert.equal(qualifies(order(),3,4),false);
  assert.equal(qualifies(order(),2,5),false);
});
test("missing tracking fields and existing tracking rejected", ()=>{
  const missing=order();delete missing.shipping.tracking_code;
  assert.equal(qualifies(missing,2,4),false);
  const tracked=order();tracked.shipping.tracking_code="2045";
  assert.equal(qualifies(tracked,2,4),false);
});
