import { BackoffPolicy } from "../src/backoff.js";

export function testRetrySchedule() {
  return new BackoffPolicy().scheduleRetry() === 1;
}
