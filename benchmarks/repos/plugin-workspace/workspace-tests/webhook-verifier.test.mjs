import test from "node:test";
import assert from "node:assert/strict";
import { verifyWebhook } from "../dist/plugins/integrations/webhook-verifier.js";

test("integration webhooks require the exact HMAC payload signature", () => {
  const digest = payload => payload === "payload" ? "abc123" : "def456";
  assert.equal(verifyWebhook("payload", "sha256=abc123", digest), true);
  assert.equal(verifyWebhook("changed", "sha256=abc123", digest), false);
});
