import { parseAmount } from "./index";

export function invoiceTotal(quantity: number, unitPrice: string): number {
  return quantity * parseAmount(unitPrice);
}
