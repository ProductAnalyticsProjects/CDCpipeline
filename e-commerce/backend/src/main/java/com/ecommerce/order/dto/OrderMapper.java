package com.ecommerce.order.dto;

import com.ecommerce.common.dto.ProductInfo;
import com.ecommerce.order.domain.Order;
import com.ecommerce.order.domain.OrderItem;
import org.springframework.stereotype.Component;

@Component
public class OrderMapper {

    public OrderDto toOrderDto(Order order) {
        return new OrderDto(
                order.getId(),
                order.getStatus(),
                order.getTotalAmount(),
                order.getItems().stream().map(this::orderItemDto).toList(),
                order.getNotes()
        );
    }

    public OrderItemDto orderItemDto(OrderItem item) {
        return new OrderItemDto(
                item.getId(),
                new ProductInfo(
                        item.getProduct().getId(),
                        item.getProduct().getName(),
                        item.getProduct().getSku()
                ),
                item.getQuantity(),
                item.getUnitPrice(),
                item.getSubtotal()

        );
    }
}
