# sc_session.py

import logging
import time
from enum import Enum

from typing import Callable, List
from binance import enums as k_binance

from sc_market import Market
from sc_order import Order, OrderStatus
from sc_balance_manager import BalanceManager, Account
from sc_pt_manager import PTManager
from sc_perfect_trade import PerfectTradeStatus
from sc_symbol import Symbol


log = logging.getLogger('log')


class QuitMode(Enum):
    CANCEL_ALL = 1
    PLACE_ALL_PENDING = 2
    TRADE_ALL_PENDING = 3


class Session:
    def __init__(self,
                 symbol: Symbol,
                 session_id: str,
                 session_stopped_callback: Callable[[Symbol, str, bool, float, float, int, int, int], None],
                 market: Market,
                 balance_manager: BalanceManager,
                 check_isolated_callback: Callable[[Symbol, str, float], None],
                 placed_isolated_callback: Callable[[Order], None],
                 # global_profit_update_callback: Callable[[float, float], None],
                 try_to_get_liquidity_callback: Callable[[Symbol, str, float], None]
                 ):

        self.symbol = symbol
        self.session_id = session_id
        self.session_stopped_callback = session_stopped_callback
        # self.placed_orders_from_previous_sessions = placed_orders_from_previous_sessions
        # self.global_profit_update_callback = global_profit_update_callback
        self.market = market
        self.bm = balance_manager

        # isolated manager callbacks
        self.check_isolated_callback = check_isolated_callback
        self.placed_isolated_callback = placed_isolated_callback

        # method to call when liquidity is needed
        self.try_to_get_liquidity_callback = try_to_get_liquidity_callback

        self.session_active = True

        config = self.symbol.config_data

        self.commission_rate_symbol = config['commission_rate_symbol']
        self.target_total_net_profit = float(config['target_total_net_profit'])
        self.cycles_count_for_inactivity = int(config['cycles_count_for_inactivity'])
        self.new_pt_shift = float(config['new_pt_shift'])
        self.isolated_distance = float(config['isolated_distance'])
        self.compensation_distance = float(config['compensation_distance'])
        self.compensation_gap = float(config['compensation_gap'])
        self.fee = float(config['fee'])
        self.quantity = float(config['quantity'])
        self.net_quote_balance = float(config['net_quote_balance'])
        self.max_negative_profit_allowed = float(config['max_negative_profit_allowed'])
        self.time_between_successive_pt_creation_tries = \
            float(config['time_between_successive_pt_creation_tries'])
        self.forced_shift = float(config['forced_shift'])

        self.ptm = PTManager(
            session_id=self.session_id,
            symbol=self.symbol
        )

        # used in dashboard in the cmp line chart. initiated with current cmp
        self.cmps = [self.market.get_cmp(self.symbol.name)]

        self.total_profit_series = [0.0]

        self.pt_created_count = 0
        self.buy_count = 0
        self.sell_count = 0
        self.cmp_count = 0
        self.cycles_from_last_trade = 0

        self.logbook: List[str] = []

        print('session object created')

    # ********** Binance socket callback functions **********
    def symbol_ticker_callback(self, cmp: float) -> None:
        if self.session_active:
            try:
                # 0.1: create first pt
                if self.cmp_count == 1:
                    is_allowed, forced_shift = self._allow_new_pt_creation(cmp=cmp, symbol=self.symbol)
                    if is_allowed:
                        shifted_cmp = cmp + forced_shift
                        self.ptm.create_new_pt(cmp=shifted_cmp, symbol=self.symbol)
                    else:
                        log.critical("initial pt not allowed, it will be tried again after inactivity period")

                # 0.2: update cmp count to control timely pt creation
                self.cmp_count += 1

                # these two lists will be used to plot
                self.cmps.append(cmp)

                # counter used to detect inactivity
                self.cycles_from_last_trade += 1

                # it is important to check first the active list and then the monitor one
                # with this order we guarantee there is only one status change per cycle
                self._check_active_orders_for_trading(cmp=cmp)

                # 4. loop through monitoring orders for activating
                self._check_monitor_orders_for_activating(cmp=cmp)

                # 5. check inactivity
                self._check_inactivity(cmp=cmp)

                # 6. check dynamic parameters
                self._check_dynamic_parameters()

                # ********** SESSION EXIT POINT ********
                self._check_exit_conditions(cmp)

            except AttributeError as e:
                print(e)

    def _check_dynamic_parameters(self):
        pass

    def _check_exit_conditions(self, cmp):
        # check profit only if orders are stable (no ACTIVE nor TO_BE_TRADED)
        orders = self.ptm.get_orders_by_request(
            orders_status=[OrderStatus.ACTIVE, OrderStatus.TO_BE_TRADED],
            pt_status=[PerfectTradeStatus.NEW, PerfectTradeStatus.BUY_TRADED, PerfectTradeStatus.SELL_TRADED]
        )
        if len(orders) == 0:
            # 8. check global net profit
            # return the total profit considering that all remaining orders are traded at current cmp
            total_profit = self.ptm.get_total_actual_profit_at_cmp(cmp=cmp)

            # exit point 1: target achieved
            if total_profit > self.target_total_net_profit:
                self.logbook.append('exit point #1: TRADE_ALL_PENDING')
                self.session_active = False
                self.quit_particular_session(quit_mode=QuitMode.TRADE_ALL_PENDING)

            # exit point 2: reached maximum allowed loss
            elif total_profit < self.max_negative_profit_allowed:
                self.logbook.append('exit point #2: PLACE_ALL_PENDING')
                self.session_active = False
                self.quit_particular_session(quit_mode=QuitMode.PLACE_ALL_PENDING)

    def _check_monitor_orders_for_activating(self, cmp: float) -> None:
        # get orders
        monitor_orders = self.ptm.get_orders_by_request(
            orders_status=[OrderStatus.MONITOR],
            pt_status=[PerfectTradeStatus.NEW, PerfectTradeStatus.BUY_TRADED, PerfectTradeStatus.SELL_TRADED]
        )
        # change status MONITOR -> ACTIVE
        [order.set_status(OrderStatus.ACTIVE) for order in monitor_orders if order.is_ready_for_activation(cmp=cmp)]

    def _check_active_orders_for_trading(self, cmp: float) -> None:
        # get orders
        active_orders = self.ptm.get_orders_by_request(
            orders_status=[OrderStatus.ACTIVE],
            pt_status=[PerfectTradeStatus.NEW, PerfectTradeStatus.BUY_TRADED, PerfectTradeStatus.SELL_TRADED]
        )
        # trade at market price active orders ready for trading
        [self._place_market_order(order=order) for order in active_orders if order.is_ready_for_trading(cmp=cmp)]

    def _check_inactivity(self, cmp):
        # a new pt is created if no order has been traded for a while
        # check elapsed time since last trade
        if self.cycles_from_last_trade > self.cycles_count_for_inactivity:
            # check liquidity
            is_allowed, forced_shift = self._allow_new_pt_creation(cmp=cmp, symbol=self.symbol)
            if is_allowed:
                shifted_cmp = cmp + forced_shift
                self.ptm.create_new_pt(cmp=shifted_cmp, symbol=self.symbol, pt_type='FROM_INACTIVITY')
                self.cycles_from_last_trade = 0  # equivalent to trading but without a trade
            else:
                log.info('new perfect trade creation is not allowed. it will be tried again after 60"')
                # update inactivity counter to try again after 60 cycles if inactivity continues
                self.cycles_from_last_trade -= self.time_between_successive_pt_creation_tries

    def order_traded_callback(self, uid: str, order_price: float, bnb_commission: float) -> None:
        print(f'********** ORDER TRADED:    price: {order_price} [Q] - commission: {bnb_commission} [BNB]')
        log.info(f'********** ORDER TRADED:    price: {order_price} [Q] - commission: {bnb_commission} [BNB]')

        # get candidate orders
        orders_to_be_traded = self.ptm.get_orders_by_request(
            orders_status=[OrderStatus.TO_BE_TRADED],
            pt_status=[PerfectTradeStatus.NEW, PerfectTradeStatus.BUY_TRADED, PerfectTradeStatus.SELL_TRADED]
        )

        for order in orders_to_be_traded:
            # check uid
            if order.uid == uid:
                log.info(f'confirmation of order traded: {order}')
                self.logbook.append(f'order traded: {order.pt.id} {order.name} {order.k_side}')
                # reset counter
                self.cycles_from_last_trade = 0

                # update buy & sell count
                if order.k_side == k_binance.SIDE_BUY:
                    self.buy_count += 1
                else:
                    self.sell_count += 1

                # set commission and price
                order.set_bnb_commission(
                    commission=bnb_commission,
                    bnb_quote_rate=self.market.get_cmp(symbol=self.commission_rate_symbol))

                # set traded order price
                order.price = order_price

                # change status
                order.set_status(status=OrderStatus.TRADED)

                # update perfect trades list & pt status
                self.ptm.order_traded(order=order)

                # check condition for new pt:
                if order.pt.status == PerfectTradeStatus.COMPLETED:
                    # check liquidity:
                    is_allowed, forced_shift = self._allow_new_pt_creation(cmp=self.cmps[-1], symbol=self.symbol)
                    if is_allowed:
                        shifted_cmp = order_price + forced_shift
                        # create pt
                        self.ptm.create_new_pt(cmp=shifted_cmp, symbol=self.symbol)
                        self.cycles_from_last_trade = 0

                # since the traded orders has been identified, do not check more orders
                break

        # if no order found, then check in placed_orders_from_previous_sessions list
        self.check_isolated_callback(self.symbol, uid, order_price)

    def _allow_new_pt_creation(self, cmp: float, symbol: Symbol) -> (bool, float):
        # 1. liquidity
        is_allowed_by_liquidity, forced_shift = self._is_liquidity_enough(cmp=cmp, symbol=symbol)
        # in case a new pt is allowed by liquidity, also return the needed shifted (to force SELL or BUY)
        if not is_allowed_by_liquidity:
            return False, 0.0

        # 2. monitor + active count
        # 3. span / depth
        # 2. momentum
        # dynamic parameters:
        #   - inactivity time
        #   - neb/amount

        # if all conditions passed
        return True, forced_shift

    def _is_liquidity_enough(self, cmp: float, symbol: Symbol) -> (bool, float):
        # liquidity needed for new pt orders (b1 & s1)
        new_pt_base_asset_liquidity_needed = self.quantity
        new_pt_quote_asset_liquidity_needed = self.quantity * cmp

        # get total quote & needed to trade all alive orders at their own price
        quote_asset_needed, base_asset_needed = self.ptm.get_symbol_liquidity_needed()

        # check available liquidity (quote & base) vs needed when trading both orders
        # get existing liquidity
        quote_asset_liquidity = self.market.get_asset_liquidity(asset=symbol.get_quote_asset().get_name())  # free
        base_asset_liquidity = self.market.get_asset_liquidity(asset=symbol.get_base_asset().get_name())  # free

        if quote_asset_liquidity < quote_asset_needed + new_pt_quote_asset_liquidity_needed:  # need for quote
            # check whether there is enough quote asset to force a pt shifted to SELL
            if base_asset_liquidity > base_asset_needed + new_pt_base_asset_liquidity_needed:  # enough base
                # force the creation of a shifted pt to SELL base and get quote
                log.info(f'new pt with forced shift: {-self.forced_shift}')
                return True, -self.forced_shift  # force SELL
            else:
                # get quote by selling base
                self.try_to_get_liquidity_callback(self.symbol, k_binance.SIDE_SELL, cmp)
                return False, 0.0

        elif base_asset_liquidity < base_asset_needed + new_pt_base_asset_liquidity_needed:  # need for base
            if quote_asset_liquidity > quote_asset_needed + new_pt_quote_asset_liquidity_needed:  # enough quote
                # force the creation of a shifted pt to BUY base
                log.info(f'new pt with forced shift: {+self.forced_shift} '
                         f'q: {quote_asset_liquidity} b: {base_asset_liquidity}')
                return True, +self.forced_shift  # force SELL
            else:
                # get base buying
                self.try_to_get_liquidity_callback(self.symbol, k_binance.SIDE_BUY, cmp)
                return False, 0.0

        else:
            return True, 0.0

    def account_balance_callback(self, accounts: List[Account]) -> None:
        # update of current balance from Binance
        # log.debug([account.name for account in accounts])
        self.bm.update_current_accounts(received_accounts=accounts)

    def place_isolated_order(self, order: Order) -> None:
        # method called from session manager to place at MARKET price an isolated order, to get liquidity
        log.info(f'place isolated order at cmp to get liquidity: {order}')
        self.logbook.append(f'place isolated order at cmp to get liquidity: {order}')
        self._place_market_order(order=order)

    # ********** check methods **********
    def _place_market_order(self, order) -> None:  # (bool, Optional[str]):
        # raise an exception if the order is not placed in binance (probably due to not enough liquidity)
        # change order status (it will be update to TRADED once received through binance socket)
        order.set_status(OrderStatus.TO_BE_TRADED)
        # place order and check message received
        msg = self.market.place_market_order(order=order)
        if msg:
            order.set_binance_id(new_id=msg.get('binance_id'))
            log.info(f'********** MARKET ORDER PLACED **********')  # msg: {msg}')
            log.info(f'order: {order}')
        else:
            log.critical(f'market order not place in binance {order}')
            raise Exception("MARKET order not placed")

    def _place_limit_order(self, order: Order) -> None:  # (bool, Optional[str]):
        order.set_status(status=OrderStatus.TO_BE_TRADED)
        # place order
        msg = self.market.place_limit_order(order=order)
        if msg:
            order.set_binance_id(new_id=msg.get('binance_id'))
            log.debug(f'********** LIMIT ORDER PLACED **********')  # msg: {msg}')
            log.info(f'order: {order}')
        else:
            log.critical(f'error placing order {order}')
            raise Exception("LIMIT order not placed")

    def quit_particular_session(self, quit_mode: QuitMode):
        log.info(f'********** STOP {quit_mode.name} **********')
        log.info(f'session {self.session_id} terminated')

        # init used variables
        is_session_fully_consolidated = False
        diff = 0
        consolidated_profit = 0.0
        expected_profit = 0.0
        placed_orders_at_order_price = 0

        if quit_mode == QuitMode.PLACE_ALL_PENDING:  # place all monitor orders
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
                        self._place_limit_order(order=order)
                        placed_orders_at_order_price += 1
                        # add to isolated orders list
                        self.placed_isolated_callback(order)
                        log.info(f'trading limit order {order.k_side} {order.status} {order.price}')
                        time.sleep(0.1)

        elif quit_mode == QuitMode.TRADE_ALL_PENDING:  # trade diff orders at reference side (BUY or SELL)
            # set session terminating status
            is_session_fully_consolidated = True

            # get consolidated profit (expected is zero)
            consolidated_profit += self.ptm.get_total_actual_profit_at_cmp(cmp=self.cmps[-1])

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
                    self._place_market_order(order=order)
                    log.info(f'trading reference market order {order.k_side} {order.status}')
                    time.sleep(0.1)
            elif diff < 0:  # SELL SIDE
                log.info('SELL SIDE')
                for i in range(-diff):
                    order = sell_orders[i]
                    self._place_market_order(order=order)
                    log.info(f'trading reference market order {order.k_side} {order.status}')
                    time.sleep(0.1)

        # log final info
        self.ptm.log_perfect_trades_info()

        log.info(f'session {self.session_id} stopped with consolidated profit: {consolidated_profit:,.2f}')
        log.info(f'session {self.session_id} stopped with expected profit: {expected_profit:,.2f}')

        market_orders_count_at_cmp = abs(diff)

        print('---------- LOGBOOK:')
        [print(f'     {msg}') for msg in self.logbook]
        print('---------- LOGBOOK END')

        # send info & profit to session manager
        self.session_stopped_callback(
            self.symbol,
            self.session_id,
            is_session_fully_consolidated,
            consolidated_profit,
            expected_profit,
            self.cmp_count,
            market_orders_count_at_cmp,  # number of orders placed at its own price
            placed_orders_at_order_price
        )
