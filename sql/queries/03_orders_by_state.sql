SELECT 
    c.customer_state                          AS state,
    COUNT(DISTINCT o.order_id)                AS total_orders,
    ROUND(SUM(oi.price)::numeric, 2)          AS total_revenue,
    ROUND(AVG(oi.price)::numeric, 2)          AS avg_order_value
FROM orders o
JOIN customers c    ON o.customer_id  = c.customer_id
JOIN order_items oi ON o.order_id     = oi.order_id
WHERE o.order_status = 'delivered'
GROUP BY c.customer_state
ORDER BY total_orders DESC
LIMIT 10;