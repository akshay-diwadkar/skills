import test from "node:test";
import assert from "node:assert/strict";
import { onboardCatalogComponent } from "../dist/plugins/app.js";

test("the portal composition root authorizes, registers, scaffolds, and indexes", async () => {
  const gateway = { decide: async () => ({ allowed: true }) };
  const context = { tenant: "tenant-a", principal: "user-a", attributes: {} };
  const entity = { apiVersion: "v1", kind: "Component", name: "checkout", owner: "payments" };
  const result = await onboardCatalogComponent(gateway, context, entity);
  assert.equal(result.registered.tenant, "tenant-a");
  assert.equal(result.scaffold.values.owner, "payments");
  assert.equal(result.search.entityRef, "Component:checkout");
});
