import test from "node:test";
import assert from "node:assert/strict";
import { fetchPaidEntitlements } from "../../sdk/merchant/entitlement_client.js";
import { AtlasClient } from "../../sdk/shared/runtime.js";

test("merchant entitlement reads carry a tenant-qualified idempotency key", async () => {
  const requests: Array<{ idempotencyKey: string }> = [];
  const client = new AtlasClient(async request => { requests.push(request); return { ok: true }; });
  await fetchPaidEntitlements(client, { tenantId: "tenant-a", subjectId: "account-a", attributes: {} });
  assert.equal(requests[0].idempotencyKey, "tenant-a:account-a:entitlements");
});
