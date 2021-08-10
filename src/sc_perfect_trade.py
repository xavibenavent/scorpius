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
                 # buy_order: Order,
                 # sell_order: Order,
                 pt_type='NORMAL'
                 ):
        self.pt_id = pt_id
        self.orders: List[Order] = orders
        # self.buy_order = buy_order
        # self.sell_order = sell_order
        self.pt_type = pt_type

        self.status = PerfectTradeStatus.NEW

    def get_actual_profit(self, cmp:float) -> float:
        pt_profit = 0
        # # get parameters needed from config.ini
        # config = configparser.ConfigParser()
        # config.read('config.ini')
        # quantity = float(config['PT_CREATION']['quantity'])
        # fee = float(config['PT_CREATION']['fee'])

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


        # # return the value considering that the pending trade is done at the actual cmp
        # elif self.status == PerfectTradeStatus.BUY_TRADED:
        #     buy_value = self.buy_order.get_total()
        #     sell_value = round(self.sell_order.get_amount() * cmp, 2)
        #     commission = (buy_value + sell_value) * fee
        #     return round(sell_value - buy_value - commission, 2)
        #
        # # return the value considering that the pending trade is done at the actual cmp
        # elif self.status == PerfectTradeStatus.SELL_TRADED:
        #     sell_value = self.sell_order.get_total()
        #     buy_value = round(self.buy_order.get_amount() * cmp, 2)
        #     commission = (buy_value + sell_value) * fee
        #     return round(sell_value - buy_value - commission, 2)
        #
        # elif self.status == PerfectTradeStatus.COMPLETED:
        #     # # this a theoretical value, the actual value might be calculated
        #     # buy_value = self.buy_order.get_total()
        #     # sell_value = self.sell_order.get_total()
        #     # commission = (buy_value + sell_value) * fee
        #     # return round(sell_value - buy_value - commission, 2)
        #     for order in self.orders:
        #         pt_profit += order.get_virtual_profit_with_cost()
        #     return pt_profit



