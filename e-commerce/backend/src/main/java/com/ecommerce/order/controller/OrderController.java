package com.ecommerce.order.controller;


import com.ecommerce.order.domain.OrderStatus;
import com.ecommerce.order.dto.CreateOrderRequest;
import com.ecommerce.order.dto.OrderDto;
import com.ecommerce.order.service.OrderService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.UUID;

@RestController
@RequestMapping("/v1/orders")
@RequiredArgsConstructor
@SuppressWarnings("NullableProblems")
@Slf4j
public class OrderController {
    private final OrderService orderService;

    @GetMapping
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Page<OrderDto>>getAllOrders(
            @PageableDefault(size = 20, sort = "createdAt", direction = Sort.Direction.DESC) Pageable pageable,
            @RequestParam(required = false) String customerEmail,
            @RequestParam(required = false) OrderStatus status
    ) {
        if (customerEmail != null && status != null) {
            return ResponseEntity.ok(orderService.findByCustomerEmailAndStatus(customerEmail, status, pageable));
        } else if (customerEmail != null) {
            return ResponseEntity.ok(orderService.findByCustomerMail(customerEmail, pageable));
        } else if (status != null) {
            return ResponseEntity.ok(orderService.findByStatus(status, pageable));
        } else {
            return ResponseEntity.ok(orderService.findAll(pageable));
        }
    }

    @GetMapping("/my")
    public ResponseEntity<Page<OrderDto>> getMyOrders(@PageableDefault(size = 20, sort = "createdAt", direction =
            Sort.Direction.DESC) Pageable pageable, @AuthenticationPrincipal String customerEmail) {
        return ResponseEntity.ok(orderService.findByCustomerMail(customerEmail, pageable));
    }

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

    @PostMapping("/{id}/refund")
    public ResponseEntity<OrderDto> refundOrder(@PathVariable UUID id) {
        orderService.refundOrder(id);
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
