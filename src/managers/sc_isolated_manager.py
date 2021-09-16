# sc_isolated_manager.py

from typing import List, Optional
import logging
from binance import enums as k_binance
from basics.sc_order import Order
from basics.sc_asset import Asset

log = logging.getLogger('log')


class IsolatedOrdersManager:
    def __init__(self):
        self.isolated_orders: List[Order] = []
        self.previous_runs_orders: List[Order] = []

    def check_previous_runs_orders(self, uid: str) -> None:
        # remove from list and, therefore, from dashboard
        print(f'check previous runs orders for uid {uid}')
        for order in self.previous_runs_orders:
            if order.uid == uid:
                self.previous_runs_orders.remove(order)

    def check_isolated_orders(self, uid: str, traded_price: float) -> (float, float):
        # check if an order from previous sessions have been traded,
        # returning the variation in global profit or zero

        # return values
        is_known_order = False
        consolidated = 0.0
        expected = 0.0

        log.info(f'checking isolated order with uid {uid}')
        log.info('********** existing isolated orders:')
        for order in self.isolated_orders:
            log.info(f'isolated order: {order} [{order.symbol.name}]')

        for order in self.isolated_orders:
            if order.uid == uid:
                log.info(f'traded isolated order from previous sessions {order}')

                is_known_order = True
                original_price = order.price

                # assess whether the actual profit is higher or lower than the expected
                qty = order.get_amount(signed=False)
                # expected is the neb
                expected = order.pt.get_original_expected_profit()
                consolidated = 0.0
                # difference between original price and actual traded price
                diff = abs(original_price - traded_price) * qty

                if order.k_side == k_binance.SIDE_BUY:
                    if original_price > traded_price:
                        # bought at a lower price (GOOD)
                        consolidated = expected + diff
                    else:
                        # BAD
                        consolidated = expected - diff

                elif order.k_side == k_binance.SIDE_SELL:
                    if original_price < traded_price:
                        # sold at a higher price (GOOD)
                        consolidated = expected + diff
                    else:
                        # BAD
                        consolidated = expected - diff

                # update global profit values
                log.info(f'total to add to consolidate: {consolidated:,.2f}')
                log.info(f'total to subtract from expected: {expected:,.2f}')

                # remove order from list
                self.isolated_orders.remove(order)

                break

        return is_known_order, consolidated, expected

    def get_expected_profit_at_cmp(self, cmp: float, symbol_name: str) -> float:
        return sum(
            [order.pt.get_actual_profit_at_cmp(cmp=cmp)
             for order in self.isolated_orders
             if order.symbol.name == symbol_name]
        )

    def try_to_get_asset_liquidity(self, asset: Asset, cmp: float, max_loss: float) -> Optional[Order]:
        # get candidate orders depending on side
        candidate_orders: List[Order] = []
        for order in self.isolated_orders:
            criteria_1 = order.k_side == k_binance.SIDE_BUY and order.symbol.base_asset().name() == asset.name()
            criteria_2 = order.k_side == k_binance.SIDE_SELL and order.symbol.quote_asset().name() == asset.name()
            if criteria_1 or criteria_2:
                candidate_orders. append(order)

        # trade one order if loss is below the threshold defined in config.ini
        if len(candidate_orders) > 0:
            for candidate_order in candidate_orders:
                # get (pt) loss taking into account the sibling order
                candidate_loss = candidate_order.get_total_at_cmp(cmp=cmp)
                sibling_loss = \
                    candidate_order.sibling_order.get_total_at_cmp(cmp=candidate_order.sibling_order.price)
                loss = candidate_loss + sibling_loss
                # check allowed limit
                if loss > max_loss:
                    log.debug(f'found a good order with loss {loss:,.2f} for getting liquidity: {candidate_order}')
                    return candidate_order
        return None

    def log(self):
        for order in self.isolated_orders:
            log.info(f'isolated order: {order}')

    def get_isolated_orders(self, symbol_name: str) -> List[Order]:
        return [order for order in self.isolated_orders if order.symbol.name == symbol_name]
