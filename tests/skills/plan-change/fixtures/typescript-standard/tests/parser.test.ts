import { parseValue } from "../src";

test("parses a value", () => {
  expect(parseValue(" value ")).toBe("value");
});
