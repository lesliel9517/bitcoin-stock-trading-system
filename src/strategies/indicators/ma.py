"""Moving average indicators"""

import pandas as pd
from typing import Optional


def simple_moving_average(data: pd.Series, window: int) -> pd.Series:
    """Simple Moving Average (SMA)

    Args:
        data: Price series
        window: Window size

    Returns:
        SMA series
    """
    return data.rolling(window=window).mean()


def exponential_moving_average(data: pd.Series, window: int) -> pd.Series:
    """Exponential Moving Average (EMA)

    Args:
        data: Price series
        window: Window size

    Returns:
        EMA series
    """
    return data.ewm(span=window, adjust=False).mean()


def weighted_moving_average(data: pd.Series, window: int) -> pd.Series:
    """Weighted Moving Average (WMA)

    Args:
        data: Price series
        window: Window size

    Returns:
        WMA series
    """
    weights = pd.Series(range(1, window + 1))

    def wma(x):
        return (x * weights).sum() / weights.sum()

    return data.rolling(window=window).apply(wma, raw=False)


def calculate_ma_cross(
    data: pd.DataFrame,
    short_window: int = 5,
    long_window: int = 20,
    ma_type: str = "SMA"
) -> pd.DataFrame:
    """Calculate moving average crossover indicators

    Args:
        data: OHLCV data
        short_window: Short-term MA window
        long_window: Long-term MA window
        ma_type: MA type (SMA, EMA, WMA)

    Returns:
        Data with moving averages and signals
    """
    df = data.copy()

    # Select MA type
    if ma_type == "EMA":
        ma_func = exponential_moving_average
    elif ma_type == "WMA":
        ma_func = weighted_moving_average
    else:
        ma_func = simple_moving_average

    # Calculate moving averages
    df['ma_short'] = ma_func(df['close'], short_window)
    df['ma_long'] = ma_func(df['close'], long_window)

    # Calculate crossover signals
    df['ma_diff'] = df['ma_short'] - df['ma_long']
    df['ma_diff_prev'] = df['ma_diff'].shift(1)

    # Golden cross: short MA crosses above long MA
    df['golden_cross'] = (df['ma_diff'] > 0) & (df['ma_diff_prev'] <= 0)

    # Death cross: short MA crosses below long MA
    df['death_cross'] = (df['ma_diff'] < 0) & (df['ma_diff_prev'] >= 0)

    return df
