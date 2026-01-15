package com.ecommerce.inventory.domain;

import com.ecommerce.common.config.BaseEntity;
import com.ecommerce.product.domain.Product;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "stocks", uniqueConstraints = {
    @UniqueConstraint(columnNames = {"product_id", "warehouse_id"})
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Stock extends BaseEntity {

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "product_id", nullable = false)
    private Product product;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "warehouse_id", nullable = false)
    private Warehouse warehouse;

    @Column(name = "available_quantity", nullable = false)
    @Builder.Default
    private Integer availableQuantity = 0;

    @Column(name = "reserved_quantity", nullable = false)
    @Builder.Default
    private Integer reservedQuantity = 0;

    /**
     * Returns the total quantity (available + reserved)
     */
    public Integer getTotalQuantity() {
        return availableQuantity + reservedQuantity;
    }

    /**
     * Check if we can reserve the requested quantity
     */
    public boolean canReserve(int quantity) {
        return availableQuantity >= quantity;
    }

    /**
     * Reserve stock (move from available to reserved)
     */
    public void reserve(int quantity) {
        if (!canReserve(quantity)) {
            throw new IllegalStateException("Not enough available stock to reserve");
        }
        this.availableQuantity -= quantity;
        this.reservedQuantity += quantity;
    }

    /**
     * Release reserved stock (move back to available)
     */
    public void releaseReservation(int quantity) {
        if (reservedQuantity < quantity) {
            throw new IllegalStateException("Not enough reserved stock to release");
        }
        this.reservedQuantity -= quantity;
        this.availableQuantity += quantity;
    }

    /**
     * Confirm reservation (remove from reserved, stock leaves warehouse)
     */
    public void confirmReservation(int quantity) {
        if (reservedQuantity < quantity) {
            throw new IllegalStateException("Not enough reserved stock to confirm");
        }
        this.reservedQuantity -= quantity;
    }
}
