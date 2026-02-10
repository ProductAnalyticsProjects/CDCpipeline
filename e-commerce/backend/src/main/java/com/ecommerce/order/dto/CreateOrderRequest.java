package com.ecommerce.order.dto;

import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;

import java.util.List;

public record CreateOrderRequest(
        @NotNull(message = "Customer email is required")
        String customerEmail,

        @NotEmpty(message = "Order must have at least one item")
        List<OrderItemRequest> items,


        String notes


) {
}
