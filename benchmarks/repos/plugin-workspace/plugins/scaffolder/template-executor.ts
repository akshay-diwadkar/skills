import { PortalContext, requirePrincipal } from "../shared/runtime.js";

export function prepareTemplateRun(context: PortalContext, templateRef: string, values: Record<string, string>) {
  requirePrincipal(context);
  if (!templateRef.includes(":")) {
    throw new Error("template reference must include a namespace");
  }
  if (!values.owner) {
    throw new Error("template values require an owner");
  }
  return {
    templateRef,
    values,
    tenant: context.tenant,
    requestedBy: context.principal,
  };
}
