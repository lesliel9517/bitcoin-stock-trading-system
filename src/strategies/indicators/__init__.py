"""Technical indicators module"""

from .ma import (
    simple_moving_average,
    exponential_moving_average,
    weighted_moving_average,
    calculate_ma_cross,
)

__all__ = [
    "simple_moving_average",
    "exponential_moving_average",
    "weighted_moving_average",
    "calculate_ma_cross",
]
