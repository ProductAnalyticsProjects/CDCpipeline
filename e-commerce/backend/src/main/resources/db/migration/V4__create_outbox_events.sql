CREATE TABLE outbox_events (
    id              UUID        PRIMARY KEY,
    aggregatetype   TEXT        NOT NULL,
    aggregateid     TEXT        NOT NULL,
    type            TEXT        NOT NULL,
    payload         JSONB       NOT NULL,
    schema_version  INT         NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_outbox_aggregate
    ON outbox_events (aggregatetype, aggregateid, created_at);
