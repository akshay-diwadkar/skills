export interface RecordStore {
  save(record: { id: string }): Promise<void>;
}
