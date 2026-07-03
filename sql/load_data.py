import os
import pandas as pd
from sqlalchemy import create_engine

# Replace the values below with your actual PostgreSQL password
DB_USER = "postgres"
DB_PASSWORD = "postgres123"   # ← change this to your actual password
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "olist_db"

engine = create_engine(
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

files_to_tables = [
    ("olist_customers_dataset.csv",           "customers"),
    ("olist_sellers_dataset.csv",             "sellers"),
    ("olist_products_dataset.csv",            "products"),
    ("olist_orders_dataset.csv",              "orders"),
    ("olist_order_items_dataset.csv",         "order_items"),
    ("olist_order_payments_dataset.csv",      "order_payments"),
    ("olist_order_reviews_dataset.csv",       "order_reviews"),
    ("product_category_name_translation.csv", "product_category_translation"),
]

for filename, table in files_to_tables:
    path = os.path.join("data", "raw", filename)
    print(f"Loading {filename}...")
    df = pd.read_csv(path)
    df.to_sql(table, engine, if_exists="append", index=False)
    print(f"  ✓ {len(df):,} rows loaded into '{table}'")

print("\n✅ All tables loaded successfully!")