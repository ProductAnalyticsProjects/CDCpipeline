package com.ecommerce.inventory.controller;

import com.ecommerce.inventory.dto.StockAddRequest;
import com.ecommerce.inventory.dto.StockDto;
import com.ecommerce.inventory.service.StockService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/v1/inventory")
@RequiredArgsConstructor
@SuppressWarnings("NullableProblems")
@Slf4j
public class StockController {

    private final StockService stockService;

    @GetMapping
    public ResponseEntity<Page<StockDto>> getAllStocks(
            @PageableDefault(size = 20, sort = "createdAt", direction = Sort.Direction.DESC) Pageable pageable
    ) {
        return ResponseEntity.ok(stockService.findAll(pageable));
    }

    @GetMapping("/low-stock")
    public ResponseEntity<List<StockDto>> getLowStock(@RequestParam(defaultValue = "10") Integer threshold) {
        return ResponseEntity.ok(stockService.findLowStock(threshold));
    }

    @GetMapping("/{productId}")
    public ResponseEntity<List<StockDto>> getStockByProductId(@PathVariable UUID productId) {
        return ResponseEntity.ok(stockService.findByProductId(productId));
    }

    @GetMapping("/{productId}/availability")
    public ResponseEntity<Boolean> checkAvailability(@PathVariable UUID productId, @RequestParam int quantity) {
        return ResponseEntity.ok(stockService.checkAvailability(productId, quantity));
    }

    @PostMapping
    public ResponseEntity<StockDto> addStock(@Valid @RequestBody StockAddRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(stockService.addStock(request));
    }

    @PutMapping("/{productId}")
    public ResponseEntity<StockDto> setStock(@PathVariable UUID productId,
                                             @RequestParam UUID warehouseId, @RequestParam int quantity) {
        return ResponseEntity.ok(stockService.setStock(productId, warehouseId, quantity));
    }

}
