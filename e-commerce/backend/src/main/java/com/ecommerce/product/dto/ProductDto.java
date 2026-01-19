package com.ecommerce.product.dto;


import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.UUID;

public record ProductDto(
    UUID id,
    String name,
    String description,
    BigDecimal basePrice,
    String sku,
    Boolean isActive,
    OffsetDateTime createdAt,
    OffsetDateTime updatedAt
) {}
