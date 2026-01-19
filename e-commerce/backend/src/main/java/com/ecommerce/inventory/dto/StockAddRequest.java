package com.ecommerce.inventory.dto;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

import java.util.UUID;

public record StockAddRequest(
        @NotNull(message = "Product ID is required")
        UUID productId,

        @NotNull(message = "Warehouse ID is required")
        UUID warehouseId,

        @NotNull(message = "Quantity is required")
        @Positive(message = "Quantity must be positive")
        Integer quantity
) {
}

