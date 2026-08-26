SELECT
    user_email,
    role,
    COUNT(*) AS total_orders,
    SUM(total_amount) AS total_spent,
    AVG(total_amount) AS avg_order_value,
    MIN(CAST(FROM_UNIXTIME(created_at / 1000000) AS DATE)) AS first_order_date,
    MAX(CAST(FROM_UNIXTIME(created_at / 1000000) AS DATE)) AS last_order_date
FROM delta.default.orders
GROUP BY user_email, role
ORDER BY total_spent DESC
