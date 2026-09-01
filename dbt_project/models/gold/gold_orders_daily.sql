SELECT
    CAST(created_at AS DATE) AS order_date,
    COUNT(*) AS total_orders,
    SUM(total_amount) AS total_revenue,
    AVG(total_amount) AS avg_order_value
FROM delta.default.orders
GROUP BY 1
ORDER BY 1
