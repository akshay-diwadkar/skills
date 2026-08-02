import test from "node:test";
import assert from "node:assert/strict";
import { registerCatalogEntity } from "../dist/plugins/catalog/entity-registration.js";

test("workspace registration preserves tenant ownership", async () => {
  const gateway = { decide: async () => ({ allowed: true }) };
  const context = { tenant: "tenant-a", principal: "user-a", attributes: {} };
  const entity = { apiVersion: "v1", kind: "Component", name: "checkout", owner: "payments" };
  assert.equal((await registerCatalogEntity(gateway, context, entity)).tenant, "tenant-a");
});
