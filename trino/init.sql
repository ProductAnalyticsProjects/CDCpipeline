CREATE SCHEMA IF NOT EXISTS delta.default;

CREATE TABLE IF NOT EXISTS delta.default.orders (
    id                  VARCHAR,
    customer_email      VARCHAR,
    status              VARCHAR,
    total_amount        DOUBLE,
    notes               VARCHAR,
    created_at          TIMESTAMP(6),
    updated_at          TIMESTAMP(6),
    version             BIGINT,
    idempotency_key     VARCHAR,
    user_email          VARCHAR,
    role                VARCHAR,
    user_registered_at  TIMESTAMP(6),
    items_count         BIGINT
)
WITH (
    location = 's3a://lakehouse/silver/orders'
);
