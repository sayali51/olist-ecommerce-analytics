SELECT 
    COALESCE(t.product_category_name_english, p.product_category_name, 'Unknown') AS category,
    COUNT(r.review_id)                         AS total_reviews,
    ROUND(AVG(r.review_score)::numeric, 2)     AS avg_score,
    SUM(CASE WHEN r.review_score = 5 THEN 1 ELSE 0 END) AS five_star,
    SUM(CASE WHEN r.review_score = 1 THEN 1 ELSE 0 END) AS one_star
FROM order_reviews r
JOIN orders o       ON r.order_id    = o.order_id
JOIN order_items oi ON o.order_id    = oi.order_id
JOIN products p     ON oi.product_id = p.product_id
LEFT JOIN product_category_translation t 
                    ON p.product_category_name = t.product_category_name
GROUP BY COALESCE(t.product_category_name_english, p.product_category_name, 'Unknown')
HAVING COUNT(r.review_id) > 100
ORDER BY avg_score DESC
LIMIT 15;