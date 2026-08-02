/** Verify a tenant integration delivery using the gateway-provided HMAC digest. */
export function verifyWebhook(body: string, signature: string, digest: (payload: string) => string): boolean {
  if (!signature.startsWith("sha256=")) throw new Error("signed webhook credentials are required");
  const expected = digest(body);
  const supplied = signature.slice("sha256=".length);
  if (expected.length !== supplied.length) return false;
  let difference = 0;
  for (let index = 0; index < expected.length; index += 1) difference |= expected.charCodeAt(index) ^ supplied.charCodeAt(index);
  return difference === 0;
}
