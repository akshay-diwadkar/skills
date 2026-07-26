import { encodePayload } from "../web/encoding.js";

export function testSerialization() {
  return encodePayload({ ok: true }) === '{"ok":true}';
}
