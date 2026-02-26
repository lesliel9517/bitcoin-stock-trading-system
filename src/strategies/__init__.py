"""Strategies module"""

from .base import Strategy
from .examples.ma_cross import MACrossStrategy

__all__ = [
    "Strategy",
    "MACrossStrategy",
]
