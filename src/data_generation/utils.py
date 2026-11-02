from datetime import datetime, timedelta
from random import randrange

import numpy as np


def normal_distribution_sequence(low: int, high: int, size: int) -> list:
    normal = np.random.normal(loc=0, scale=1, size=size)
    normal = normal.clip(-3, 3)
    scaling_factor = (high - low) / 6
    normal_scaled = normal * scaling_factor
    normal_scaled += low + (high - low) / 2
    return np.int_(np.round(normal_scaled)).tolist()


def random_datetime(start: datetime, end: datetime) -> datetime:
    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    random_second = randrange(int_delta)
    return start + timedelta(seconds=random_second)


def random_datetimes(
    start: datetime,
    end: datetime,
    size: int,
) -> np.ndarray:
    rng = np.random.default_rng()

    end_ns = np.datetime64(end, "ns")
    start_ns = start.astype("datetime64[ns]")

    span_ns = (end_ns - start_ns).astype("int64")
    span_ns = np.maximum(span_ns, 0)

    offsets_ns = (rng.random(size) * span_ns).astype("timedelta64[ns]")
    return start_ns + offsets_ns


def add_random_timedelta(
    dt: np.ndarray,
    max_days: int = 0,
    max_hours: int = 0,
    max_minutes: int = 0,
    max_seconds: int = 0,
) -> np.ndarray:
    rng = np.random.default_rng()

    days = rng.integers(0, max_days + 1, size=len(dt))
    hours = rng.integers(0, max_hours + 1, size=len(dt))
    minutes = rng.integers(0, max_minutes + 1, size=len(dt))
    seconds = rng.integers(0, max_seconds + 1, size=len(dt))

    delta = (
        days.astype("timedelta64[D]")
        + hours.astype("timedelta64[h]")
        + minutes.astype("timedelta64[m]")
        + seconds.astype("timedelta64[s]")
    )
    return dt + delta
