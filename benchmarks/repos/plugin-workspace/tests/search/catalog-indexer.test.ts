import test from "node:test";
import assert from "node:assert/strict";
import { indexCatalogEntity } from "../../plugins/search/catalog-indexer.js";

test("catalog search partitions documents by tenant", () => {
  assert.equal(indexCatalogEntity("tenant-a", "component:checkout", "Checkout", { owner: "payments" }).tenant, "tenant-a");
});
