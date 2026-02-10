package com.ecommerce.inventory.dto;

import com.ecommerce.common.dto.ProductInfo;
import com.ecommerce.inventory.domain.Stock;
import org.springframework.stereotype.Component;

@Component
public class StockMapper {

    public StockDto toDto(Stock stock) {
        return new StockDto(
                stock.getId(),
                new ProductInfo(
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
