# sc_perfect_trade.py

import logging
import configparser
from enum import Enum
from sc_order import Order, OrderStatus
from typing import List


class PerfectTradeStatus(Enum):
    NEW = 1
    BUY_TRADED = 2
    SELL_TRADED = 3
    COMPLETED = 4


class PerfectTrade:
    def __init__(self,
                 pt_id: str,
                 orders: List[Order],
                 pt_type='NORMAL'
                 ):
        self.pt_id = pt_id
        self.orders: List[Order] = orders
        self.pt_type = pt_type

        self.status = PerfectTradeStatus.NEW

    def get_actual_profit(self, cmp:float) -> float:
        pt_profit = 0

        if self.status == PerfectTradeStatus.NEW:
            return 0

        if self.status in [PerfectTradeStatus.BUY_TRADED, PerfectTradeStatus.SELL_TRADED, PerfectTradeStatus.COMPLETED]:
            for order in self.orders:
                if order.status in [OrderStatus.MONITOR, OrderStatus.ACTIVE, OrderStatus.TO_BE_TRADED]:
                    # return the value as traded at current cmp
                    pt_profit += order.get_virtual_profit_with_cost(cmp=cmp)
                elif order.status == OrderStatus.TRADED:
                    # return the value at the price traded
                    pt_profit += order.get_virtual_profit_with_cost()
                elif order.status == OrderStatus.CANCELED:
                    # does nothing
                    pass

        return pt_profit



