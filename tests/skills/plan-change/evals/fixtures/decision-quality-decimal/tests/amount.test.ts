import { parseAmount } from "../src";

test("parses whole amounts", () => {
  expect(parseAmount("12")).toBe(12);
});
