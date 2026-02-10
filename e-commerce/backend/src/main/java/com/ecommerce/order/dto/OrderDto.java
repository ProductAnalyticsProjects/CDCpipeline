package com.ecommerce.order.dto;

import com.ecommerce.order.domain.OrderStatus;

import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;

public record OrderDto(
        UUID id,
        OrderStatus status,
        BigDecimal totalPrice,
        List<OrderItemDto> items,
        String notes
) {
}
