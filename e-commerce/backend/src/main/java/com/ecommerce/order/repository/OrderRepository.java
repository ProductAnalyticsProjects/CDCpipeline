package com.ecommerce.order.repository;

import com.ecommerce.order.domain.Order;
import com.ecommerce.order.domain.OrderStatus;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface OrderRepository extends JpaRepository<Order, UUID> {

    Page<Order> findByCustomerEmail(String customerEmail, Pageable pageable);

    Page<Order> findByStatus(OrderStatus status, Pageable pageable);

    Page<Order> findByCustomerEmailAndStatus(String customerEmail, OrderStatus status, Pageable pageable);

    @Query("SELECT o FROM Order o WHERE o.status = :status AND o.createdAt < :beforeDate")
    List<Order> findByStatusAndCreatedAtBefore(
        @Param("status") OrderStatus status,
        @Param("beforeDate") OffsetDateTime beforeDate
    );

    @Query("SELECT o FROM Order o LEFT JOIN FETCH o.items WHERE o.id = :id")
    Optional<Order> findByIdWithItems(@Param("id") UUID id);

    @Query("SELECT COUNT(o) FROM Order o WHERE o.status = :status")
    long countByStatus(@Param("status") OrderStatus status);

    Optional<Order> findByIdempotencyKey(String idempotencyKey);
}
