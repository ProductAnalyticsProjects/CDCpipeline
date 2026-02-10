package com.ecommerce.order.service;


import com.ecommerce.common.exception.BusinessException;
import com.ecommerce.common.exception.ResourceNotFoundException;
import com.ecommerce.inventory.service.StockService;
import com.ecommerce.order.domain.Order;
import com.ecommerce.order.domain.OrderItem;
import com.ecommerce.order.domain.OrderStatus;
import com.ecommerce.order.dto.CreateOrderRequest;
import com.ecommerce.order.dto.OrderDto;
import com.ecommerce.order.dto.OrderItemRequest;
import com.ecommerce.order.dto.OrderMapper;
import com.ecommerce.order.repository.OrderRepository;
import com.ecommerce.product.domain.Product;
import com.ecommerce.product.repository.ProductRepository;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class OrderService {
    private final static UUID defaultWarehouseId = UUID.fromString("00000000-0000-0000-0000-000000000001");
    private final OrderRepository orderRepository;
    private final OrderMapper orderMapper;
    private final ProductRepository productRepository;
    private final StockService stockService;


    @Transactional(readOnly = true)
    public Page<OrderDto> findAll(Pageable pageable) {
        return orderRepository.findAll(pageable).map(orderMapper::toOrderDto);
    }

    @Transactional(readOnly = true)
    public Page<OrderDto> findByCustomerMail(String customerEmail, Pageable pageable) {
        return orderRepository.findByCustomerEmail(customerEmail, pageable).map(orderMapper::toOrderDto);
    }

    @Transactional(readOnly = true)
    public Page<OrderDto> findByStatus(OrderStatus status, Pageable pageable) {
        return orderRepository.findByStatus(status, pageable).map(orderMapper::toOrderDto);
    }

    @Transactional(readOnly = true)
    public Page<OrderDto> findByCustomerEmailAndStatus(String customerEmail, OrderStatus status, Pageable pageable) {
        return orderRepository.findByCustomerEmailAndStatus(customerEmail, status, pageable).map(orderMapper::toOrderDto);
    }

    @Transactional
    public OrderDto createOrder(CreateOrderRequest request) {
        Order order = new Order();
        order.setCustomerEmail(request.customerEmail());
        order.setNotes(request.notes());
        for (OrderItemRequest i : request.items()) {
            Product product = productRepository.findByIdAndIsActiveTrue(i.productId()).orElseThrow(() ->
                    new ResourceNotFoundException("product", i.productId()));
            if (!stockService.checkAvailability(i.productId(), i.quantity())) {
                throw new BusinessException("INSUFFICIENT_STOCK",
                        "Not enough stock for product: " + i.productId());
            }
            stockService.reserve(i.productId(), defaultWarehouseId, i.quantity());
            OrderItem item = new OrderItem();
            item.setProduct(product);
            item.setQuantity(i.quantity());
            item.setUnitPrice(product.getBasePrice());
            item.calculateSubtotal();
            order.addItem(item);


        }
        order.recalculateTotal();
        orderRepository.save(order);
        return orderMapper.toOrderDto(order);

    }

    @Transactional
    public void payOrder(UUID orderId) {
        var orderEntity = orderRepository.findById(orderId).orElseThrow(() -> new ResourceNotFoundException("Order",
                orderId));
        if (orderEntity.canTransitionTo(OrderStatus.PAID)) {
            orderEntity.setStatus(OrderStatus.PAID);
        } else {
            throw new BusinessException("Order cannot be paid");
        }
        orderRepository.save(orderEntity);
    }

    @Transactional
    public void cancelOrder(UUID orderId) {
        var orderEntity = orderRepository.findById(orderId).orElseThrow(() -> new ResourceNotFoundException("Order", orderId));
        if (orderEntity.canBeCancelled()) {
            orderEntity.setStatus(OrderStatus.CANCELLED);
            for (OrderItem item : orderEntity.getItems()) {
                stockService.release(item.getProduct().getId(), defaultWarehouseId, item.getQuantity());
            }
        } else {
            throw new BusinessException("Order cannot be cancelled");
        }
        orderRepository.save(orderEntity);
    }

    public OrderDto getOrderById(UUID id) {
        return orderMapper.toOrderDto(orderRepository.findById(id).orElseThrow(() -> new ResourceNotFoundException("Order", id)));
    }

    @Transactional
    public void shipOrder(UUID orderId) {
        var orderEntity = orderRepository.findById(orderId).orElseThrow(() -> new ResourceNotFoundException("Order", orderId));
        if (orderEntity.canTransitionTo(OrderStatus.SHIPPED)) {
            orderEntity.setStatus(OrderStatus.SHIPPED);
            for (OrderItem item : orderEntity.getItems()) {
                stockService.confirm(item.getProduct().getId(), defaultWarehouseId, item.getQuantity());
            }
        } else {
            throw new BusinessException("Order cannot be shipped");
        }
        orderRepository.save(orderEntity);
    }

    @Transactional
    public void processOrder(UUID orderId) {
        var orderEntity = orderRepository.findById(orderId).orElseThrow(() -> new ResourceNotFoundException("Order",
                orderId));

        if (orderEntity.canTransitionTo(OrderStatus.PROCESSING)) {
            orderEntity.setStatus(OrderStatus.PROCESSING);
        } else {
            throw new BusinessException("Order cannot be processed");
        }
        orderRepository.save(orderEntity);
    }

    @Transactional
    public void deliverOrder(UUID orderId) {
        var orderEntity = orderRepository.findById(orderId).orElseThrow(() -> new ResourceNotFoundException("Order", orderId));
        if (orderEntity.canTransitionTo(OrderStatus.DELIVERED)) {
            orderEntity.setStatus(OrderStatus.DELIVERED);
        } else {
            throw new BusinessException("Order cannot be delivered");
        }
        orderRepository.save(orderEntity);
    }
}
