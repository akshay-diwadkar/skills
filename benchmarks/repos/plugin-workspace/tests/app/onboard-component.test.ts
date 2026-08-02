import test from "node:test";
import assert from "node:assert/strict";
import { onboardCatalogComponent } from "../../plugins/app.js";

test("component onboarding composes every maintained plugin boundary", async () => {
  const gateway = { decide: async () => ({ allowed: true }) };
  const context = { tenant: "tenant-a", principal: "user-a", attributes: {} };
  const entity = { apiVersion: "v1", kind: "Component", name: "checkout", owner: "payments" };
  assert.equal((await onboardCatalogComponent(gateway, context, entity)).search.tenant, "tenant-a");
});
