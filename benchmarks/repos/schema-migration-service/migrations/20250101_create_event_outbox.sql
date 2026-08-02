CREATE TABLE event_outbox (id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, payload JSON NOT NULL, published_at TIMESTAMP NULL);
