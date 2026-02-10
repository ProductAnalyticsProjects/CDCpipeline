package com.ecommerce.order.controller;


import com.ecommerce.order.dto.CreateOrderRequest;
import com.ecommerce.order.dto.OrderDto;
import com.ecommerce.order.service.OrderService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.UUID;

@RestController
@RequestMapping("/v1/orders")
@RequiredArgsConstructor
@SuppressWarnings("NullableProblems")
@Slf4j
public class OrderController {
    private final OrderService orderService;

    @PostMapping
    public ResponseEntity<OrderDto> createOrder(@Valid @RequestBody CreateOrderRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(orderService.createOrder(request));
    }

    @GetMapping("/{id}")
    public ResponseEntity<OrderDto> getOrder(@PathVariable UUID id) {
        return ResponseEntity.ok(orderService.getOrderById(id));
    }

    @PostMapping("/{id}/pay")
    public ResponseEntity<OrderDto> payOrder(@PathVariable UUID id) {
        orderService.payOrder(id);
        return ResponseEntity.ok(orderService.getOrderById(id));
    }

    @PostMapping("/{id}/process")
    public ResponseEntity<OrderDto> processOrder(@PathVariable UUID id) {
        orderService.processOrder(id);
        return ResponseEntity.ok(orderService.getOrderById(id));
    }

    @PostMapping("/{id}/cancel")
    public ResponseEntity<OrderDto> cancelOrder(@PathVariable UUID id) {
        orderService.cancelOrder(id);
        return ResponseEntity.ok(orderService.getOrderById(id));
    }

    @PostMapping("/{id}/ship")
    public ResponseEntity<OrderDto> shipOrder(@PathVariable UUID id) {
        orderService.shipOrder(id);
        return ResponseEntity.ok(orderService.getOrderById(id));
    }

    @PostMapping("/{id}/deliver")
    public ResponseEntity<OrderDto> deliverOrder(@PathVariable UUID id) {
        orderService.deliverOrder(id);
        return ResponseEntity.ok(orderService.getOrderById(id));
    }


}
