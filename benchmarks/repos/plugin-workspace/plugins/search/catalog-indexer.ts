export type SearchDocument = Readonly<{ tenant: string; entityRef: string; title: string; text: string }>;

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
