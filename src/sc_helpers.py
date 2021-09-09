# sc_helpers.py

from typing import List, Union
from binance import enums as k_binance
from sc_order import Order


class Helpers:
    @staticmethod
    def get_side_span_from_list(orders: List[Order],
                                side: Union[k_binance.SIDE_BUY, k_binance.SIDE_SELL],
                                cmp: float) -> float:
        distances = [order.distance(cmp=cmp) for order in orders if order.k_side == side]
        return max(distances) if len(distances) > 0 else 0.0

    @staticmethod
    def get_span_from_list(orders: List[Order], cmp: float) -> (float, float):
        buy_span = Helpers.get_side_span_from_list(orders=orders, side=k_binance.SIDE_BUY, cmp=cmp)
        sell_span = Helpers.get_side_span_from_list(orders=orders, side=k_binance.SIDE_SELL, cmp=cmp)
        return buy_span, sell_span

    @staticmethod
    def get_gap_span_from_list(orders: List[Order], cmp: float, gap: float) -> (float, float):
        if gap == 0:
            return 0.0, 0.0
        else:
            buy_span, sell_span = Helpers.get_span_from_list(orders=orders, cmp=cmp)
            return (buy_span / gap), (sell_span / gap)
