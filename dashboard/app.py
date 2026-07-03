import os
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from dash import dcc, html

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

print("Loading data from PostgreSQL...")

# ── Load all data ────────────────────────────────────────────────────
q1 = run("""
    SELECT DATE_TRUNC('month', o.order_purchase_timestamp::timestamp) AS month,
        COUNT(DISTINCT o.order_id) AS total_orders,
        ROUND(SUM(oi.price + oi.freight_value)::numeric, 2) AS total_revenue
    FROM orders o JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp::timestamp >= '2017-01-01'
    GROUP BY DATE_TRUNC('month', o.order_purchase_timestamp::timestamp)
    ORDER BY month
""")
q1['month'] = pd.to_datetime(q1['month'])

q2 = run("""
    SELECT COALESCE(t.product_category_name_english, p.product_category_name, 'Unknown') AS category,
        ROUND(SUM(oi.price)::numeric, 2) AS total_revenue,
        COUNT(DISTINCT o.order_id) AS total_orders
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.order_id
    JOIN products p ON oi.product_id = p.product_id
    LEFT JOIN product_category_translation t ON p.product_category_name = t.product_category_name
    WHERE o.order_status = 'delivered'
    GROUP BY COALESCE(t.product_category_name_english, p.product_category_name, 'Unknown')
    ORDER BY total_revenue DESC LIMIT 15
""")

q3 = run("""
    SELECT c.customer_state AS state,
        COUNT(DISTINCT o.order_id) AS total_orders,
        ROUND(SUM(oi.price)::numeric, 2) AS total_revenue
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_state ORDER BY total_orders DESC LIMIT 10
""")

q4 = run("""
    SELECT c.customer_state,
        COUNT(*) AS total_delivered,
        ROUND(100.0 * SUM(CASE WHEN o.order_delivered_customer_date::timestamp > o.order_estimated_delivery_date::timestamp THEN 1 ELSE 0 END) / COUNT(*), 2) AS late_delivery_pct,
        ROUND(AVG(EXTRACT(EPOCH FROM (o.order_delivered_customer_date::timestamp - o.order_purchase_timestamp::timestamp)) / 86400)::numeric, 1) AS avg_delivery_days
    FROM orders o JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
    GROUP BY c.customer_state ORDER BY late_delivery_pct DESC
""")

q5 = run("""
    SELECT payment_type, COUNT(*) AS total_transactions,
        ROUND(AVG(payment_value)::numeric, 2) AS avg_value
    FROM order_payments GROUP BY payment_type ORDER BY total_transactions DESC
""")

q7 = run("""
    SELECT COALESCE(t.product_category_name_english, p.product_category_name, 'Unknown') AS category,
        ROUND(AVG(r.review_score)::numeric, 2) AS avg_score,
        COUNT(r.review_id) AS total_reviews
    FROM order_reviews r
    JOIN orders o ON r.order_id = o.order_id
    JOIN order_items oi ON o.order_id = oi.order_id
    JOIN products p ON oi.product_id = p.product_id
    LEFT JOIN product_category_translation t ON p.product_category_name = t.product_category_name
    GROUP BY COALESCE(t.product_category_name_english, p.product_category_name, 'Unknown')
    HAVING COUNT(r.review_id) > 100
    ORDER BY avg_score DESC LIMIT 15
""")

q8 = run("""
    WITH ds AS (
        SELECT r.review_score,
            CASE WHEN o.order_delivered_customer_date::timestamp <= o.order_estimated_delivery_date::timestamp 
                 THEN 'On Time' ELSE 'Late' END AS delivery_result
        FROM orders o JOIN order_reviews r ON o.order_id = r.order_id
        WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
    )
    SELECT delivery_result, review_score, COUNT(*) AS count
    FROM ds GROUP BY delivery_result, review_score
    ORDER BY delivery_result, review_score
""")

q9 = run("""
    WITH co AS (
        SELECT c.customer_unique_id, COUNT(DISTINCT o.order_id) AS order_count
        FROM orders o JOIN customers c ON o.customer_id = c.customer_id
        WHERE o.order_status = 'delivered' GROUP BY c.customer_unique_id
    )
    SELECT CASE 
        WHEN order_count = 1 THEN 'One-time'
        WHEN order_count = 2 THEN 'Repeat (2x)'
        WHEN order_count BETWEEN 3 AND 5 THEN 'Loyal (3-5x)'
        ELSE 'Champion (6x+)'
    END AS segment, COUNT(*) AS customer_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS percentage
    FROM co GROUP BY segment ORDER BY customer_count DESC
""")

print("Data loaded! Building dashboard...")

# ── Build charts ─────────────────────────────────────────────────────
fig1 = make_subplots(specs=[[{"secondary_y": True}]])
fig1.add_trace(go.Bar(x=q1['month'], y=q1['total_revenue'],
    name='Revenue (BRL)', marker_color='#2196F3'), secondary_y=False)
fig1.add_trace(go.Scatter(x=q1['month'], y=q1['total_orders'],
    name='Orders', line=dict(color='#FF5722', width=2), mode='lines+markers'), secondary_y=True)
fig1.update_layout(title='Monthly Revenue & Order Trend', template='plotly_white', height=400)
fig1.update_yaxes(title_text="Revenue (BRL)", secondary_y=False)
fig1.update_yaxes(title_text="Orders", secondary_y=True)

fig2 = px.bar(q2.sort_values('total_revenue'), x='total_revenue', y='category',
    orientation='h', color='total_revenue', color_continuous_scale='Blues',
    title='Top 15 Categories by Revenue',
    labels={'total_revenue': 'Revenue (BRL)', 'category': ''})
fig2.update_layout(template='plotly_white', height=450, showlegend=False)

fig3 = px.bar(q3, x='state', y='total_orders', color='total_revenue',
    color_continuous_scale='Viridis', title='Top 10 States by Order Volume',
    labels={'state': 'State', 'total_orders': 'Orders'})
fig3.update_layout(template='plotly_white', height=400)

fig4 = px.scatter(q4, x='avg_delivery_days', y='late_delivery_pct',
    size='total_delivered', text='customer_state', color='late_delivery_pct',
    color_continuous_scale='Reds', title='Delivery Performance by State',
    labels={'avg_delivery_days': 'Avg Delivery Days', 'late_delivery_pct': 'Late %'})
fig4.update_traces(textposition='top center')
fig4.update_layout(template='plotly_white', height=450)

fig5 = px.pie(q5, names='payment_type', values='total_transactions',
    title='Payment Method Distribution',
    color_discrete_sequence=px.colors.qualitative.Set2)
fig5.update_traces(textposition='inside', textinfo='percent+label')
fig5.update_layout(template='plotly_white', height=400)

fig6 = px.bar(q7.sort_values('avg_score'), x='avg_score', y='category',
    orientation='h', color='avg_score', color_continuous_scale='RdYlGn',
    title='Avg Review Score by Category',
    labels={'avg_score': 'Avg Score', 'category': ''})
fig6.update_layout(template='plotly_white', height=450, showlegend=False)

fig7 = px.bar(q8, x='review_score', y='count', color='delivery_result',
    barmode='group', title='Review Scores: On Time vs Late Deliveries',
    color_discrete_map={'On Time': '#4CAF50', 'Late': '#F44336'},
    labels={'review_score': 'Score (1-5)', 'count': 'Orders'})
fig7.update_layout(template='plotly_white', height=400)

fig8 = px.pie(q9, names='segment', values='customer_count',
    title='Customer Loyalty Segments',
    color_discrete_sequence=px.colors.qualitative.Pastel)
fig8.update_traces(textposition='inside', textinfo='percent+label')
fig8.update_layout(template='plotly_white', height=400)

# ── KPI values ───────────────────────────────────────────────────────
total_revenue   = f"R$ {q1['total_revenue'].sum()/1e6:.1f}M"
total_orders    = f"{q1['total_orders'].sum():,.0f}"
avg_late_pct    = f"{q4['late_delivery_pct'].mean():.1f}%"
top_category    = q2.iloc[0]['category'].title()

# ── Dash Layout ──────────────────────────────────────────────────────
app = dash.Dash(__name__)

app.layout = html.Div([

    # Header
    html.Div([
        html.H1("Olist E-Commerce Analytics Dashboard",
            style={'color': 'white', 'margin': '0', 'fontSize': '28px'}),
        html.P("Brazilian E-Commerce | 2017–2018 | 99K+ Orders",
            style={'color': '#B0BEC5', 'margin': '4px 0 0 0'})
    ], style={'background': '#1565C0', 'padding': '24px 32px'}),

    # KPI Cards
    html.Div([
        html.Div([
            html.P("Total Revenue", style={'color': '#666', 'margin': '0', 'fontSize': '13px'}),
            html.H2(total_revenue, style={'margin': '4px 0', 'color': '#1565C0'})
        ], style={'background': 'white', 'padding': '20px 24px', 'borderRadius': '8px',
                  'boxShadow': '0 2px 8px rgba(0,0,0,0.1)', 'flex': '1'}),

        html.Div([
            html.P("Total Orders", style={'color': '#666', 'margin': '0', 'fontSize': '13px'}),
            html.H2(total_orders, style={'margin': '4px 0', 'color': '#2E7D32'})
        ], style={'background': 'white', 'padding': '20px 24px', 'borderRadius': '8px',
                  'boxShadow': '0 2px 8px rgba(0,0,0,0.1)', 'flex': '1'}),

        html.Div([
            html.P("Avg Late Delivery Rate", style={'color': '#666', 'margin': '0', 'fontSize': '13px'}),
            html.H2(avg_late_pct, style={'margin': '4px 0', 'color': '#C62828'})
        ], style={'background': 'white', 'padding': '20px 24px', 'borderRadius': '8px',
                  'boxShadow': '0 2px 8px rgba(0,0,0,0.1)', 'flex': '1'}),

        html.Div([
            html.P("Top Category", style={'color': '#666', 'margin': '0', 'fontSize': '13px'}),
            html.H2(top_category, style={'margin': '4px 0', 'color': '#E65100', 'fontSize': '18px'})
        ], style={'background': 'white', 'padding': '20px 24px', 'borderRadius': '8px',
                  'boxShadow': '0 2px 8px rgba(0,0,0,0.1)', 'flex': '1'}),

    ], style={'display': 'flex', 'gap': '16px', 'padding': '24px 32px',
              'background': '#F5F7FA'}),

    # Row 1
    html.Div([
        html.Div([dcc.Graph(figure=fig1)],
            style={'flex': '2', 'background': 'white', 'borderRadius': '8px',
                   'boxShadow': '0 2px 8px rgba(0,0,0,0.07)', 'padding': '8px'}),
        html.Div([dcc.Graph(figure=fig5)],
            style={'flex': '1', 'background': 'white', 'borderRadius': '8px',
                   'boxShadow': '0 2px 8px rgba(0,0,0,0.07)', 'padding': '8px'}),
    ], style={'display': 'flex', 'gap': '16px', 'padding': '0 32px 16px'}),

    # Row 2
    html.Div([
        html.Div([dcc.Graph(figure=fig2)],
            style={'flex': '1', 'background': 'white', 'borderRadius': '8px',
                   'boxShadow': '0 2px 8px rgba(0,0,0,0.07)', 'padding': '8px'}),
        html.Div([dcc.Graph(figure=fig3)],
            style={'flex': '1', 'background': 'white', 'borderRadius': '8px',
                   'boxShadow': '0 2px 8px rgba(0,0,0,0.07)', 'padding': '8px'}),
    ], style={'display': 'flex', 'gap': '16px', 'padding': '0 32px 16px'}),

    # Row 3
    html.Div([
        html.Div([dcc.Graph(figure=fig4)],
            style={'flex': '1', 'background': 'white', 'borderRadius': '8px',
                   'boxShadow': '0 2px 8px rgba(0,0,0,0.07)', 'padding': '8px'}),
        html.Div([dcc.Graph(figure=fig7)],
            style={'flex': '1', 'background': 'white', 'borderRadius': '8px',
                   'boxShadow': '0 2px 8px rgba(0,0,0,0.07)', 'padding': '8px'}),
    ], style={'display': 'flex', 'gap': '16px', 'padding': '0 32px 16px'}),

    # Row 4
    html.Div([
        html.Div([dcc.Graph(figure=fig6)],
            style={'flex': '1', 'background': 'white', 'borderRadius': '8px',
                   'boxShadow': '0 2px 8px rgba(0,0,0,0.07)', 'padding': '8px'}),
        html.Div([dcc.Graph(figure=fig8)],
            style={'flex': '1', 'background': 'white', 'borderRadius': '8px',
                   'boxShadow': '0 2px 8px rgba(0,0,0,0.07)', 'padding': '8px'}),
    ], style={'display': 'flex', 'gap': '16px', 'padding': '0 32px 32px'}),

    # Footer
    html.Div([
        html.P("Built by Sayali | PostgreSQL + Python + Plotly Dash | Olist Brazilian E-Commerce Dataset",
            style={'color': '#90A4AE', 'margin': '0', 'fontSize': '12px'})
    ], style={'background': '#1565C0', 'padding': '16px 32px', 'textAlign': 'center'})

], style={'background': '#F5F7FA', 'minHeight': '100vh', 'fontFamily': 'Segoe UI, sans-serif'})

if __name__ == '__main__':
    print("Dashboard running at http://127.0.0.1:8050")
    app.run(debug=True)