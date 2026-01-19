package com.ecommerce.product.service;

import com.ecommerce.common.exception.BusinessException;
import com.ecommerce.common.exception.ResourceNotFoundException;
import com.ecommerce.product.domain.Product;
import com.ecommerce.product.dto.CreateProductRequest;
import com.ecommerce.product.dto.ProductDto;
import com.ecommerce.product.dto.ProductMapper;
import com.ecommerce.product.dto.UpdateProductRequest;
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
@SuppressWarnings("NullableProblems")
public class ProductService {

    private final ProductRepository productRepository;
    private final ProductMapper productMapper;

    @Transactional(readOnly = true)
    public Page<ProductDto> findAll(Pageable pageable) {
        log.debug("Finding all products, page: {}", pageable);
        return productRepository.findAll(pageable)
            .map(productMapper::toDto);
    }

    @Transactional(readOnly = true)
    public Page<ProductDto> findAllActive(Pageable pageable) {
        log.debug("Finding all active products, page: {}", pageable);
        return productRepository.findByIsActiveTrue(pageable)
            .map(productMapper::toDto);
    }

    @Transactional(readOnly = true)
    public Page<ProductDto> searchByName(String name, Pageable pageable) {
        log.debug("Searching products by name: {}", name);
        return productRepository.findByNameContainingIgnoreCaseAndIsActiveTrue(name, pageable)
            .map(productMapper::toDto);
    }

    @Transactional(readOnly = true)
    public ProductDto findById(UUID id) {
        log.debug("Finding product by id: {}", id);
        return productRepository.findById(id)
            .map(productMapper::toDto)
            .orElseThrow(() -> new ResourceNotFoundException("Product", id));
    }

    @Transactional(readOnly = true)
    public ProductDto findBySku(String sku) {
        log.debug("Finding product by SKU: {}", sku);
        return productRepository.findBySku(sku)
            .map(productMapper::toDto)
            .orElseThrow(() -> new ResourceNotFoundException("Product not found with SKU: " + sku));
    }

    @Transactional
    public ProductDto create(CreateProductRequest request) {
        log.info("Creating product with SKU: {}", request.sku());

        if (productRepository.existsBySku(request.sku())) {
            throw new BusinessException("SKU_EXISTS", "Product with SKU '" + request.sku() + "' already exists");
        }

        Product product = productMapper.toEntity(request);
        Product saved = productRepository.save(product);

        log.info("Created product with id: {}", saved.getId());
        return productMapper.toDto(saved);
    }

    @Transactional
    public ProductDto update(UUID id, UpdateProductRequest request) {
        log.info("Updating product with id: {}", id);

        Product product = productRepository.findById(id)
            .orElseThrow(() -> new ResourceNotFoundException("Product", id));

        productMapper.updateEntity(product, request);
        Product saved = productRepository.save(product);

        log.info("Updated product with id: {}", saved.getId());
        return productMapper.toDto(saved);
    }

    @Transactional
    public void delete(UUID id) {
        log.info("Deleting product with id: {}", id);

        if (!productRepository.existsById(id)) {
            throw new ResourceNotFoundException("Product", id);
        }

        productRepository.deleteById(id);
        log.info("Deleted product with id: {}", id);
    }

    @Transactional
    public ProductDto deactivate(UUID id) {
        log.info("Deactivating product with id: {}", id);

        Product product = productRepository.findById(id)
            .orElseThrow(() -> new ResourceNotFoundException("Product", id));

        product.setIsActive(false);
        Product saved = productRepository.save(product);

        log.info("Deactivated product with id: {}", id);
        return productMapper.toDto(saved);
    }

    @Transactional
    public ProductDto activate(UUID id) {
        log.info("Activating product with id: {}", id);

        Product product = productRepository.findById(id)
            .orElseThrow(() -> new ResourceNotFoundException("Product", id));

        product.setIsActive(true);
        Product saved = productRepository.save(product);

        log.info("Activated product with id: {}", id);
        return productMapper.toDto(saved);
    }
}
