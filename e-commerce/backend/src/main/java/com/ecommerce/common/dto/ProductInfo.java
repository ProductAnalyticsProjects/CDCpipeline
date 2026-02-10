package com.ecommerce.common.dto;

import java.util.UUID;

public record ProductInfo(
        UUID id, String name, String sku
) {
}
