# sc_isolated_manager.py

from typing import List
import logging
from binance import enums as k_binance
from sc_order import Order

log = logging.getLogger('log')


class IsolatedOrdersManager:
    def __init__(self):
        self.isolated_orders: List[Order] = []

    def check_isolated_orders(self, uid: str, traded_price: float) -> (float, float):
        # check if an order from previous sessions have been traded,
        # returning the variation in global profit or zero

        # return values
        is_known_order = False
        consolidated = 0.0
        expected = 0.0

        for order in self.isolated_orders:
            if order.uid == uid:
                log.info(f'traded order from previous sessions {order}')

                is_known_order = True
                original_price = order.price

                # assess whether the actual profit is higher or lower than the expected
                qty = order.get_amount()
                # expected is the neb
                expected = order.pt.get_original_expected_profit()
                consolidated = 0.0
                # difference between original price and actual traded price
                diff = abs(original_price - traded_price) * qty

                if order.k_side == k_binance.SIDE_BUY:
                    if order.price > traded_price:
                        # bought at a lower price (GOOD)
                        consolidated = expected + diff
                    else:
                        # BAD
                        consolidated = expected - diff

                elif order.k_side == k_binance.SIDE_SELL:
                    if order.price < traded_price:
                        # sold at a higher price (GOOD)
                        consolidated = expected + diff
                    else:
                        # BAD
                        consolidated = expected - diff

                # update global profit values
                log.info(f'total to add to consolidate: {consolidated:,.2f}')
                log.info(f'total to add to expected: {expected:,.2f}')

                # remove order from list
                self.isolated_orders.remove(order)

                break

        return is_known_order, consolidated, expected

    def get_expected_profit_at_cmp(self, cmp: float) -> float:
        return sum([order.pt.get_actual_profit_at_cmp(cmp=cmp) for order in self.isolated_orders])