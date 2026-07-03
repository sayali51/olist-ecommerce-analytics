SELECT 
    COALESCE(t.product_category_name_english, p.product_category_name, 'Unknown') AS category,
    COUNT(DISTINCT o.order_id)                                AS total_orders,
    ROUND(SUM(oi.price)::numeric, 2)                         AS total_revenue,
    ROUND(AVG(oi.price)::numeric, 2)                         AS avg_item_price
FROM order_items oi
JOIN orders o       ON oi.order_id   = o.order_id
JOIN products p     ON oi.product_id = p.product_id
LEFT JOIN product_category_translation t 
                    ON p.product_category_name = t.product_category_name
WHERE o.order_status = 'delivered'
GROUP BY COALESCE(t.product_category_name_english, p.product_category_name, 'Unknown')
ORDER BY total_revenue DESC
LIMIT 15;