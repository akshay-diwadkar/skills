import type { RecordStore } from "./store.ts";

export async function createRecord(store: RecordStore, id: string): Promise<{ id: string }> {
  const record = { id };
  store.save(record);
  return record;
}
