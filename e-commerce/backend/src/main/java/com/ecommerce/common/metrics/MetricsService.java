package com.ecommerce.common.metrics;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import org.springframework.stereotype.Service;

@Service
public class MetricsService {

    private final Counter ordersCreatedCounter;
    private final Counter ordersCancelledCounter;
    private final Counter stockReservationsCounter;

    public MetricsService(MeterRegistry registry) {
        this.ordersCreatedCounter = Counter.builder("orders_created_total")
                .description("Total orders created")
                .register(registry);

        this.ordersCancelledCounter = Counter.builder("orders_cancelled_total")
                .description("Total orders cancelled")
                .register(registry);

        this.stockReservationsCounter = Counter.builder("stock_reservations_total")
                .description("Total stock reservations")
                .register(registry);
    }

    public void incrementOrdersCreated() {
        ordersCreatedCounter.increment();
    }

    public void incrementOrdersCancelled() {
        ordersCancelledCounter.increment();
    }

    public void incrementStockReservations() {
        stockReservationsCounter.increment();
    }
}