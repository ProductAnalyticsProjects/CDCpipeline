SELECT
    status,
    COUNT(*) AS total_orders,
    SUM(total_amount) AS total_revenue
FROM delta.default.orders
GROUP BY status
ORDER BY total_orders DESC
