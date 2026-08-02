import test from "node:test";
import assert from "node:assert/strict";
import { AtlasClient } from "../dist/sdk/shared/runtime.js";
import { fetchPaidEntitlements } from "../dist/sdk/merchant/entitlement_client.js";

test("merchant entitlement requests carry a tenant-qualified idempotency key", async () => {
  const requests = [];
  const client = new AtlasClient(async request => { requests.push(request); return { ok: true }; });
  await fetchPaidEntitlements(client, { tenantId: "tenant-a", subjectId: "account-a", attributes: {} });
  assert.equal(requests[0].idempotencyKey, "tenant-a:account-a:entitlements");
});
