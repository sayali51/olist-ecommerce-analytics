WITH delivery_status AS (
    SELECT 
        o.order_id,
        r.review_score,
        CASE 
            WHEN o.order_delivered_customer_date::timestamp <= o.order_estimated_delivery_date::timestamp 
            THEN 'On Time'
            ELSE 'Late'
        END AS delivery_result,
        EXTRACT(EPOCH FROM (
            o.order_delivered_customer_date::timestamp - o.order_estimated_delivery_date::timestamp
        )) / 86400 AS days_late
    FROM orders o
    JOIN order_reviews r ON o.order_id = r.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
)
SELECT 
    delivery_result,
    COUNT(*)                                  AS total_orders,
    ROUND(AVG(review_score)::numeric, 2)      AS avg_review_score,
    ROUND(AVG(CASE WHEN days_late > 0 THEN days_late END)::numeric, 1) AS avg_days_late
FROM delivery_status
GROUP BY delivery_result
ORDER BY avg_review_score DESC;