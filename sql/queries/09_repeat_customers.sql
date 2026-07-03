WITH customer_orders AS (
    SELECT 
        c.customer_unique_id,
        COUNT(DISTINCT o.order_id) AS order_count
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id
)
SELECT 
    CASE 
        WHEN order_count = 1 THEN 'One-time buyer'
        WHEN order_count = 2 THEN 'Repeat (2 orders)'
        WHEN order_count BETWEEN 3 AND 5 THEN 'Loyal (3-5 orders)'
        ELSE 'Champion (6+ orders)'
    END AS customer_segment,
    COUNT(*) AS customer_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS percentage
FROM customer_orders
GROUP BY customer_segment
ORDER BY customer_count DESC;