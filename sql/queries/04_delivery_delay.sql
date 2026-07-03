SELECT 
    c.customer_state,
    COUNT(*) AS total_delivered,
    SUM(CASE 
        WHEN o.order_delivered_customer_date::timestamp > o.order_estimated_delivery_date::timestamp 
        THEN 1 ELSE 0 
    END) AS late_deliveries,
    ROUND(100.0 * SUM(CASE 
        WHEN o.order_delivered_customer_date::timestamp > o.order_estimated_delivery_date::timestamp 
        THEN 1 ELSE 0 
    END) / COUNT(*), 2) AS late_delivery_pct,
    ROUND(AVG(
        EXTRACT(EPOCH FROM (
            o.order_delivered_customer_date::timestamp - o.order_purchase_timestamp::timestamp
        )) / 86400
    )::numeric, 1) AS avg_delivery_days
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
GROUP BY c.customer_state
ORDER BY late_delivery_pct DESC;