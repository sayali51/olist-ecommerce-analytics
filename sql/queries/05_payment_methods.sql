SELECT 
    payment_type,
    COUNT(*)                                    AS total_transactions,
    ROUND(SUM(payment_value)::numeric, 2)       AS total_value,
    ROUND(AVG(payment_value)::numeric, 2)       AS avg_value,
    ROUND(AVG(payment_installments)::numeric, 1) AS avg_installments
FROM order_payments
GROUP BY payment_type
ORDER BY total_transactions DESC;