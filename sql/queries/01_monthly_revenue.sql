SELECT 
    DATE_TRUNC('month', o.order_purchase_timestamp::timestamp) AS month,
    COUNT(DISTINCT o.order_id) AS total_orders,
    ROUND(SUM(oi.price + oi.freight_value)::numeric, 2) AS total_revenue,
    ROUND(AVG(oi.price + oi.freight_value)::numeric, 2) AS avg_order_value
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered'
  AND o.order_purchase_timestamp::timestamp >= '2017-01-01'
GROUP BY DATE_TRUNC('month', o.order_purchase_timestamp::timestamp)
ORDER BY month;