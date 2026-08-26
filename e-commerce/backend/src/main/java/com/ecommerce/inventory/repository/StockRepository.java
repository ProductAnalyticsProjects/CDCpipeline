package com.ecommerce.inventory.repository;

import com.ecommerce.inventory.domain.Stock;
import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface StockRepository extends JpaRepository<Stock, UUID> {

    /**
     * Find stock by product and warehouse
     */
    Optional<Stock> findByProductIdAndWarehouseId(UUID productId, UUID warehouseId);

    /**
     * Find stock with pessimistic lock for updates
     */
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("SELECT s FROM Stock s WHERE s.product.id = :productId AND s.warehouse.id = :warehouseId")
    Optional<Stock> findByProductIdAndWarehouseIdWithLock(
        @Param("productId") UUID productId,
        @Param("warehouseId") UUID warehouseId
    );

    /**
     * Find all stocks for a product across warehouses
     */
    List<Stock> findByProductId(UUID productId);

    /**
     * Find all stocks in a warehouse
     */
    List<Stock> findByWarehouseId(UUID warehouseId);

    /**
     * Find low stock items (available below threshold)
     */
    @Query("SELECT s FROM Stock s WHERE s.availableQuantity < :threshold AND s.warehouse.isActive = true")
    List<Stock> findLowStock(@Param("threshold") int threshold);

    /**
     * Get total available quantity for a product across all warehouses
     */
    @Query("SELECT COALESCE(SUM(s.availableQuantity), 0) FROM Stock s WHERE s.product.id = :productId")
    int getTotalAvailableQuantity(@Param("productId") UUID productId);
}
