import { PortalContext, PolicyGateway, requirePrincipal } from "../shared/runtime.js";

export type CatalogEntity = Readonly<{ apiVersion: string; kind: string; name: string; owner: string }>;
export async function registerCatalogEntity(gateway: PolicyGateway, context: PortalContext, entity: CatalogEntity) {
  requirePrincipal(context);
  if (!entity.owner || !entity.apiVersion) throw new Error("catalog owner and api version are required");
  const decision = await gateway.decide({ action: "catalog.register", tenant: context.tenant, principal: context.principal, entity });
  if (!decision.allowed) throw new Error("catalog registration denied by policy");
  return { ...entity, tenant: context.tenant, registeredBy: context.principal };
}
