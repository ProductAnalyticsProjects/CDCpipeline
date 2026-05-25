package com.ecommerce.common.outbox;

import java.util.UUID;

public interface DomainEvent {
    UUID eventId();           // id univoco evento (finirà sia in OutboxEvent.id sia nel payload)
    String aggregateType();
    String aggregateId();
    String eventType();       // es. "OrderCreated.v1"
    int schemaVersion();
}
