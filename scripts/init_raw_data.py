import pandas as pd

from src.data_generation.clickhouse import (
    gen_delivery_price_history_dataframe,
    gen_products_price_history_dataframe,
    generate_interaction_history_dataframe,
    generate_orders_history_dataframe,
)
from src.data_generation.mongodb import gen_competitors_products_price_history_dataframe
from src.data_generation.pg_ml import (
    gen_daily_revenue_predict,
    gen_shops_daily_all_orders_predict,
    gen_shops_daily_completed_orders_predict,
)
from src.data_generation.pg_prod import (
    generate_products_dataframe,
    generate_shops_dataframe,
    generate_users_dataframe,
)
from src.data_generation.redis import (
    gen_users_cities_dataframe,
    gen_users_clusters_dataframe,
)

UNIQUE_USERS_NUM = 1000000
UNIQUE_SHOPS_NUM = 30000
NUM_UNIQUE_INTERACTIONS = 100000000

def init_databases_dataframes() -> dict[str, pd.DataFrame]:
    # PG prod
    products_df = generate_products_dataframe(pd.read_csv("data/products.csv", sep=";"))
    shops_df = generate_shops_dataframe(UNIQUE_SHOPS_NUM)
    users_df = generate_users_dataframe(UNIQUE_USERS_NUM)

    # Clickhouse
    interactions_df = generate_interaction_history_dataframe(
        products_df.copy(), users_df.copy(), NUM_UNIQUE_INTERACTIONS
    )
    orders_history = generate_orders_history_dataframe(
        interactions_df.copy(), shops_df.copy()
    )
    products_price_history_df = gen_products_price_history_dataframe(products_df.copy())
    delivery_price_history_df = gen_delivery_price_history_dataframe(shops_df.copy())

    # Mongodb
    competitors_products_price_history_df = (
        gen_competitors_products_price_history_dataframe(products_df.copy())
    )

    # PG ml
    shops_daily_completed_orders_predict_df = gen_shops_daily_completed_orders_predict(
        shops_df.copy()
    )
    shops_daily_all_orders_predict_df = gen_shops_daily_all_orders_predict(
        shops_daily_completed_orders_predict_df.copy()
    )
    daily_revenue_predict_df = gen_daily_revenue_predict()

    # Redis
    users_cities_df = gen_users_cities_dataframe(users_df.copy())
    users_clusters_df = gen_users_clusters_dataframe(users_df.copy())
    return {
        "pg_main": [products_df, shops_df, users_df],
        "pg_ml": [shops_daily_completed_orders_predict_df, shops_daily_all_orders_predict_df, daily_revenue_predict_df],
        "redis": [users_cities_df, users_clusters_df],
        "mongodb": [competitors_products_price_history_df],
        "clickhouse": [interactions_df, orders_history, products_price_history_df, delivery_price_history_df]
    }

def init_databases_connections():
    pass

def load_data_to_databases():
    pass
    

if __name__ == "__main__":
    databases_dfs = init_databases_dataframes()
