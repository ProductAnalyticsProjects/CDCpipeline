package com.ecommerce.order.job;

import com.ecommerce.order.domain.OrderStatus;
import com.ecommerce.order.dto.OrderDto;
import com.ecommerce.order.service.OrderService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.OffsetDateTime;
import java.util.List;

@Component
@Slf4j
public class ReservationCleanupJob {
    @Value("${app.inventory.reservation-timeout-minutes}") private long reservationCleanupInterval;
    private final OrderService orderService;
    public ReservationCleanupJob(OrderService orderService) {
        this.orderService = orderService;
    }


    @Scheduled(cron = "0 */5 * * * *")
    public void releasePendingStock() {
        log.info("Running reservation cleanup job");
        List<OrderDto> pendingOrders = orderService.findByStatusAndCreatedAtBefore(OrderStatus.PENDING,
                OffsetDateTime.now().minusMinutes(reservationCleanupInterval));
        log.info("Found {} expired reservations", pendingOrders.size());
        for (OrderDto order: pendingOrders) {
            orderService.cancelOrder(order.id());
            log.info("Cancelled order {}", order.id());
        }
    }
}
