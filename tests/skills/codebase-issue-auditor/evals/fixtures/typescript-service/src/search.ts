import { DEFAULT_PAGE_SIZE } from "./config.ts";
import { isValidPageSize } from "./validation.ts";

export function pageSize(requested: number | undefined): number {
  if (requested !== undefined && !isValidPageSize(requested)) {
    throw new Error("invalid page size");
  }
  return requested || DEFAULT_PAGE_SIZE;
}
