export type RequestContext = Readonly<{
  tenantId: string;
  subjectId: string;
  attributes: Record<string, string>;
}>;
export type Request = Readonly<{ path: string; method: "POST"; idempotencyKey: string; body: object }>;
export class AtlasClient {
  constructor(private readonly transport: (request: Request) => Promise<unknown>) {}
  request(request: Request) { return this.transport(request); }
}
export function validateContext(context: RequestContext): void {
  if (!context.tenantId || !context.subjectId) throw new Error("tenant and subject are required");
}
