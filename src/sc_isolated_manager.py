# sc_isolated_manager.py

from typing import List
import logging
from binance import enums as k_binance
from sc_order import Order

log = logging.getLogger('log')


class IsolatedOrdersManager:
    def __init__(self):
        self.isolated_orders: List[Order] = []

    def check_isolated_orders(self, uid: str, order_price: float) -> (float, float):
        # check if an order from previous sessions have been traded,
        # returning the variation in global profit or zero

        # return values
        consolidated = 0.0
        expected = 0.0

        for order in self.isolated_orders:
            if order.uid == uid:
                log.info(f'traded order from previous sessions {order}')

                # assess whether the actual profit is higher or lower than the expected
                qty = order.get_amount()
                # todo: fix it
                # the total to remove must be from the order and its sibling
                expected = abs(order.price - order.sibling_order.price) * qty
                consolidated = 0.0
                diff = abs(order.price - order_price) * qty

                if order.k_side == k_binance.SIDE_BUY:
                    if order.price < order_price:
                        # bought at a lower price (GOOD)
                        consolidated = expected + diff
                    else:
                        # BAD
                        consolidated = expected - diff

                elif order.k_side == k_binance.SIDE_SELL:
                    if order.price > order_price:
                        # sold at a higher price (GOOD)
                        consolidated = expected + diff
                    else:
                        # BAD
                        consolidated = expected - diff

                # update global profit values
                log.info(f'total to add to consolidate: {consolidated:,.2f}')
                log.info(f'total to add to expected: {expected:,.2f}')

                # remove order from list
                [print(order) for order in self.isolated_orders]
                self.isolated_orders.remove(order)

                break

        return consolidated, expected
