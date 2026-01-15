package com.ecommerce.order.domain;

public enum OrderStatus {
    PENDING,        // Ordine creato, in attesa di pagamento
    PAID,           // Pagamento ricevuto
    PROCESSING,     // In preparazione
    SHIPPED,        // Spedito
    DELIVERED,      // Consegnato
    CANCELLED,      // Annullato
    REFUNDED        // Rimborsato
}
