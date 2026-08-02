import { AtlasClient, RequestContext, validateContext } from "../shared/runtime.js";

/** Maintained merchant boundary for reading paid-invoice entitlements. */
export async function fetchPaidEntitlements(client: AtlasClient, context: RequestContext) {
  validateContext(context);
  const idempotencyKey = `${context.tenantId}:${context.subjectId}:entitlements`;
  const request = {
    path: "/v1/entitlements/paid" as const,
    method: "POST" as const,
    idempotencyKey,
    body: context,
  };
  return client.request(request);
}
