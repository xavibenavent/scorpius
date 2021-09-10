# sc_helpers.py

import logging
from typing import List, Union
from binance import enums as k_binance
from sc_order import Order, OrderStatus
from sc_pt_manager import PTManager
from sc_market_api_out import MarketAPIOut

log = logging.getLogger('log')


class Helpers:
    def __init__(self, pt_manager: PTManager, market: MarketAPIOut):
        self.ptm = pt_manager
        self.market = market

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

    @staticmethod
    def get_side_depth_from_list(orders: List[Order],
                                 side: Union[k_binance.SIDE_BUY, k_binance.SIDE_SELL],
                                 cmp: float) -> float:
        distances = [order.distance(cmp=cmp) for order in orders if order.k_side == side]
        return min(distances) if len(distances) > 0 else 0.0

    @staticmethod
    def get_depth_from_list(orders: List[Order], cmp: float) -> (float, float):
        buy_depth = Helpers.get_side_depth_from_list(orders=orders, side=k_binance.SIDE_BUY, cmp=cmp)
        sell_depth = Helpers.get_side_depth_from_list(orders=orders, side=k_binance.SIDE_SELL, cmp=cmp)
        return buy_depth, sell_depth

    @staticmethod
    def get_gap_depth_from_list(orders: List[Order], cmp: float, gap: float) -> (float, float):
        if gap == 0:
            return 0.0, 0.0
        else:
            buy_depth, sell_depth = Helpers.get_depth_from_list(orders=orders, cmp=cmp)
            return (buy_depth / gap), (sell_depth / gap)

    @staticmethod
    def get_side_momentum_from_list(orders: List[Order],
                                    side: Union[k_binance.SIDE_BUY, k_binance.SIDE_SELL],
                                    cmp: float) \
            -> float:
        distances = [order.distance(cmp=cmp) for order in orders if order.k_side == side]
        return sum(distances) if len(distances) > 0 else 0.0

    @staticmethod
    def get_momentum_from_list(orders: List[Order], cmp: float) -> (float, float):
        buy_mtm = Helpers.get_side_momentum_from_list(orders=orders, side=k_binance.SIDE_BUY, cmp=cmp)
        sell_mtm = Helpers.get_side_momentum_from_list(orders=orders, side=k_binance.SIDE_SELL, cmp=cmp)
        return buy_mtm, sell_mtm

    @staticmethod
    def get_gap_momentum_from_list(orders: List[Order], cmp: float, gap: float) -> (float, float):
        if gap == 0:
            return 0.0, 0.0
        else:
            buy_mtm, sell_mtm = Helpers.get_momentum_from_list(orders=orders, cmp=cmp)
            return (buy_mtm / gap), (sell_mtm / gap)

    def place_market_order(self, order) -> None:
        # raise an exception if the order is not placed in binance (probably due to not enough liquidity)
        # change order status (it will be update to TRADED once received through binance socket)
        order.set_status(OrderStatus.TO_BE_TRADED)
        # place order and check message received
        msg = self.market.place_market_order(order=order)
        if msg:
            order.set_binance_id(new_id=msg.get('binance_id'))
            log.info(f'********** MARKET ORDER PLACED ********** {order}')  # msg: {msg}')
        else:
            log.critical(f'market order not place in binance {order}')
            raise Exception("MARKET order not placed")

    def place_limit_order(self, order: Order) -> None:
        order.set_status(status=OrderStatus.TO_BE_TRADED)
        # place order
        msg = self.market.place_limit_order(order=order)
        if msg:
            order.set_binance_id(new_id=msg.get('binance_id'))
            log.debug(f'********** LIMIT ORDER PLACED ********** {order}')  # msg: {msg}')
        else:
            log.critical(f'error placing order {order}')
            raise Exception("LIMIT order not placed")

