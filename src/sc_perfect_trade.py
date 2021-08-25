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
        # this is the neb (original)
        self._original_expected_profit = \
            sum([order.get_signed_total_at_cmp(cmp=order.price, with_commission=True)
                 for order in self.orders])

    def get_actual_profit_at_cmp(self, cmp:float) -> float:
        # return the pt profit considering that all remaining orders, except NEW, are traded at current cmp
        pt_profit = 0.0

        if self.status == PerfectTradeStatus.NEW:
            return 0.0

        if self.status in [PerfectTradeStatus.BUY_TRADED, PerfectTradeStatus.SELL_TRADED, PerfectTradeStatus.COMPLETED]:
            for order in self.orders:

                if order.status.name in ['MONITOR', 'ACTIVE', 'TO_BE_TRADED']:
                # if order.status in [OrderStatus.MONITOR, OrderStatus.ACTIVE, OrderStatus.TO_BE_TRADED]:
                    # return the value as traded at current cmp
                    pt_profit += order.get_signed_total_at_cmp(cmp=cmp, with_commission=True)

                elif order.status.name == 'TRADED':
                # elif order.status == OrderStatus.TRADED:
                    # return the value at the price traded
                    pt_profit += order.get_signed_total_at_cmp(cmp=order.price, with_commission=True)

        return pt_profit

    def get_original_expected_profit(self) -> float:
        # it does not depend on the actual status
        return self._original_expected_profit

    def get_consolidated_profit(self) -> float:
        # not all traded orders, only those in completed pt
        if self.status == PerfectTradeStatus.COMPLETED:
            return sum([order.get_signed_total_at_cmp(cmp=order.price, with_commission=True)
                        for order in self.orders])
        return 0.0




