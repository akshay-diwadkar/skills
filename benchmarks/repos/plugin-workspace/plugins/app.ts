import { registerCatalogEntity, CatalogEntity } from "./catalog/entity-registration.js";
import { authorizePluginRoute } from "./permissions/permission-router.js";
import { prepareTemplateRun } from "./scaffolder/template-executor.js";
import { indexCatalogEntity } from "./search/catalog-indexer.js";
import { PolicyGateway, PortalContext } from "./shared/runtime.js";

/** Composition root for one catalog registration and indexing workflow. */
export async function onboardCatalogComponent(
  gateway: PolicyGateway,
  context: PortalContext,
  entity: CatalogEntity,
) {
  const permission = await authorizePluginRoute(gateway, context, "portal.catalog.register");
  if (!permission.allowed) throw new Error("catalog registration permission denied");
  const registered = await registerCatalogEntity(gateway, context, entity);
  const scaffold = prepareTemplateRun(context, "service:catalog", { owner: entity.owner });
  const search = indexCatalogEntity(context.tenant, `${entity.kind}:${entity.name}`, entity.name, { owner: entity.owner });
  return { registered, scaffold, search };
}
