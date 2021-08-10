# sc_perfect_trade.py

import logging
import configparser
from enum import Enum
from sc_order import Order


class PerfectTradeStatus(Enum):
    NEW = 1
    BUY_TRADED = 2
    SELL_TRADED = 3
    COMPLETED = 4


class PerfectTrade:
    def __init__(self,
                 pt_id: str,
                 buy_order: Order,
                 sell_order: Order,
                 pt_type='NORMAL'
                 ):
        self.pt_id = pt_id
        self.buy_order = buy_order
        self.sell_order = sell_order
        self.pt_type = pt_type

        self.status = PerfectTradeStatus.NEW

    def order_traded(self, order: Order):
        raise Exception("not implemented")
        pass

    def get_actual_profit(self, cmp:float) -> float:
        # get parameters needed from config.ini
        config = configparser.ConfigParser()
        config.read('config.ini')
        quantity = float(config['PT_CREATION']['quantity'])
        fee = float(config['PT_CREATION']['fee'])

        if self.status == PerfectTradeStatus.NEW:
            return 0

        # return the value considering that the pending trade is done at the actual cmp
        elif self.status == PerfectTradeStatus.BUY_TRADED:
            buy_value = self.buy_order.get_total()
            sell_value = round(self.sell_order.get_amount() * cmp, 2)
            commission = (buy_value + sell_value) * fee
            return round(sell_value - buy_value - commission, 2)

        # return the value considering that the pending trade is done at the actual cmp
        elif self.status == PerfectTradeStatus.SELL_TRADED:
            sell_value = self.sell_order.get_total()
            buy_value = round(self.buy_order.get_amount() * cmp, 2)
            commission = (buy_value + sell_value) * fee
            return round(sell_value - buy_value - commission, 2)

        elif self.status == PerfectTradeStatus.COMPLETED:
            # this a theoretical value, the actual value might be calculated
            buy_value = self.buy_order.get_total()
            sell_value = self.sell_order.get_total()
            commission = (buy_value + sell_value) * fee
            return round(sell_value - buy_value - commission, 2)
        else:
            # log error
            pass



