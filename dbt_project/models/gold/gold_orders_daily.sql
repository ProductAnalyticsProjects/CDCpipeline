SELECT
    CAST(FROM_UNIXTIME(created_at / 1000000) AS DATE) AS order_date,
    COUNT(*) AS total_orders,
    SUM(total_amount) AS total_revenue,
    AVG(total_amount) AS avg_order_value
FROM delta.default.orders
GROUP BY 1
ORDER BY 1
