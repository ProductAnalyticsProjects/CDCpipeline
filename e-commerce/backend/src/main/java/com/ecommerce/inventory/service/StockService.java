package com.ecommerce.inventory.service;

import com.ecommerce.common.exception.ResourceNotFoundException;
import com.ecommerce.inventory.domain.Stock;
import com.ecommerce.inventory.domain.Warehouse;
import com.ecommerce.inventory.dto.StockAddRequest;
import com.ecommerce.inventory.dto.StockDto;
import com.ecommerce.inventory.dto.StockMapper;
import com.ecommerce.inventory.repository.StockRepository;
import com.ecommerce.inventory.repository.WarehouseRepository;
import com.ecommerce.product.domain.Product;
import com.ecommerce.product.repository.ProductRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
@SuppressWarnings("NullableProblems")
public class StockService {
    private final StockRepository stockRepository;
    private final StockMapper stockMapper;
    private final WarehouseRepository warehouseRepository;
    private final ProductRepository productRepository;


    public Page<StockDto> findAll(Pageable pageable) {
        return stockRepository.findAll(pageable).map(stockMapper::toDto);
    }

    public List<StockDto> findByProductId(UUID productId) {
        return stockRepository.findByProductId(productId).stream().map(stockMapper::toDto).toList();
    }

    public List<StockDto> findLowStock(int threshold) {
        return stockRepository.findLowStock(threshold).stream().map(stockMapper::toDto).toList();
    }

    public boolean checkAvailability(UUID productId, int quantity) {
        int available = stockRepository.getTotalAvailableQuantity(productId);
        return available >= quantity;
    }

    public StockDto addStock(StockAddRequest request) {

        Stock stock =
                stockRepository.findByProductIdAndWarehouseId(request.productId(), request.warehouseId()).orElseGet(() ->
                        createNewStock(request.productId(), request.warehouseId())
        );
        stock.setAvailableQuantity(stock.getAvailableQuantity() + request.quantity());
        stockRepository.save(stock);
        return stockMapper.toDto(stock);
    }

    public StockDto setStock(UUID productId, UUID warehouseId, int quantity) {
        Stock stock = stockRepository.findByProductIdAndWarehouseId(productId, warehouseId).orElseThrow(() ->
                new ResourceNotFoundException("Stock", productId + "-" + warehouseId));
        stock.setAvailableQuantity(quantity);
        stockRepository.save(stock);
        return stockMapper.toDto(stock);
    }

    public void reserve(UUID productId, UUID warehouseId, int quantity) {
        Stock stock = stockRepository.findByProductIdAndWarehouseId(productId, warehouseId).orElseThrow(() ->
                new ResourceNotFoundException("Stock", productId + "-" + warehouseId));
        stock.reserve(quantity);
        stockRepository.save(stock);
    }

    public void release(UUID productId, UUID warehouseId, int quantity) {
        Stock stock = stockRepository.findByProductIdAndWarehouseId(productId, warehouseId).orElseThrow(() ->
                new ResourceNotFoundException("Stock", productId + "-" + warehouseId));
        stock.releaseReservation(quantity);
        stockRepository.save(stock);
    }

    public void confirm(UUID productId, UUID warehouseId, int quantity) {
        Stock stock = stockRepository.findByProductIdAndWarehouseId(productId, warehouseId).orElseThrow(() ->
                new ResourceNotFoundException("Stock", productId + "-" + warehouseId));
        stock.confirmReservation(quantity);
        stockRepository.save(stock);
    }

    private Stock createNewStock(UUID productId, UUID warehouseId) {
        Product product =
                productRepository.findById(productId).orElseThrow(() -> new ResourceNotFoundException("Product",
                        productId));
        Warehouse warehouse = warehouseRepository.findById(warehouseId).orElseThrow(() -> new ResourceNotFoundException(
                "Warehouse", warehouseId));

        return Stock.builder()
                .product(product)
                .warehouse(warehouse)
                .availableQuantity(0)
                .reservedQuantity(0)
                .build();

    }
}
