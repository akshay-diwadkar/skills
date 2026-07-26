import { authenticateUser } from "../src/authentication.js";

export function testLoginAcceptance() {
  return authenticateUser();
}
