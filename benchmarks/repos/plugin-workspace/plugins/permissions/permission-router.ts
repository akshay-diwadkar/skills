import { PortalContext, PolicyGateway, requirePrincipal } from "../shared/runtime.js";

export async function authorizePluginRoute(gateway: PolicyGateway, context: PortalContext, permission: string) {
  requirePrincipal(context);
  if (!permission.startsWith("portal.")) {
    throw new Error("permission must use the portal namespace");
  }
  const request = {
    action: permission,
    tenant: context.tenant,
    principal: context.principal,
    attributes: context.attributes,
  };
  return gateway.decide(request);
}
