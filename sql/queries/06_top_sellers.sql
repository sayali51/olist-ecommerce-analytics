SELECT 
    oi.seller_id,
    s.seller_city,
    s.seller_state,
    COUNT(DISTINCT oi.order_id)               AS total_orders,
    ROUND(SUM(oi.price)::numeric, 2)          AS total_revenue,
    ROUND(AVG(oi.price)::numeric, 2)          AS avg_price,
    ROUND(AVG(r.review_score)::numeric, 2)    AS avg_review_score
FROM order_items oi
JOIN sellers s      ON oi.seller_id  = s.seller_id
JOIN orders o       ON oi.order_id   = o.order_id
JOIN order_reviews r ON o.order_id   = r.order_id
WHERE o.order_status = 'delivered'
GROUP BY oi.seller_id, s.seller_city, s.seller_state
ORDER BY total_revenue DESC
LIMIT 10;