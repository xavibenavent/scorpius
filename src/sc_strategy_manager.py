# sc_strategy_manager.py

from typing import List, Union
from binance import enums as k_binance
from sc_order import Order


class StrategyManager:
    def __init__(self, gap: float):
        self.gap = gap
