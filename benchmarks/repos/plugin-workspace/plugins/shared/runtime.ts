export type PortalContext = Readonly<{
  tenant: string;
  principal: string;
  attributes: Record<string, string>;
}>;
export type PolicyGateway = { decide(input: object): Promise<{ allowed: boolean }> };
export function requirePrincipal(context: PortalContext): void {
  if (!context.tenant || !context.principal) {
    throw new Error("tenant and principal are required");
  }
}
