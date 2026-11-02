import os
from contextlib import ExitStack

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
from src.data_handlers.clickhouse_handler import ClickHouseHandler
from src.data_handlers.config import (
    ClickhouseConfig,
    MongoConfig,
    PostgresConfig,
    RedisConfig,
)
from src.data_handlers.mongodb_handler import MongoHandler
from src.data_handlers.pg_handler import PostgresHandler
from src.data_handlers.redis_handler import RedisHandler

UNIQUE_USERS_NUM = int(os.getenv("UNIQUE_USERS_NUM", "1000000"))
UNIQUE_SHOPS_NUM = int(os.getenv("UNIQUE_SHOPS_NUM", "30000"))
NUM_UNIQUE_INTERACTIONS = int(os.getenv("NUM_UNIQUE_INTERACTIONS", "100000000"))

def init_databases_dataframes() -> dict[str, list[pd.DataFrame]]:
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
        "pg_ml": [
            shops_daily_completed_orders_predict_df,
            shops_daily_all_orders_predict_df,
            daily_revenue_predict_df,
        ],
        "redis": [users_cities_df, users_clusters_df],
        "mongodb": [competitors_products_price_history_df],
        "clickhouse": [
            interactions_df,
            orders_history,
            products_price_history_df,
            delivery_price_history_df,
        ],
    }

def init_databases_connections():
    """Build source handlers from environment variables."""
    return {
        "pg_main": PostgresConfig(
            host=os.getenv("POSTGRES_MAIN_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_MAIN_PORT", "5432")),
            dbname=os.getenv(
                "POSTGRES_MAIN_DB", os.getenv("POSTGRES_MAIN_USER", "postgres")
            ),
            user=os.getenv("POSTGRES_MAIN_USER", "postgres"),
            password=os.getenv("POSTGRES_MAIN_PASSWORD", "practice"),
        ),
        "pg_ml": PostgresConfig(
            host=os.getenv("POSTGRES_ML_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_ML_PORT", "5433")),
            dbname=os.getenv(
                "POSTGRES_ML_DB", os.getenv("POSTGRES_ML_USER", "postgres")
            ),
            user=os.getenv("POSTGRES_ML_USER", "postgres"),
            password=os.getenv("POSTGRES_ML_PASSWORD", "practice"),
        ),
        "clickhouse": ClickhouseConfig(
            host=os.getenv("CLICKHOUSE_HOST", "localhost"),
            port=int(os.getenv("CLICKHOUSE_HTTP_PORT", "8123")),
            username=os.getenv("CLICKHOUSE_USER", "default"),
            password=os.getenv("CLICKHOUSE_PASSWORD", "practice"),
            database=os.getenv("CLICKHOUSE_DATABASE", "default"),
        ),
        "mongodb": MongoConfig(
            host=os.getenv("MONGO_HOST", "localhost"),
            port=int(os.getenv("MONGO_PORT", "27017")),
            username=os.getenv("MONGO_USER", "root"),
            password=os.getenv("MONGO_PASSWORD", "practice"),
            database=os.getenv("MONGO_DATABASE", "shop"),
        ),
        "redis": RedisConfig(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD", "practice"),
        ),
    }

def load_data_to_databases():
    databases_dfs = init_databases_dataframes()
    configs = init_databases_connections()

    with ExitStack() as stack:
        handlers = {
            "pg_main": stack.enter_context(PostgresHandler(configs["pg_main"])),
            "pg_ml": stack.enter_context(PostgresHandler(configs["pg_ml"])),
            "clickhouse": stack.enter_context(
                ClickHouseHandler(configs["clickhouse"])
            ),
            "mongodb": stack.enter_context(MongoHandler(configs["mongodb"])),
            "redis": stack.enter_context(RedisHandler(configs["redis"])),
        }

        for table_name, dataframe in zip(
            ("products", "shops", "users"), databases_dfs["pg_main"], strict=True
        ):
            handlers["pg_main"].load_dataframe(
                dataframe, table_name, mode="replace"
            )

        for table_name, dataframe in zip(
            (
                "shops_daily_completed_orders_predict",
                "shops_daily_all_orders_predict",
                "daily_revenue_predict",
            ),
            databases_dfs["pg_ml"],
            strict=True,
        ):
            handlers["pg_ml"].load_dataframe(
                dataframe, table_name, mode="replace"
            )

        clickhouse = handlers["clickhouse"]
        clickhouse.create_database(configs["clickhouse"].database)
        for table_name, dataframe in zip(
            (
                "interactions",
                "orders_history",
                "products_price_history",
                "delivery_price_history",
            ),
            databases_dfs["clickhouse"],
            strict=True,
        ):
            clickhouse.create_table_from_dataframe(dataframe, table_name)
            clickhouse.load_dataframe(dataframe, table_name, mode="replace")

        handlers["mongodb"].load_dataframe(
            databases_dfs["mongodb"][0],
            "competitors_products_price_history",
            mode="replace",
            index_fields=[[('product_id', 1), ('datetime', 1)]],
        )

        redis = handlers["redis"]
        redis.delete_keys_matching("users_cities:*")
        redis.load_dataframe_as_hashes(
            databases_dfs["redis"][0],
            key_template="users_cities:{user_id}",
            key_fields=["user_id"],
            value_fields=["city"],
        )
        redis.delete_keys_matching("users_clusters:*")
        redis.load_dataframe_as_hashes(
            databases_dfs["redis"][1],
            key_template="users_clusters:{user_id}",
            key_fields=["user_id"],
            value_fields=["price_cluster"],
        )

if __name__ == "__main__":
    load_data_to_databases()
