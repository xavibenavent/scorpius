# sc_helpers.py

import logging
from typing import List, Union, Callable
from enum import Enum
from binance import enums as k_binance
from sc_order import Order, OrderStatus
from sc_perfect_trade import PerfectTradeStatus
from sc_pt_manager import PTManager
from sc_market_api_out import MarketAPIOut
from sc_symbol import Symbol
from sc_isolated_manager import IsolatedOrdersManager

log = logging.getLogger('log')


class QuitMode(Enum):
    CANCEL_ALL = 1
    PLACE_ALL_PENDING = 2
    TRADE_ALL_PENDING = 3


class Helpers:
    def __init__(self,
                 pt_manager: PTManager,
                 market: MarketAPIOut,
                 session_stopped_callback: Callable[[Symbol, str, bool, float, float, int, int, int], None]
                 ):
        self.ptm = pt_manager
        self.market = market
        self._session_stopped_callback = session_stopped_callback

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

    def quit_particular_session(self,
                                quit_mode: QuitMode,
                                session_id: str,
                                symbol: Symbol,
                                cmp: float,
                                iom: IsolatedOrdersManager,
                                cmp_count: int):
        log.info(f'********** STOP {quit_mode.name} ********** [{session_id}] terminated')
        # init used variables
        is_session_fully_consolidated = False
        diff = 0
        consolidated_profit = 0.0
        expected_profit = 0.0
        placed_orders_at_order_price = 0

        if quit_mode == QuitMode.PLACE_ALL_PENDING:  # place all monitor orders
            log.info('quit placing isolated orders')
            # set session terminating status
            is_session_fully_consolidated = False

            # get consolidated: total profit considering only the COMPLETED perfect trades
            consolidated_profit += self.ptm.get_consolidated_profit()
            expected_profit += self.ptm.get_expected_profit()

            # get non completed pt
            non_completed_pt = [pt for pt in self.ptm.perfect_trades
                                if pt.status == PerfectTradeStatus.BUY_TRADED
                                or pt.status == PerfectTradeStatus.SELL_TRADED]

            # get expected profit as the profit of all non completed pt orders (by pairs)
            for pt in non_completed_pt:
                for order in pt.orders:
                    # place only MONITOR orders
                    if order.status == OrderStatus.MONITOR:
                        log.info(f'** isolated order to be appended to list: {order}')
                        iom.isolated_orders.append(order)
                        # self.placed_isolated_callback(order)
                        self.place_limit_order(order=order)

                        placed_orders_at_order_price += 1
                        # add to isolated orders list
                        log.info(f'trading LIMIT order {order}')

        elif quit_mode == QuitMode.TRADE_ALL_PENDING:  # trade diff orders at reference side (BUY or SELL)
            # set session terminating status
            is_session_fully_consolidated = True

            # get consolidated profit (expected is zero)
            consolidated_profit += self.ptm.get_total_actual_profit_at_cmp(cmp=cmp)

            # place orders
            # get MONITOR orders in non completed pt
            monitor_orders = self.ptm.get_orders_by_request(
                orders_status=[OrderStatus.MONITOR],
                pt_status=[PerfectTradeStatus.BUY_TRADED, PerfectTradeStatus.SELL_TRADED]
            )

            # get diff to know at which side to trade & set reference orders
            buy_orders = []
            sell_orders = []
            for order in monitor_orders:
                if order.k_side == k_binance.SIDE_BUY:
                    buy_orders.append(order)
                    diff += 1
                elif order.k_side == k_binance.SIDE_SELL:
                    sell_orders.append(order)
                    diff -= 1

            log.info(f'diff: {diff}')
            # trade only diff count orders at market price (cmp), at the right side
            if diff == 0:
                pass
            elif diff > 0:  # BUY SIDE
                log.info('BUY SIDE')
                for i in range(diff):
                    order = buy_orders[i]
                    self.place_market_order(order=order)
                    log.info(f'trading reference market order {order}')
            elif diff < 0:  # SELL SIDE
                log.info('SELL SIDE')
                for i in range(-diff):
                    order = sell_orders[i]
                    self.place_market_order(order=order)
                    log.info(f'trading reference market order {order}')

        # log final info
        self.ptm.log_perfect_trades_info()

        log.info(f'session {session_id} stopped with consolidated profit: {consolidated_profit:,.2f}')
        log.info(f'session {session_id} stopped with expected profit: {expected_profit:,.2f}')

        market_orders_count_at_cmp = abs(diff)

        # send info & profit to session manager
        self._session_stopped_callback(
            symbol,
            session_id,
            is_session_fully_consolidated,
            consolidated_profit,
            expected_profit,
            cmp_count,
            market_orders_count_at_cmp,  # number of orders placed at its own price
            placed_orders_at_order_price
        )

