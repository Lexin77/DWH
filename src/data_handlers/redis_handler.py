from __future__ import annotations

import json
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import numpy as np
import pandas as pd
import redis

from src.data_handlers.config import RedisConfig

logger = logging.getLogger(__name__)


class RedisHandler:
    def __init__(
        self,
        config: RedisConfig,
        decode_responses: bool = True,
    ) -> None:
        self.config = config
        self.decode_responses = decode_responses
        self._client: redis.Redis | None = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                username=self.config.username,
                password=self.config.password,
                ssl=self.config.ssl,
                decode_responses=self.decode_responses,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
            )

        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> RedisHandler:
        self.client.ping()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def flush_database(self) -> None:
        self.client.flushdb()

    def load_dataframe_as_hashes(
        self,
        df: pd.DataFrame,
        key_template: str,
        key_fields: list[str],
        value_fields: list[str] | None = None,
        ttl_seconds: int | None = None,
        batch_size: int = 5_000,
    ) -> int:
        if df.empty:
            logger.warning("DataFrame пустой; запись в Redis пропущена.")
            return 0

        if not all(field in df.columns for field in key_fields):
            missing = set(key_fields) - set(df.columns)
            raise ValueError(f"Отсутствуют key_fields в DataFrame: {missing}")

        fields = value_fields or [
            column for column in df.columns if column not in key_fields
        ]

        if not all(field in df.columns for field in fields):
            missing = set(fields) - set(df.columns)
            raise ValueError(f"Отсутствуют value_fields в DataFrame: {missing}")

        prepared_df = self._prepare_dataframe(df)
        written = 0

        for start in range(0, len(prepared_df), batch_size):
            batch = prepared_df.iloc[start : start + batch_size]
            pipe = self.client.pipeline(transaction=False)

            for row in batch.itertuples(index=False):
                row_dict = dict(zip(prepared_df.columns, row))
                key = key_template.format(
                    **{field: row_dict[field] for field in key_fields}
                )

                mapping = {
                    field: self._serialize_value(row_dict[field]) for field in fields
                }

                pipe.hset(key, mapping=mapping)

                if ttl_seconds is not None:
                    pipe.expire(key, ttl_seconds)

            pipe.execute()
            written += len(batch)

        logger.info("Записано %d HASH-ключей по шаблону %s", written, key_template)
        return written

    def load_dataframe_as_json(
        self,
        df: pd.DataFrame,
        key_template: str,
        key_fields: list[str],
        ttl_seconds: int | None = None,
        batch_size: int = 5_000,
    ) -> int:
        if df.empty:
            logger.warning("DataFrame пустой; запись в Redis пропущена.")
            return 0

        prepared_df = self._prepare_dataframe(df)
        written = 0

        for start in range(0, len(prepared_df), batch_size):
            batch = prepared_df.iloc[start : start + batch_size]
            pipe = self.client.pipeline(transaction=False)

            for row in batch.itertuples(index=False):
                row_dict = dict(zip(prepared_df.columns, row))
                key = key_template.format(
                    **{field: row_dict[field] for field in key_fields}
                )

                document = {
                    column: self._json_safe(value) for column, value in row_dict.items()
                }

                pipe.json().set(key, "$", document)

                if ttl_seconds is not None:
                    pipe.expire(key, ttl_seconds)

            pipe.execute()
            written += len(batch)

        logger.info("Записано %d JSON-ключей по шаблону %s", written, key_template)
        return written

    def load_dataframe_as_sorted_set(
        self,
        df: pd.DataFrame,
        key_template: str,
        member_field: str,
        score_field: str,
        key_fields: list[str],
        ttl_seconds: int | None = None,
        batch_size: int = 5_000,
    ) -> int:
        required = set(key_fields + [member_field, score_field])

        if not required.issubset(df.columns):
            missing = required - set(df.columns)
            raise ValueError(f"Отсутствуют колонки в DataFrame: {missing}")

        prepared_df = self._prepare_dataframe(df)
        written = 0

        for start in range(0, len(prepared_df), batch_size):
            batch = prepared_df.iloc[start : start + batch_size]
            pipe = self.client.pipeline(transaction=False)

            for row in batch.itertuples(index=False):
                row_dict = dict(zip(prepared_df.columns, row))
                key = key_template.format(
                    **{field: row_dict[field] for field in key_fields}
                )

                member = self._serialize_value(row_dict[member_field])
                score = float(row_dict[score_field])

                pipe.zadd(key, {member: score})

                if ttl_seconds is not None:
                    pipe.expire(key, ttl_seconds)

            pipe.execute()
            written += len(batch)

        logger.info("Записано %d элементов ZSET по шаблону %s", written, key_template)
        return written

    def load_dataframe_as_stream(
        self,
        df: pd.DataFrame,
        stream_key: str,
        max_length: int | None = 100_000,
        approximate: bool = True,
        batch_size: int = 5_000,
    ) -> int:
        if df.empty:
            logger.warning("DataFrame пустой; запись в Stream пропущена.")
            return 0

        prepared_df = self._prepare_dataframe(df)
        written = 0

        for start in range(0, len(prepared_df), batch_size):
            batch = prepared_df.iloc[start : start + batch_size]
            pipe = self.client.pipeline(transaction=False)

            for row in batch.itertuples(index=False):
                event = {
                    column: self._serialize_value(value)
                    for column, value in zip(prepared_df.columns, row)
                }

                if max_length is None:
                    pipe.xadd(stream_key, event)
                else:
                    pipe.xadd(
                        stream_key,
                        event,
                        maxlen=max_length,
                        approximate=approximate,
                    )

            pipe.execute()
            written += len(batch)

        logger.info("Записано %d событий в Stream %s", written, stream_key)
        return written

    def read_hashes_to_dataframe(
        self,
        key_pattern: str,
        count: int = 10_000,
    ) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []

        for key in self.client.scan_iter(match=key_pattern, count=count):
            value = self.client.hgetall(key)
            rows.append({"_redis_key": key, **value})

        return pd.DataFrame(rows)

    def read_json_to_dataframe(
        self,
        key_pattern: str,
        count: int = 10_000,
    ) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []

        for key in self.client.scan_iter(match=key_pattern, count=count):
            document = self.client.json().get(key)
            rows.append({"_redis_key": key, **document})

        return pd.DataFrame(rows)

    @staticmethod
    def _prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()

        for column in result.columns:
            if pd.api.types.is_datetime64_any_dtype(result[column]):
                result[column] = pd.to_datetime(result[column], utc=True)

            elif pd.api.types.is_bool_dtype(result[column]):
                result[column] = result[column].astype("boolean")

            elif pd.api.types.is_object_dtype(result[column]):
                result[column] = result[column].where(result[column].notna(), None)

        return result.replace({np.nan: None})

    @staticmethod
    def _serialize_value(value: Any) -> str | None:
        if value is None or pd.isna(value):
            return None

        if isinstance(value, (datetime, pd.Timestamp)):
            return value.isoformat()

        if isinstance(value, date):
            return value.isoformat()

        if isinstance(value, (UUID,)):
            return str(value)

        if isinstance(value, Decimal):
            return str(value)

        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value, ensure_ascii=False, default=str)

        return str(value)

    @staticmethod
    def _json_safe(value: Any) -> Any:
        if value is None or pd.isna(value):
            return None

        if isinstance(value, (datetime, pd.Timestamp, date)):
            return value.isoformat()

        if isinstance(value, (UUID, Decimal)):
            return str(value)

        if isinstance(value, np.generic):
            return value.item()

        if isinstance(value, dict):
            return {key: RedisHandler._json_safe(item) for key, item in value.items()}

        if isinstance(value, (list, tuple, set)):
            return [RedisHandler._json_safe(item) for item in value]

        return value
