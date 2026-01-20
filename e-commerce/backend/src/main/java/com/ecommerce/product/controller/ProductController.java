package com.ecommerce.product.controller;

import com.ecommerce.product.dto.CreateProductRequest;
import com.ecommerce.product.dto.ProductDto;
import com.ecommerce.product.dto.UpdateProductRequest;
import com.ecommerce.product.service.ProductService;
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

import java.util.UUID;

@RestController
@RequestMapping("/v1/product")
@RequiredArgsConstructor
@SuppressWarnings("NullableProblems")
@Slf4j
public class ProductController {

    private final ProductService productService;

    @GetMapping
    public ResponseEntity<Page<ProductDto>> getAllProducts(
            @PageableDefault(size = 20, sort = "createdAt", direction = Sort.Direction.DESC) Pageable pageable,
            @RequestParam(required = false) String search,
            @RequestParam(required = false, defaultValue = "false") boolean includeInactive
    ) {
        log.debug("GET /v1/products - search: {}, includeInactive: {}", search, includeInactive);

        Page<ProductDto> products;
        if (search != null && !search.isBlank()) {
            products = productService.searchByName(search, pageable);
        } else if (includeInactive) {
            products = productService.findAll(pageable);
        } else {
            products = productService.findAllActive(pageable);
        }

        return ResponseEntity.ok(products);
    }

    @GetMapping("/{id}")
    public ResponseEntity<ProductDto> getProductById(@PathVariable UUID id) {
        log.debug("GET /v1/products/{}", id);
        ProductDto product = productService.findById(id);
        return ResponseEntity.ok(product);
    }

    @GetMapping("/sku/{sku}")
    public ResponseEntity<ProductDto> getProductBySku(@PathVariable String sku) {
        log.debug("GET /v1/products/sku/{}", sku);
        ProductDto product = productService.findBySku(sku);
        return ResponseEntity.ok(product);
    }

    @PostMapping
    public ResponseEntity<ProductDto> createProduct(@Valid @RequestBody CreateProductRequest request) {
        log.debug("POST /v1/products - SKU: {}", request.sku());
        ProductDto created = productService.create(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }

    @PutMapping("/{id}")
    public ResponseEntity<ProductDto> updateProduct(
            @PathVariable UUID id,
            @Valid @RequestBody UpdateProductRequest request
    ) {
        log.debug("PUT /v1/products/{}", id);
        ProductDto updated = productService.update(id, request);
        return ResponseEntity.ok(updated);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteProduct(@PathVariable UUID id) {
        log.debug("DELETE /v1/products/{}", id);
        productService.delete(id);
        return ResponseEntity.noContent().build();
    }

    @PostMapping("/{id}/deactivate")
    public ResponseEntity<ProductDto> deactivateProduct(@PathVariable UUID id) {
        log.debug("POST /v1/products/{}/deactivate", id);
        ProductDto product = productService.deactivate(id);
        return ResponseEntity.ok(product);
    }

    @PostMapping("/{id}/activate")
    public ResponseEntity<ProductDto> activateProduct(@PathVariable UUID id) {
        log.debug("POST /v1/products/{}/activate", id);
        ProductDto product = productService.activate(id);
        return ResponseEntity.ok(product);
    }
}
