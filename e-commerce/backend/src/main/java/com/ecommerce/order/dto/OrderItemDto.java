package com.ecommerce.order.dto;

import com.ecommerce.common.dto.ProductInfo;

import java.math.BigDecimal;
import java.util.UUID;

public record OrderItemDto(
        UUID id,
        ProductInfo product,
        Integer quantity,
        BigDecimal unitPrice,
        BigDecimal subtotal
) {
}
