import test from "node:test";
import assert from "node:assert/strict";
import { prepareTemplateRun } from "../../plugins/scaffolder/template-executor.js";

test("template runs bind the requesting tenant", () => {
  const run = prepareTemplateRun({ tenant: "tenant-a", principal: "user-a", attributes: {} }, "service:node", { owner: "platform" });
  assert.equal(run.tenant, "tenant-a");
});
