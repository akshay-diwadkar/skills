CREATE TABLE jobs_state (
    key TEXT PRIMARY KEY,
    revision INTEGER NOT NULL,
    payload TEXT NOT NULL
);
