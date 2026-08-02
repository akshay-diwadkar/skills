"""Northstar developer-portal fixture emitter (TypeScript workspace plus Gradle Java)."""

from __future__ import annotations

from pathlib import Path

from .common import asset_bytes, asset_text, generated_provenance, json_text, require_empty_output, write, write_bytes

def _write_reference_flows(output: Path) -> None:
    write(output, "plugins/catalog/entity-registration.ts", '''import { PortalContext, PolicyGateway, requirePrincipal } from "../shared/runtime.js";

export type CatalogEntity = Readonly<{ apiVersion: string; kind: string; name: string; owner: string }>;
export async function registerCatalogEntity(gateway: PolicyGateway, context: PortalContext, entity: CatalogEntity) {
  requirePrincipal(context);
  if (!entity.owner || !entity.apiVersion) throw new Error("catalog owner and api version are required");
  const decision = await gateway.decide({ action: "catalog.register", tenant: context.tenant, principal: context.principal, entity });
  if (!decision.allowed) throw new Error("catalog registration denied by policy");
  return { ...entity, tenant: context.tenant, registeredBy: context.principal };
}
''')
    write(output, "plugins/permissions/permission-router.ts", '''import { PortalContext, PolicyGateway, requirePrincipal } from "../shared/runtime.js";

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
''')
    write(output, "plugins/scaffolder/template-executor.ts", '''import { PortalContext, requirePrincipal } from "../shared/runtime.js";

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
''')
    write(output, "plugins/search/catalog-indexer.ts", '''export type SearchDocument = Readonly<{ tenant: string; entityRef: string; title: string; text: string }>;

export function indexCatalogEntity(tenant: string, entityRef: string, title: string, annotations: Record<string, string>): SearchDocument {
  if (!tenant || !entityRef) {
    throw new Error("tenant and entity reference are required");
  }
  const text = Object.entries(annotations)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, value]) => `${key}:${value}`)
    .join(" ");
  return { tenant, entityRef, title, text };
}
''')
    write(output, "plugins/integrations/webhook-verifier.ts", '''/** Verify a tenant integration delivery using the gateway-provided HMAC digest. */
export function verifyWebhook(body: string, signature: string, digest: (payload: string) => string): boolean {
  if (!signature.startsWith("sha256=")) throw new Error("signed webhook credentials are required");
  const expected = digest(body);
  const supplied = signature.slice("sha256=".length);
  if (expected.length !== supplied.length) return false;
  let difference = 0;
  for (let index = 0; index < expected.length; index += 1) difference |= expected.charCodeAt(index) ^ supplied.charCodeAt(index);
  return difference === 0;
}
''')
    write(output, "policy-service/src/main/java/portal/policy/CatalogRegistrationPolicy.java", '''package portal.policy;

import java.util.Map;
import portal.shared.PolicyDecision;
import portal.shared.PolicyRequest;

public final class CatalogRegistrationPolicy {
  public PolicyDecision evaluate(PolicyRequest request) {
    if (!request.attributes().containsKey("catalogOwner")) return PolicyDecision.denied("catalog owner claim is required");
    boolean allowed = !"production".equals(request.attributes().get("environment")) || "admin".equals(request.attributes().get("role"));
    return new PolicyDecision(allowed, allowed ? "catalog registration accepted" : "production registration requires admin", Map.of("policy", "catalog-registration"));
  }
}
''')
    write(output, "plugins/app.ts", '''import { registerCatalogEntity, CatalogEntity } from "./catalog/entity-registration.js";
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
''')
    write(output, "config/catalog/registration.yaml", "required_fields: [apiVersion, kind, name, owner]\nproduction_role: admin\n")
    write(output, "config/permissions/routes.yaml", "namespace: portal.\ndefault: deny\ncache_seconds: 30\n")
    write(output, "config/scaffolder/execution.yaml", "require_namespaced_template: true\nrequire_owner: true\n")
    write(output, "config/search/indexing.yaml", "partition_key: tenant\nannotation_order: lexical\n")
    write(output, "config/integrations/webhooks.yaml", "signature: hmac-sha256\nreject_unsigned: true\n")
    write(output, "tests/catalog/entity-registration.test.ts", '''import test from "node:test";
import assert from "node:assert/strict";
import { registerCatalogEntity } from "../../plugins/catalog/entity-registration.js";

test("registration preserves tenant ownership", async () => {
  const entity = await registerCatalogEntity({ decide: async () => ({ allowed: true }) }, { tenant: "tenant-a", principal: "user-a", attributes: {} }, { apiVersion: "v1", kind: "Component", name: "checkout", owner: "payments" });
  assert.equal(entity.tenant, "tenant-a");
});
''')
    write(output, "tests/permissions/permission-router.test.ts", '''import test from "node:test";
import assert from "node:assert/strict";
import { authorizePluginRoute } from "../../plugins/permissions/permission-router.js";

test("permission routes require the portal namespace", async () => {
  await assert.rejects(() => authorizePluginRoute({ decide: async () => ({ allowed: true }) }, { tenant: "tenant-a", principal: "user-a", attributes: {} }, "catalog.write"), /portal namespace/);
});
''')
    write(output, "tests/scaffolder/template-executor.test.ts", '''import test from "node:test";
import assert from "node:assert/strict";
import { prepareTemplateRun } from "../../plugins/scaffolder/template-executor.js";

test("template runs bind the requesting tenant", () => {
  const run = prepareTemplateRun({ tenant: "tenant-a", principal: "user-a", attributes: {} }, "service:node", { owner: "platform" });
  assert.equal(run.tenant, "tenant-a");
});
''')
    write(output, "tests/search/catalog-indexer.test.ts", '''import test from "node:test";
import assert from "node:assert/strict";
import { indexCatalogEntity } from "../../plugins/search/catalog-indexer.js";

test("catalog search partitions documents by tenant", () => {
  assert.equal(indexCatalogEntity("tenant-a", "component:checkout", "Checkout", { owner: "payments" }).tenant, "tenant-a");
});
''')
    write(output, "tests/app/onboard-component.test.ts", '''import test from "node:test";
import assert from "node:assert/strict";
import { onboardCatalogComponent } from "../../plugins/app.js";

test("component onboarding composes every maintained plugin boundary", async () => {
  const gateway = { decide: async () => ({ allowed: true }) };
  const context = { tenant: "tenant-a", principal: "user-a", attributes: {} };
  const entity = { apiVersion: "v1", kind: "Component", name: "checkout", owner: "payments" };
  assert.equal((await onboardCatalogComponent(gateway, context, entity)).search.tenant, "tenant-a");
});
''')
    write(output, "tests/shared/runtime.test.ts", '''import test from "node:test";
import assert from "node:assert/strict";
import { requirePrincipal } from "../../plugins/shared/runtime.js";

test("shared principal validation rejects an absent tenant", () => {
  assert.throws(() => requirePrincipal({ tenant: "", principal: "user-a", attributes: {} }), /tenant and principal/);
});
''')
    write(output, "policy-service/src/test/java/portal/policy/CatalogRegistrationPolicyTest.java", '''package portal.policy;
import static org.junit.jupiter.api.Assertions.assertFalse;
import java.util.Map;
import org.junit.jupiter.api.Test;
import portal.shared.PolicyRequest;

final class CatalogRegistrationPolicyTest {
  @Test void productionRegistrationRequiresAnAdministrator() {
    var request = new PolicyRequest("tenant-a", "user-a", Map.of("catalogOwner", "payments", "environment", "production", "role", "reader"));
    assertFalse(new CatalogRegistrationPolicy().evaluate(request).allowed());
  }
}
''')
    write(output, "workspace-tests/catalog-registration.test.mjs", '''import test from "node:test";
import assert from "node:assert/strict";
import { registerCatalogEntity } from "../dist/plugins/catalog/entity-registration.js";

test("workspace registration preserves tenant ownership", async () => {
  const gateway = { decide: async () => ({ allowed: true }) };
  const context = { tenant: "tenant-a", principal: "user-a", attributes: {} };
  const entity = { apiVersion: "v1", kind: "Component", name: "checkout", owner: "payments" };
  assert.equal((await registerCatalogEntity(gateway, context, entity)).tenant, "tenant-a");
});
''')
    write(output, "workspace-tests/onboard-component.test.mjs", '''import test from "node:test";
import assert from "node:assert/strict";
import { onboardCatalogComponent } from "../dist/plugins/app.js";

test("the portal composition root authorizes, registers, scaffolds, and indexes", async () => {
  const gateway = { decide: async () => ({ allowed: true }) };
  const context = { tenant: "tenant-a", principal: "user-a", attributes: {} };
  const entity = { apiVersion: "v1", kind: "Component", name: "checkout", owner: "payments" };
  const result = await onboardCatalogComponent(gateway, context, entity);
  assert.equal(result.registered.tenant, "tenant-a");
  assert.equal(result.scaffold.values.owner, "payments");
  assert.equal(result.search.entityRef, "Component:checkout");
});
''')
    write(output, "workspace-tests/webhook-verifier.test.mjs", '''import test from "node:test";
import assert from "node:assert/strict";
import { verifyWebhook } from "../dist/plugins/integrations/webhook-verifier.js";

test("integration webhooks require the exact HMAC payload signature", () => {
  const digest = payload => payload === "payload" ? "abc123" : "def456";
  assert.equal(verifyWebhook("payload", "sha256=abc123", digest), true);
  assert.equal(verifyWebhook("changed", "sha256=abc123", digest), false);
});
''')


def emit(output: Path) -> None:
    require_empty_output(output)
    write(output, ".gitignore", "node_modules/\n.gradle/\nbuild/\n")
    write(output, "README.md", "# Northstar Developer Portal\n\nPlugin workspace and policy-service benchmark fixture.\n")
    write(output, "docs/operations.md", "# Operations\n\nPlugin registrations are evaluated against the tenant policy service.\n")
    write(output, "package.json", json_text({"name": "northstar-portal", "private": True, "type": "module", "workspaces": ["plugins/*"], "scripts": {"build": "tsc -p tsconfig.json", "test": "node --test workspace-tests/*.test.mjs"}, "devDependencies": {"typescript": "5.7.2"}}))
    write(output, "package-lock.json", asset_text("portal-package-lock.json"))
    write(output, "tsconfig.json", json_text({"compilerOptions": {"target": "ES2022", "module": "NodeNext", "moduleResolution": "NodeNext", "strict": True, "outDir": "dist"}, "include": ["plugins/**/*.ts", "generated/**/*.ts"]}))
    write(output, "settings.gradle", "rootProject.name = 'northstar-policy'\ninclude 'policy-service'\n")
    write(output, "build.gradle", "allprojects {\n  repositories { mavenCentral() }\n  dependencyLocking { lockAllConfigurations() }\n}\n")
    write(output, "policy-service/build.gradle", "plugins { id 'java' }\njava { toolchain { languageVersion = JavaLanguageVersion.of(17) } }\ndependencies { testImplementation 'org.junit.jupiter:junit-jupiter:5.11.4' }\ntest { useJUnitPlatform() }\n")
    write(output, "gradle/wrapper/gradle-wrapper.properties", asset_text("gradle-wrapper.properties"))
    write_bytes(output, "gradle/wrapper/gradle-wrapper.jar", asset_bytes("gradle-wrapper.jar"))
    write(output, "gradlew", asset_text("portal-gradlew"))
    write(output, "gradlew.bat", asset_text("portal-gradlew.bat"))
    write(output, "gradle/verification-metadata.xml", asset_text("gradle-verification-metadata.xml"))
    write(output, "policy-service/gradle.lockfile", asset_text("policy-service-gradle.lockfile"))
    write(output, "plugins/shared/runtime.ts", '''export type PortalContext = Readonly<{
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
''')
    write(output, "policy-service/src/main/java/portal/shared/PolicyRequest.java", '''package portal.shared;
import java.util.Map;

public record PolicyRequest(
    String tenant,
    String principal,
    Map<String,String> attributes
) {}
''')
    write(output, "policy-service/src/main/java/portal/shared/PolicyDecision.java", '''package portal.shared;
import java.util.Map;

public record PolicyDecision(boolean allowed, String reason, Map<String,String> audit) {
  public static PolicyDecision denied(String reason) {
    return new PolicyDecision(false, reason, Map.of());
  }
}
''')
    write(output, "schemas/change-event.json", json_text({"type": "object", "required": ["tenant", "principal"], "properties": {"tenant": {"type": "string"}, "principal": {"type": "string"}}}))
    write(output, "generated/portal-client.ts", generated_provenance(source="schemas/change-event.json", input_value="portal-event-v1") + "export interface PortalEvent { tenant: string; principal: string }\n")
    _write_reference_flows(output)
