import assert from "node:assert/strict";
import test from "node:test";

import { pageSize } from "../src/search.ts";

test("uses the default page size", () => {
  assert.equal(pageSize(undefined), 25);
});

test("accepts a positive page size", () => {
  assert.equal(pageSize(10), 10);
});
