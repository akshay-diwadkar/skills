import test from "node:test";
import assert from "node:assert/strict";
import { requirePrincipal } from "../../plugins/shared/runtime.js";

test("shared principal validation rejects an absent tenant", () => {
  assert.throws(() => requirePrincipal({ tenant: "", principal: "user-a", attributes: {} }), /tenant and principal/);
});
