# sc_orders_manager.py

from typing import List
from binance import enums as k_binance
from basics.sc_order import Order, OrderStatus
from basics.sc_symbol import Symbol
from market.sc_market_api_out import MarketAPIOut


class OrdersManager:
    def __init__(self,
                 market_api_out: MarketAPIOut):
        self.market_api_out = market_api_out

        self.orders: List[Order] = []

    def get_consolidated(self) -> float:
        return sum([order.get_total_at_cmp(cmp=order.price)
                    for order in self.orders
                    if order.status == OrderStatus.TRADED])

    def get_consolidated_paired(self, cmp: float, qty: float) -> float:
        # the difference between buy & sell are traded at cmp
        diff = self._get_diff()
        orders_sum = sum([order.get_total_at_cmp(cmp=order.price)
                          for order in self.orders
                          if order.status == OrderStatus.TRADED])
        return orders_sum - (diff * cmp * qty)

    def _get_diff(self) -> int:
        buy_count = self.get_side_count(side=k_binance.SIDE_BUY)
        sell_count = self.get_side_count(side=k_binance.SIDE_SELL)
        return sell_count - buy_count

    def get_side_count(self, side: k_binance):
        side_count = len([order for order in self.orders
                         if order.k_side == side
                         and order.status == OrderStatus.TRADED])
        return side_count

    def get_to_be_consolidated(self) -> float:
        return sum([order.get_total_at_cmp(cmp=order.price)
                    for order in self.orders
                    if order.status in [OrderStatus.ACTIVE]])

    def get_optimistic_monitor(self) -> float:
        # profit if MONITOR orders are traded at its price
        return sum([order.get_total_at_cmp(cmp=order.price)
                    for order in self.orders
                    if order.status in [OrderStatus.MONITOR, OrderStatus.TO_BE_TRADED]])

    def get_cmp_monitor(self, cmp: float) -> float:
        # profit if MONITOR orders are traded at its price
        return sum([order.get_total_at_cmp(cmp=cmp)
                    for order in self.orders
                    if order.status in [OrderStatus.MONITOR, OrderStatus.TO_BE_TRADED]])

    def get_optimistic_canceled(self) -> float:
        # profit if MONITOR orders are traded at its price
        return sum([order.get_total_at_cmp(cmp=order.price)
                    for order in self.orders
                    if order.status in [OrderStatus.CANCELED]])

    def get_cmp_canceled(self, cmp: float) -> float:
        # profit if MONITOR orders are traded at its price
        return sum([order.get_total_at_cmp(cmp=cmp)
                    for order in self.orders
                    if order.status in [OrderStatus.CANCELED]])

    def show_orders(self):
        [print(order) for order in self.orders]