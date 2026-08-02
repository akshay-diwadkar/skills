import test from "node:test";
import assert from "node:assert/strict";
import { authorizePluginRoute } from "../../plugins/permissions/permission-router.js";

test("permission routes require the portal namespace", async () => {
  await assert.rejects(() => authorizePluginRoute({ decide: async () => ({ allowed: true }) }, { tenant: "tenant-a", principal: "user-a", attributes: {} }, "catalog.write"), /portal namespace/);
});
