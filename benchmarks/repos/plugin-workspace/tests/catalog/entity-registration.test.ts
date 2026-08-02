import test from "node:test";
import assert from "node:assert/strict";
import { registerCatalogEntity } from "../../plugins/catalog/entity-registration.js";

test("registration preserves tenant ownership", async () => {
  const entity = await registerCatalogEntity({ decide: async () => ({ allowed: true }) }, { tenant: "tenant-a", principal: "user-a", attributes: {} }, { apiVersion: "v1", kind: "Component", name: "checkout", owner: "payments" });
  assert.equal(entity.tenant, "tenant-a");
});
