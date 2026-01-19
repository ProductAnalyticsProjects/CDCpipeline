package com.ecommerce.inventory.dto;

import com.ecommerce.inventory.domain.Stock;
import com.ecommerce.product.dto.ProductDto;
import com.ecommerce.product.dto.ProductMapper;
import org.springframework.stereotype.Component;

@Component
public class StockMapper {

    public StockDto toDto(Stock stock) {
        return new StockDto(
                stock.getId(),
                new StockDto.ProductInfo(
                        stock.getProduct().getId(),
                        stock.getProduct().getName(),
                        stock.getProduct().getSku()
                ),
                new StockDto.WarehouseInfo(
                        stock.getWarehouse().getId(),
                        stock.getWarehouse().getName()
                ),
                stock.getAvailableQuantity(),
                stock.getReservedQuantity(),
                stock.getCreatedAt(),
                stock.getUpdatedAt()
        );
    }

}
