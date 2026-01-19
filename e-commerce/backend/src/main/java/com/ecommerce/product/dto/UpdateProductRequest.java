package com.ecommerce.product.dto;

import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Size;

import java.math.BigDecimal;

public record UpdateProductRequest(
    @Size(max = 255, message = "Name must be less than 255 characters")
    String name,

    @Size(max = 2000, message = "Description must be less than 2000 characters")
    String description,

    @DecimalMin(value = "0.0", inclusive = false, message = "Base price must be greater than 0")
    BigDecimal basePrice,

    Boolean isActive
) {}
