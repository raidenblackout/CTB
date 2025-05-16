# Crypto_Trading_Bot/agent/strategies/__init__.py
"""
Trading strategies module.
Contains the base strategy class and sub-packages for different types of strategies.
"""
from .base_strategy import BaseStrategy
from .rule_based.moving_average_crossover import  MovingAverageCrossoverStrategy# Example direct import

__all__ = [
    "BaseStrategy",
    "MovingAverageCrossoverStrategy",
]