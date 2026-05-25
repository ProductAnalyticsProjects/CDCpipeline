package com.ecommerce.order.events;

import com.ecommerce.common.outbox.DomainEvent;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

public record OrderCreatedV1(
        UUID eventId,
        UUID orderId,
        UUID customerId,
        BigDecimal totalPrice,
        List<OrderLine> items,
        String notes,
        Instant occurredAt
) implements DomainEvent {
    public record OrderLine(UUID productId, int quantity, BigDecimal unitPrice, BigDecimal subtotal) {}
    @Override public String aggregateType() { return "Order"; }
    @Override public String aggregateId()   { return orderId.toString(); }
    @Override public String eventType()     { return "OrderCreated.v1"; }
    @Override public int schemaVersion()    { return 1; }
}
