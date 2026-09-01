SELECT
    user_email,
    role,
    COUNT(*) AS total_orders,
    SUM(total_amount) AS total_spent,
    AVG(total_amount) AS avg_order_value,
    MIN(CAST(created_at AS DATE)) AS first_order_date,
    MAX(CAST(created_at AS DATE)) AS last_order_date
FROM delta.default.orders
GROUP BY user_email, role
ORDER BY total_spent DESC
