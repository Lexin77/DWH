# Карта исходных таблиц

Этот документ описывает датафреймы, создаваемые в `scripts/init_raw_data.py`, и структуры, в которые они загружаются. Для SQL-источников используются таблицы в схеме `public` (PostgreSQL) и базе, заданной в конфигурации ClickHouse. В MongoDB используются коллекции, в Redis — HASH-ключи.

Типы приведены по данным генераторов и текущей логике хендлеров. PostgreSQL-хендлер сохраняет UUID в виде `TEXT`; ClickHouse-хендлер сохраняет UUID как `String`. Даты Python `date` попадают в PostgreSQL как `DATE`; даты-время сериализуются как временные метки с часовым поясом. В ClickHouse даты-время создаются как `DateTime64(6, 'UTC')`. Nullable-колонки в ClickHouse оборачиваются в `Nullable(...)`.

## PostgreSQL: основная база

| Таблица / DataFrame | Колонка | Тип в источнике | Null |
|---|---|---|---|
| `products` / `products_df` | `product_id` | BIGINT | нет |
| | `category` | TEXT | нет |
| | `product_name` | TEXT | нет |
| | `prime_cost` | BIGINT | нет |
| `shops` / `shops_df` | `shop_id` | TEXT (128-bit UUID integer) | нет |
| | `city` | TEXT | нет |
| | `timezone` | TEXT | нет |
| | `is_only_picking` | BOOLEAN | нет |
| | `is_removed` | BOOLEAN | нет |
| | `open_date` | DATE | нет |
| | `closing_date` | DATE | да |
| `users` / `users_df` | `user_id` | TEXT (UUID) | нет |
| | `gender` | TEXT | нет |
| | `birthday` | DATE | нет |
| | `registration_date` | TIMESTAMP WITH TIME ZONE | нет |

## PostgreSQL: ML-база

| Таблица / DataFrame | Колонка | Тип в источнике | Null |
|---|---|---|---|
| `shops_daily_completed_orders_predict` / `shops_daily_completed_orders_predict_df` | `shop_id` | TEXT (128-bit UUID integer) | нет |
| | `forecast_date` | TIMESTAMP WITH TIME ZONE | нет |
| | `predict_orders` | BIGINT | нет |
| | `creation_date` | DATE | нет |
| `shops_daily_all_orders_predict` / `shops_daily_all_orders_predict_df` | `shop_id` | TEXT (128-bit UUID integer) | нет |
| | `forecast_date` | TIMESTAMP WITH TIME ZONE | нет |
| | `predict_orders` | BIGINT | нет |
| | `creation_date` | DATE | нет |
| `daily_revenue_predict` / `daily_revenue_predict_df` | `forecast_date` | TIMESTAMP WITH TIME ZONE | нет |
| | `predict_revenue` | BIGINT | нет |
| | `creation_date` | DATE | нет |
| | `model_name` | TEXT | нет |

## ClickHouse

| Таблица / DataFrame | Колонка | Тип в источнике | Null |
|---|---|---|---|
| `interactions` / `interactions_df` | `interaction_id` | Int64 | нет |
| | `user_id` | Int64 | нет |
| | `product_id` | Int64 | нет |
| | `datetime` | DateTime64(6, 'UTC') | нет |
| | `interaction_type` | String | нет |
| | `order_id` | Nullable(String, UUID) | да |
| `orders_history` / `orders_history` | `user_id` | Int64 | нет |
| | `product_id` | Int64 | нет |
| | `datetime` | DateTime64(6, 'UTC') | нет |
| | `order_id` | String (UUID) | нет |
| | `stage` | String | нет |
| | `shop_id` | String (UUID) | нет |
| `products_price_history` / `products_price_history_df` | `product_id` | Int64 | нет |
| | `effective_from` | DateTime64(6, 'UTC') | нет |
| | `price` | Int64 | нет |
| `delivery_price_history` / `delivery_price_history_df` | `object_id` | String (магазин UUID или город) | нет |
| | `object_type` | String | нет |
| | `effective_from` | DateTime64(6, 'UTC') | нет |
| | `price` | Int64 | нет |

## MongoDB

Коллекция: `competitors_products_price_history` (из `competitors_products_price_history_df`). MongoDB добавляет служебное поле `_id` типа ObjectId; остальные поля:

| Поле | Тип | Null |
|---|---|---|
| `parse_id` | String (UUID) | нет |
| `product_id` | Int64 | нет |
| `company_name` | String | нет |
| `datetime` | Date | нет |
| `price` | Number | да |
| `cost` | Number | да |
| `value` | Number | да |

## Redis

Каждая строка датафрейма хранится как HASH. Значения сериализуются в строки; UUID используется в ключе в текстовом представлении.

| Логическая таблица / DataFrame | Шаблон ключа | Поле ключа | Поля HASH |
|---|---|---|---|
| `users_cities` / `users_cities_df` | `users_cities:{user_id}` | `user_id` (UUID) | `city` (String) |
| `users_clusters` / `users_clusters_df` | `users_clusters:{user_id}` | `user_id` (UUID) | `price_cluster` (String) |

## Примечания к схемам

- Фактический DataFrame истории заказов содержит `shop_id`, хотя эта колонка не перечислена в описании таблицы Orders History в README.
- Фактический DataFrame цен конкурентов содержит `company_name`, хотя эта колонка не перечислена в описании таблицы Competitors Products Price History в README.
- В DataFrame интеракций `order_id` пуст для кликов и добавлений в корзину, поэтому в ClickHouse колонка должна допускать `NULL`.
- `forecast_date` в прогнозах строится через pandas `date_range` и имеет datetime dtype; PostgreSQL-хендлер приводит такие колонки к UTC и сохраняет как `TIMESTAMP WITH TIME ZONE`. `creation_date` создаётся как Python `date` и сохраняется как `DATE`.
- Таблицы ClickHouse следует создавать по типам значений и семантике DataFrame. Сейчас `create_table_from_dataframe` распознаёт только колонки pandas с datetime dtype; даты-время, полученные через `explode`, могут иметь object dtype и ошибочно выводиться как `String`. Перед использованием этого метода нужно исправить вывод типов или задать DDL явно. Таблицы PostgreSQL можно создавать через `load_dataframe` с `if_exists='replace'`. MongoDB создаёт коллекцию при первой записи; Redis не требует предварительного создания ключей.
