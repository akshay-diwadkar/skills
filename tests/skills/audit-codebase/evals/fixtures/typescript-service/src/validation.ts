export function isValidPageSize(value: number): boolean {
  return Number.isInteger(value) && value >= 0 && value <= 100;
}
