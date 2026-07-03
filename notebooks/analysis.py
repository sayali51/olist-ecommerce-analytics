import os
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── Database connection ──────────────────────────────────────────────
DB_USER     = "postgres"
DB_PASSWORD = "postgres123"   #password
DB_HOST     = "localhost"
DB_PORT     = "5432"
DB_NAME     = "olist_db"

engine = create_engine(
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ── Helper ───────────────────────────────────────────────────────────
def run(sql):
    return pd.read_sql(sql, engine)

# ── Query 1 — Monthly Revenue ────────────────────────────────────────
q1 = run("""
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
    ORDER BY month
""")
print("Q1 Monthly Revenue:"); print(q1.to_string()); print()

# ── Query 2 — Revenue by Category ───────────────────────────────────
q2 = run("""
    SELECT 
        COALESCE(t.product_category_name_english, p.product_category_name, 'Unknown') AS category,
        COUNT(DISTINCT o.order_id) AS total_orders,
        ROUND(SUM(oi.price)::numeric, 2) AS total_revenue,
        ROUND(AVG(oi.price)::numeric, 2) AS avg_item_price
    FROM order_items oi
    JOIN orders o   ON oi.order_id   = o.order_id
    JOIN products p ON oi.product_id = p.product_id
    LEFT JOIN product_category_translation t ON p.product_category_name = t.product_category_name
    WHERE o.order_status = 'delivered'
    GROUP BY COALESCE(t.product_category_name_english, p.product_category_name, 'Unknown')
    ORDER BY total_revenue DESC LIMIT 15
""")
print("Q2 Revenue by Category:"); print(q2.to_string()); print()

# ── Query 3 — Orders by State ────────────────────────────────────────
q3 = run("""
    SELECT 
        c.customer_state AS state,
        COUNT(DISTINCT o.order_id) AS total_orders,
        ROUND(SUM(oi.price)::numeric, 2) AS total_revenue,
        ROUND(AVG(oi.price)::numeric, 2) AS avg_order_value
    FROM orders o
    JOIN customers c    ON o.customer_id  = c.customer_id
    JOIN order_items oi ON o.order_id     = oi.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_state
    ORDER BY total_orders DESC LIMIT 10
""")
print("Q3 Orders by State:"); print(q3.to_string()); print()

# ── Query 4 — Delivery Delay ─────────────────────────────────────────
q4 = run("""
    SELECT 
        c.customer_state,
        COUNT(*) AS total_delivered,
        SUM(CASE WHEN o.order_delivered_customer_date::timestamp > o.order_estimated_delivery_date::timestamp THEN 1 ELSE 0 END) AS late_deliveries,
        ROUND(100.0 * SUM(CASE WHEN o.order_delivered_customer_date::timestamp > o.order_estimated_delivery_date::timestamp THEN 1 ELSE 0 END) / COUNT(*), 2) AS late_delivery_pct,
        ROUND(AVG(EXTRACT(EPOCH FROM (o.order_delivered_customer_date::timestamp - o.order_purchase_timestamp::timestamp)) / 86400)::numeric, 1) AS avg_delivery_days
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
    GROUP BY c.customer_state
    ORDER BY late_delivery_pct DESC
""")
print("Q4 Delivery Delay:"); print(q4.to_string()); print()

# ── Query 5 — Payment Methods ────────────────────────────────────────
q5 = run("""
    SELECT 
        payment_type,
        COUNT(*) AS total_transactions,
        ROUND(SUM(payment_value)::numeric, 2) AS total_value,
        ROUND(AVG(payment_value)::numeric, 2) AS avg_value,
        ROUND(AVG(payment_installments)::numeric, 1) AS avg_installments
    FROM order_payments
    GROUP BY payment_type
    ORDER BY total_transactions DESC
""")
print("Q5 Payment Methods:"); print(q5.to_string()); print()

# ── Query 6 — Top Sellers ────────────────────────────────────────────
q6 = run("""
    SELECT 
        oi.seller_id, s.seller_city, s.seller_state,
        COUNT(DISTINCT oi.order_id) AS total_orders,
        ROUND(SUM(oi.price)::numeric, 2) AS total_revenue,
        ROUND(AVG(oi.price)::numeric, 2) AS avg_price,
        ROUND(AVG(r.review_score)::numeric, 2) AS avg_review_score
    FROM order_items oi
    JOIN sellers s       ON oi.seller_id = s.seller_id
    JOIN orders o        ON oi.order_id  = o.order_id
    JOIN order_reviews r ON o.order_id   = r.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY oi.seller_id, s.seller_city, s.seller_state
    ORDER BY total_revenue DESC LIMIT 10
""")
print("Q6 Top Sellers:"); print(q6.to_string()); print()

# ── Query 7 — Reviews by Category ───────────────────────────────────
q7 = run("""
    SELECT 
        COALESCE(t.product_category_name_english, p.product_category_name, 'Unknown') AS category,
        COUNT(r.review_id) AS total_reviews,
        ROUND(AVG(r.review_score)::numeric, 2) AS avg_score,
        SUM(CASE WHEN r.review_score = 5 THEN 1 ELSE 0 END) AS five_star,
        SUM(CASE WHEN r.review_score = 1 THEN 1 ELSE 0 END) AS one_star
    FROM order_reviews r
    JOIN orders o       ON r.order_id    = o.order_id
    JOIN order_items oi ON o.order_id    = oi.order_id
    JOIN products p     ON oi.product_id = p.product_id
    LEFT JOIN product_category_translation t ON p.product_category_name = t.product_category_name
    GROUP BY COALESCE(t.product_category_name_english, p.product_category_name, 'Unknown')
    HAVING COUNT(r.review_id) > 100
    ORDER BY avg_score DESC LIMIT 15
""")
print("Q7 Reviews by Category:"); print(q7.to_string()); print()

# ── Query 8 — Delay vs Reviews ───────────────────────────────────────
q8 = run("""
    WITH delivery_status AS (
        SELECT o.order_id, r.review_score,
            CASE WHEN o.order_delivered_customer_date::timestamp <= o.order_estimated_delivery_date::timestamp THEN 'On Time' ELSE 'Late' END AS delivery_result,
            EXTRACT(EPOCH FROM (o.order_delivered_customer_date::timestamp - o.order_estimated_delivery_date::timestamp)) / 86400 AS days_late
        FROM orders o
        JOIN order_reviews r ON o.order_id = r.order_id
        WHERE o.order_status = 'delivered'
          AND o.order_delivered_customer_date IS NOT NULL
    )
    SELECT delivery_result, COUNT(*) AS total_orders,
        ROUND(AVG(review_score)::numeric, 2) AS avg_review_score,
        ROUND(AVG(CASE WHEN days_late > 0 THEN days_late END)::numeric, 1) AS avg_days_late
    FROM delivery_status
    GROUP BY delivery_result
    ORDER BY avg_review_score DESC
""")
print("Q8 Delay vs Reviews:"); print(q8.to_string()); print()

# ── Query 9 — Repeat Customers ───────────────────────────────────────
q9 = run("""
    WITH customer_orders AS (
        SELECT c.customer_unique_id, COUNT(DISTINCT o.order_id) AS order_count
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
    ORDER BY customer_count DESC
""")
print("Q9 Repeat Customers:"); print(q9.to_string()); print()

# ── Query 10 — Freight Analysis ──────────────────────────────────────
q10 = run("""
    SELECT 
        COALESCE(t.product_category_name_english, p.product_category_name, 'Unknown') AS category,
        ROUND(AVG(oi.price)::numeric, 2) AS avg_product_price,
        ROUND(AVG(oi.freight_value)::numeric, 2) AS avg_freight,
        ROUND(AVG(oi.freight_value / NULLIF(oi.price, 0) * 100)::numeric, 1) AS freight_pct_of_price
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    LEFT JOIN product_category_translation t ON p.product_category_name = t.product_category_name
    GROUP BY COALESCE(t.product_category_name_english, p.product_category_name, 'Unknown')
    HAVING AVG(oi.price) > 50
    ORDER BY freight_pct_of_price DESC LIMIT 15
""")
print("Q10 Freight Analysis:"); print(q10.to_string()); print()

print("✅ All 10 queries ran successfully!")