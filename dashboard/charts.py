import os
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

DB_USER     = "postgres"
DB_PASSWORD = "postgres123" 
DB_HOST     = "localhost"
DB_PORT     = "5432"
DB_NAME     = "olist_db"

engine = create_engine(
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

def run(sql):
    return pd.read_sql(sql, engine)

os.makedirs("dashboard/outputs", exist_ok=True)

# ── Chart 1 — Monthly Revenue Trend ─────────────────────────────────
print("Building Chart 1...")
q1 = run("""
    SELECT DATE_TRUNC('month', o.order_purchase_timestamp::timestamp) AS month,
        COUNT(DISTINCT o.order_id) AS total_orders,
        ROUND(SUM(oi.price + oi.freight_value)::numeric, 2) AS total_revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp::timestamp >= '2017-01-01'
    GROUP BY DATE_TRUNC('month', o.order_purchase_timestamp::timestamp)
    ORDER BY month
""")
q1['month'] = pd.to_datetime(q1['month'])

fig1 = make_subplots(specs=[[{"secondary_y": True}]])
fig1.add_trace(go.Bar(x=q1['month'], y=q1['total_revenue'],
    name='Revenue (BRL)', marker_color='#2196F3'), secondary_y=False)
fig1.add_trace(go.Scatter(x=q1['month'], y=q1['total_orders'],
    name='Total Orders', line=dict(color='#FF5722', width=2), mode='lines+markers'), secondary_y=True)
fig1.update_layout(title='Monthly Revenue & Order Trend (2017–2018)',
    xaxis_title='Month', template='plotly_white', height=500)
fig1.update_yaxes(title_text="Revenue (BRL)", secondary_y=False)
fig1.update_yaxes(title_text="Total Orders", secondary_y=True)
fig1.write_html("dashboard/outputs/01_monthly_revenue.html")
print("  ✓ Saved")

# ── Chart 2 — Top 15 Categories by Revenue ──────────────────────────
print("Building Chart 2...")
q2 = run("""
    SELECT COALESCE(t.product_category_name_english, p.product_category_name, 'Unknown') AS category,
        COUNT(DISTINCT o.order_id) AS total_orders,
        ROUND(SUM(oi.price)::numeric, 2) AS total_revenue
    FROM order_items oi
    JOIN orders o   ON oi.order_id   = o.order_id
    JOIN products p ON oi.product_id = p.product_id
    LEFT JOIN product_category_translation t ON p.product_category_name = t.product_category_name
    WHERE o.order_status = 'delivered'
    GROUP BY COALESCE(t.product_category_name_english, p.product_category_name, 'Unknown')
    ORDER BY total_revenue DESC LIMIT 15
""")

fig2 = px.bar(q2.sort_values('total_revenue'), x='total_revenue', y='category',
    orientation='h', color='total_revenue', color_continuous_scale='Blues',
    title='Top 15 Product Categories by Revenue',
    labels={'total_revenue': 'Total Revenue (BRL)', 'category': 'Category'})
fig2.update_layout(template='plotly_white', height=550, showlegend=False)
fig2.write_html("dashboard/outputs/02_revenue_by_category.html")
print("  ✓ Saved")

# ── Chart 3 — Orders by State ────────────────────────────────────────
print("Building Chart 3...")
q3 = run("""
    SELECT c.customer_state AS state,
        COUNT(DISTINCT o.order_id) AS total_orders,
        ROUND(SUM(oi.price)::numeric, 2) AS total_revenue
    FROM orders o
    JOIN customers c    ON o.customer_id  = c.customer_id
    JOIN order_items oi ON o.order_id     = oi.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_state
    ORDER BY total_orders DESC LIMIT 10
""")

fig3 = px.bar(q3, x='state', y='total_orders',
    color='total_revenue', color_continuous_scale='Viridis',
    title='Top 10 States by Order Volume',
    labels={'state': 'State', 'total_orders': 'Total Orders', 'total_revenue': 'Revenue (BRL)'})
fig3.update_layout(template='plotly_white', height=500)
fig3.write_html("dashboard/outputs/03_orders_by_state.html")
print("  ✓ Saved")

# ── Chart 4 — Late Delivery % by State ──────────────────────────────
print("Building Chart 4...")
q4 = run("""
    SELECT c.customer_state,
        COUNT(*) AS total_delivered,
        ROUND(100.0 * SUM(CASE WHEN o.order_delivered_customer_date::timestamp > o.order_estimated_delivery_date::timestamp THEN 1 ELSE 0 END) / COUNT(*), 2) AS late_delivery_pct,
        ROUND(AVG(EXTRACT(EPOCH FROM (o.order_delivered_customer_date::timestamp - o.order_purchase_timestamp::timestamp)) / 86400)::numeric, 1) AS avg_delivery_days
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
    GROUP BY c.customer_state
    ORDER BY late_delivery_pct DESC
""")

fig4 = px.scatter(q4, x='avg_delivery_days', y='late_delivery_pct',
    size='total_delivered', text='customer_state',
    color='late_delivery_pct', color_continuous_scale='Reds',
    title='Delivery Performance by State (Size = Order Volume)',
    labels={'avg_delivery_days': 'Avg Delivery Days', 'late_delivery_pct': 'Late Delivery %'})
fig4.update_traces(textposition='top center')
fig4.update_layout(template='plotly_white', height=550)
fig4.write_html("dashboard/outputs/04_delivery_delay.html")
print("  ✓ Saved")

# ── Chart 5 — Payment Methods ────────────────────────────────────────
print("Building Chart 5...")
q5 = run("""
    SELECT payment_type,
        COUNT(*) AS total_transactions,
        ROUND(AVG(payment_value)::numeric, 2) AS avg_value
    FROM order_payments
    GROUP BY payment_type
    ORDER BY total_transactions DESC
""")

fig5 = px.pie(q5, names='payment_type', values='total_transactions',
    title='Payment Method Distribution',
    color_discrete_sequence=px.colors.qualitative.Set2)
fig5.update_traces(textposition='inside', textinfo='percent+label')
fig5.update_layout(template='plotly_white', height=500)
fig5.write_html("dashboard/outputs/05_payment_methods.html")
print("  ✓ Saved")

# ── Chart 6 — Review Score by Category ──────────────────────────────
print("Building Chart 6...")
q7 = run("""
    SELECT COALESCE(t.product_category_name_english, p.product_category_name, 'Unknown') AS category,
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

fig6 = px.bar(q7.sort_values('avg_score'), x='avg_score', y='category',
    orientation='h', color='avg_score',
    color_continuous_scale='RdYlGn',
    title='Average Review Score by Product Category (min 100 reviews)',
    labels={'avg_score': 'Avg Review Score', 'category': 'Category'})
fig6.update_layout(template='plotly_white', height=550)
fig6.write_html("dashboard/outputs/06_reviews_by_category.html")
print("  ✓ Saved")

# ── Chart 7 — Late vs On-Time Review Impact ──────────────────────────
print("Building Chart 7...")
q8 = run("""
    WITH delivery_status AS (
        SELECT o.order_id, r.review_score,
            CASE WHEN o.order_delivered_customer_date::timestamp <= o.order_estimated_delivery_date::timestamp 
                 THEN 'On Time' ELSE 'Late' END AS delivery_result
        FROM orders o
        JOIN order_reviews r ON o.order_id = r.order_id
        WHERE o.order_status = 'delivered'
          AND o.order_delivered_customer_date IS NOT NULL
    )
    SELECT delivery_result, review_score, COUNT(*) AS count
    FROM delivery_status
    GROUP BY delivery_result, review_score
    ORDER BY delivery_result, review_score
""")

fig7 = px.bar(q8, x='review_score', y='count', color='delivery_result',
    barmode='group', title='Review Score Distribution: On Time vs Late Deliveries',
    labels={'review_score': 'Review Score (1-5)', 'count': 'Number of Orders'},
    color_discrete_map={'On Time': '#4CAF50', 'Late': '#F44336'})
fig7.update_layout(template='plotly_white', height=500)
fig7.write_html("dashboard/outputs/07_delay_vs_reviews.html")
print("  ✓ Saved")

# ── Chart 8 — Customer Segments ──────────────────────────────────────
print("Building Chart 8...")
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

fig8 = px.funnel(q9, x='customer_count', y='customer_segment',
    title='Customer Loyalty Segments',
    labels={'customer_count': 'Number of Customers', 'customer_segment': 'Segment'})
fig8.update_layout(template='plotly_white', height=450)
fig8.write_html("dashboard/outputs/08_customer_segments.html")
print("  ✓ Saved")

# ── Chart 9 — Freight % of Price by Category ────────────────────────
print("Building Chart 9...")
q10 = run("""
    SELECT COALESCE(t.product_category_name_english, p.product_category_name, 'Unknown') AS category,
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

fig9 = px.scatter(q10, x='avg_product_price', y='avg_freight',
    size='freight_pct_of_price', color='freight_pct_of_price',
    text='category', color_continuous_scale='Oranges',
    title='Freight Cost vs Product Price by Category',
    labels={'avg_product_price': 'Avg Product Price (BRL)', 'avg_freight': 'Avg Freight (BRL)'})
fig9.update_traces(textposition='top center')
fig9.update_layout(template='plotly_white', height=600)
fig9.write_html("dashboard/outputs/09_freight_analysis.html")
print("  ✓ Saved")

print("\n✅ All 9 charts saved to dashboard/outputs/")
print("Open any .html file in your browser to view the charts!")