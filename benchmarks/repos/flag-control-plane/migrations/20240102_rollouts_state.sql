CREATE TABLE rollouts_state (
    key TEXT PRIMARY KEY,
    revision INTEGER NOT NULL,
    payload TEXT NOT NULL
);
