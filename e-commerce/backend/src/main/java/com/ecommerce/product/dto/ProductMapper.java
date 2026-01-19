package com.ecommerce.product.dto;

import com.ecommerce.product.domain.Product;
import org.springframework.stereotype.Component;

@Component
public class ProductMapper {

    public ProductDto toDto(Product product) {
        return new ProductDto(
            product.getId(),
            product.getName(),
            product.getDescription(),
            product.getBasePrice(),
            product.getSku(),
            product.getIsActive(),
            product.getCreatedAt(),
            product.getUpdatedAt()
        );
    }

    public Product toEntity(CreateProductRequest request) {
        return Product.builder()
            .name(request.name())
            .description(request.description())
            .basePrice(request.basePrice())
            .sku(request.sku())
            .isActive(true)
            .build();
    }

    public void updateEntity(Product product, UpdateProductRequest request) {
        if (request.name() != null) {
            product.setName(request.name());
        }
        if (request.description() != null) {
            product.setDescription(request.description());
        }
        if (request.basePrice() != null) {
            product.setBasePrice(request.basePrice());
        }
        if (request.isActive() != null) {
            product.setIsActive(request.isActive());
        }
    }
}
