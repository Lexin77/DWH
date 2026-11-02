from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import date, datetime
from typing import Any
from uuid import UUID

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.types import (
    BIGINT,
    BOOLEAN,
    DATE,
    DOUBLE_PRECISION,
    TEXT,
    TIMESTAMP,
    Interval,
)

from src.data_handlers.config import PostgresConfig

logger = logging.getLogger(__name__)


class PostgresHandler:
    def __init__(
        self,
        config: PostgresConfig,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_pre_ping: bool = True,
        echo: bool = False,
    ) -> None:
        self.config = config
        self.engine: Engine = create_engine(
            config.build_url(),
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=pool_pre_ping,
            echo=echo,
        )

    def close(self) -> None:
        self.engine.dispose()

    def __enter__(self) -> PostgresHandler:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def table_exists(self, table_name: str, schema: str = "public") -> bool:
        inspector = inspect(self.engine)
        return inspector.has_table(table_name, schema=schema)

    def query_df(self, query: str) -> pd.DataFrame:
        with self.engine.connect() as connection:
            return pd.read_sql(text(query), connection)

    def truncate_table(self, table_name: str, schema: str = "public") -> None:
        qualified_name = f'"{schema}"."{table_name}"'

        with self.engine.begin() as connection:
            connection.execute(text(f"TRUNCATE TABLE {qualified_name}"))

    def load_dataframe(
        self,
        df: pd.DataFrame,
        table_name: str,
        schema: str = "public",
        mode: str = "append",
        chunksize: int = 10_000,
        dtype: Mapping[str, Any] | None = None,
        index: bool = False,
    ) -> int:
        if df.empty:
            logger.warning("DataFrame для %s пустой; загрузка пропущена.", table_name)
            return 0

        if mode not in {"append", "replace", "fail"}:
            raise ValueError("mode должен быть 'append', 'replace' или 'fail'")

        prepared_df = self._prepare_dataframe(df)
        inferred_dtype = dtype or self._infer_sqlalchemy_types(prepared_df)
        safe_chunksize = min(chunksize, max(1, 60_000 // max(1, len(prepared_df.columns))))

        rows_written = prepared_df.to_sql(
            name=table_name,
            con=self.engine,
            schema=schema,
            if_exists=mode,
            index=index,
            chunksize=safe_chunksize,
            dtype=inferred_dtype,
            method="multi",
        )

        logger.info(
            "Загружено %s строк в %s.%s",
            rows_written if rows_written is not None else len(prepared_df),
            schema,
            table_name,
        )

        return int(rows_written or len(prepared_df))

    def replace_preserving_schema(
        self,
        df: pd.DataFrame,
        table_name: str,
        schema: str = "public",
        chunksize: int = 10_000,
        dtype: Mapping[str, Any] | None = None,
    ) -> int:
        if not self.table_exists(table_name, schema=schema):
            raise ValueError(
                f"Таблица {schema}.{table_name} не существует; "
                "сначала создайте её миграцией или используйте load_dataframe(mode='replace')."
            )

        self.truncate_table(table_name=table_name, schema=schema)

        return self.load_dataframe(
            df=df,
            table_name=table_name,
            schema=schema,
            mode="append",
            chunksize=chunksize,
            dtype=dtype,
        )

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
                non_null = result[column].dropna()
                if not non_null.empty:
                    sample = non_null.iloc[0]
                    if isinstance(sample, (UUID, int)):
                        result[column] = result[column].map(
                            lambda v: str(v) if v is not None else None
                        )

        return result.replace({np.nan: None})

    @staticmethod
    def _infer_sqlalchemy_types(df: pd.DataFrame) -> dict[str, Any]:
        inferred: dict[str, Any] = {}

        for column in df.columns:
            series = df[column]

            if pd.api.types.is_bool_dtype(series):
                inferred[column] = BOOLEAN
            elif pd.api.types.is_datetime64_any_dtype(series):
                inferred[column] = TIMESTAMP(timezone=True)
            elif pd.api.types.is_timedelta64_dtype(series):
                inferred[column] = Interval
            elif pd.api.types.is_integer_dtype(series):
                inferred[column] = BIGINT
            elif pd.api.types.is_float_dtype(series):
                inferred[column] = DOUBLE_PRECISION
            else:
                non_null = series.dropna()
                if not non_null.empty and isinstance(non_null.iloc[0], date) and not isinstance(non_null.iloc[0], datetime):
                    inferred[column] = DATE
                else:
                    inferred[column] = TEXT

        return inferred
