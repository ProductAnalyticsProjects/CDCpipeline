package com.ecommerce.inventory.dto;


import com.ecommerce.common.dto.ProductInfo;

import java.time.OffsetDateTime;
import java.util.UUID;

public record StockDto(
        UUID id,
        ProductInfo product,
        WarehouseInfo warehouse,
        Integer availableQuantity,
        Integer reservedQuantity,
        OffsetDateTime createdAt,
        OffsetDateTime updatedAt
) {

    public record WarehouseInfo(UUID id, String name) {
    }
}
