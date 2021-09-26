# sc_session.py

import logging

from typing import Callable, List
from binance import enums as k_binance

from market.sc_market_api_out import MarketAPIOut
from basics.sc_order import OrderStatus
from managers.sc_account_manager import Account, AccountManager
from session.sc_pt_manager import PTManager
from basics.sc_perfect_trade import PerfectTradeStatus
from basics.sc_symbol import Symbol, Asset
from managers.sc_isolated_manager import IsolatedOrdersManager
from managers.sc_strategy_manager import StrategyManager
from session.sc_helpers import Helpers, QuitMode

log = logging.getLogger('log')


class Session:
    CMP_PATTERN_LENGTH = 10

    def __init__(self,
                 symbol: Symbol,
                 session_id: str,
                 isolated_orders_manager: IsolatedOrdersManager,
                 session_stopped_callback: Callable[[Symbol, bool, float, float, int, int, int], None],
                 market: MarketAPIOut,
                 account_manager: AccountManager,
                 isolated_order_traded_callback: Callable[[Symbol, float, float], None],
                 get_liquidity_needed_callback: Callable[[Asset], float],
                 ):

        self.symbol = symbol
        self.session_id = session_id
        self.iom = isolated_orders_manager
        self.market = market
        self.am = account_manager

        # isolated manager callbacks
        self.isolated_order_traded_callback = isolated_order_traded_callback

        # liquidity needed callback
        self._get_liquidity_needed_callback = get_liquidity_needed_callback

        self.session_active = True

        config = self.symbol.config_data

        self.commission_rate_symbol = config['commission_rate_symbol']
        self.target_total_net_profit = float(config['target_total_net_profit'])
        self.cycles_count_for_inactivity = int(config['cycles_count_for_inactivity'])
        self.ref_cycles_inactivity = self.cycles_count_for_inactivity
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
        self.accepted_loss_to_get_liquidity = float(config['accepted_loss_to_get_liquidity'])
        self.forced_shift = float(config['forced_shift'])

        self.ptm = PTManager(
            session_id=self.session_id,
            symbol=self.symbol
        )

        # class with useful methods
        self.helpers = Helpers(
            pt_manager=self.ptm,
            market=self.market,
            session_stopped_callback=session_stopped_callback
        )

        self.strategy_manager = StrategyManager(
            quantity=self.quantity,
            market_api_out=self.market,
            isolated_orders_manager=self.iom,
            helpers=self.helpers,
            get_liquidity_needed_callback=get_liquidity_needed_callback
        )

        self.cmp = self.market.get_cmp(symbol_name=self.symbol.name)
        print(f'initial cmp: {self.cmp}')
        self.min_cmp = self.cmp
        self.max_cmp = self.cmp

        self.cmp_pattern_short: List[float] = [0.0] * self.CMP_PATTERN_LENGTH
        self.cmp_pattern_long: List[float] = [0.0] * self.CMP_PATTERN_LENGTH

        self.gap = 0.0

        self.total_profit_series = [0.0]

        self.pt_created_count = 0
        self.buy_count = 0
        self.sell_count = 0
        self.cmp_count = 0
        self.cycles_from_last_trade = 0

        self.logbook: List[str] = []

        self.alert_msg = ''

    # *******************************************************
    # ********** Binance socket callback functions **********
    # *******************************************************

    def symbol_ticker_callback(self, cmp: float) -> None:
        if self.session_active:
            try:
                # 0.1: create first pt
                if self.cmp_count == 5:
                    if self._try_new_pt_creation(cmp=cmp, symbol=self.symbol):
                        self.gap = self.ptm.get_first_gap()
                    else:
                        log.critical("initial pt not allowed, it will be tried again after inactivity period")

                # 0.2: update cmp count to control timely pt creation
                self.cmp_count += 1

                # update cmp, min_cmp & max_cmp
                if cmp < self.min_cmp:
                    self.min_cmp = cmp
                if cmp > self.max_cmp:
                    self.max_cmp = cmp
                self.cmp = cmp

                # add to pattern for prediction
                # short: last 10 cmp
                self.add_cmp_to_pattern(new_cmp=cmp, pattern=self.cmp_pattern_short)
                # long: last 100 cmp (save one out of 10)
                if self.cmp_count % 10 == 0:
                    self.add_cmp_to_pattern(new_cmp=cmp, pattern=self.cmp_pattern_long)
                # print(f'{self.symbol.name} pattern: {self.cmp_pattern}')

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

    def order_traded_callback(self, uid: str, order_price: float, bnb_commission: float) -> None:
        print(f'********** ORDER TRADED:    price: {order_price} [Q] - commission: {bnb_commission} [BNB]')
        log.info(f'********** ORDER TRADED:    {uid}')

        # get candidate orders
        orders_to_be_traded = self.ptm.get_orders_by_request(
            orders_status=[OrderStatus.TO_BE_TRADED],
            pt_status=[PerfectTradeStatus.NEW, PerfectTradeStatus.BUY_TRADED, PerfectTradeStatus.SELL_TRADED]
        )

        order_found = False

        for order in orders_to_be_traded:
            # check uid
            if order.uid == uid:
                order_found = True

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
                    bnb_quote_rate=self.market.get_cmp(symbol_name=self.commission_rate_symbol))

                # set traded order price
                order.price = order_price

                # change status
                order.set_status(status=OrderStatus.TRADED)

                # update perfect trades list & pt status
                self.ptm.order_traded(order=order)

                # check condition for new pt:
                if order.pt.status == PerfectTradeStatus.COMPLETED:
                    self._try_new_pt_creation(cmp=self.cmp, symbol=self.symbol)

        # if no order found, then check in placed_orders_from_previous_sessions list
        if not order_found:
            # check the isolated orders and, in case an order from previous session have been traded,
            # return the variation in profit (consolidated & expected), otherwise return zero
            is_known_order, consolidated, expected = \
                self.iom.check_isolated_orders(uid=uid, traded_price=order_price)

            if is_known_order:
                self.isolated_order_traded_callback(self.symbol, consolidated, expected)
            else:
                print(f'checking previous runs order with uid: {uid} price: {order_price}')
                self.iom.check_previous_runs_orders(uid=uid)

    def account_balance_callback(self, accounts: List[Account]) -> None:
        # update of current balance from Binance
        # log.debug([account.name for account in accounts])
        self.am.update_current_accounts(received_accounts=accounts)

    def _try_new_pt_creation(self, cmp: float, symbol: Symbol) -> bool:
        is_allowed, forced_shift = self._allow_new_pt_creation(cmp=self.cmp, symbol=self.symbol)
        if is_allowed:
            shifted_cmp = cmp + forced_shift
            # create pt
            self.ptm.create_new_pt(cmp=shifted_cmp, symbol=self.symbol)

            # update inactivity counters
            self.cycles_from_last_trade = 0
            self.cycles_count_for_inactivity = self.strategy_manager.get_new_inactivity_cycles(
                buy_count=self.buy_count,
                sell_count=self.sell_count,
                ref_cycles=self.ref_cycles_inactivity)
        return is_allowed

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
                # self.quit_particular_session(quit_mode=QuitMode.TRADE_ALL_PENDING)
                self.helpers.quit_particular_session(quit_mode=QuitMode.TRADE_ALL_PENDING,
                                                     session_id=self.session_id,
                                                     symbol=self.symbol,
                                                     cmp=self.cmp,
                                                     iom=self.iom,
                                                     cmp_count=self.cmp_count)

            # exit point 2: reached maximum allowed loss
            elif total_profit < self.max_negative_profit_allowed:
                self.logbook.append('exit point #2: PLACE_ALL_PENDING by max negative profit reached')
                self.session_active = False
                self.helpers.quit_particular_session(quit_mode=QuitMode.PLACE_ALL_PENDING,
                                                     session_id=self.session_id,
                                                     symbol=self.symbol,
                                                     cmp=self.cmp,
                                                     iom=self.iom,
                                                     cmp_count=self.cmp_count)

            # exit point 3: reached target with completed pt
            else:
                completed_pt = self.ptm.get_pt_by_request(pt_status=[PerfectTradeStatus.COMPLETED])
                if sum([pt.get_actual_profit_at_cmp(cmp=cmp) for pt in completed_pt]) > self.target_total_net_profit:
                    self.logbook.append('exit point #3: PLACE_ALL_PENDING by target reached with completed pt')
                    self.session_active = False
                    self.helpers.quit_particular_session(quit_mode=QuitMode.PLACE_ALL_PENDING,
                                                         session_id=self.session_id,
                                                         symbol=self.symbol,
                                                         cmp=self.cmp,
                                                         iom=self.iom,
                                                         cmp_count=self.cmp_count)

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
        [self.helpers.place_market_order(order=order) for order in active_orders if order.is_ready_for_trading(cmp=cmp)]

    def _check_inactivity(self, cmp):
        # a new pt is created if no order has been traded for a while
        # check elapsed time since last trade
        if self.cycles_from_last_trade > self.cycles_count_for_inactivity:
            if not self._try_new_pt_creation(cmp=cmp, symbol=self.symbol):
                log.info('new perfect trade creation is not allowed. it will be tried again after 60"')
                # update inactivity counter to try again after 60 cycles if inactivity continues
                self.cycles_from_last_trade -= self.time_between_successive_pt_creation_tries

    def manually_create_new_pt(self, cmp: float, symbol: Symbol):
        # called from the button in the dashboard
        self._try_new_pt_creation(cmp=cmp, symbol=symbol)

    def _allow_new_pt_creation(self, cmp: float, symbol: Symbol) -> (bool, float):
        # 1. check liquidity
        # check base liquidity and try to get if not enough
        if not self.strategy_manager.is_asset_liquidity_enough(asset=symbol.base_asset(), new_pt_need=self.quantity):
            # try to get
            # self.strategy_manager.try_to_get_liquidity(symbol=symbol, asset=symbol.base_asset(), cmp=cmp)
            return False, 0.0

        # check quote liquidity and try to get if not enough
        if not self.strategy_manager.is_asset_liquidity_enough(asset=symbol.quote_asset(),
                                                               new_pt_need=self.quantity * cmp):
            # try to get
            # self.strategy_manager.try_to_get_liquidity(symbol=symbol, asset=symbol.quote_asset(), cmp=cmp)
            return False, 0.0

        # check whether it is the last possible buy
        is_base_last, base_rel_dist = self.strategy_manager.is_last_possible(asset=symbol.base_asset(),
                                                                             new_pt_need=self.quantity)
        is_quote_last, quote_rel_dist = self.strategy_manager.is_last_possible(asset=symbol.quote_asset(),
                                                                               new_pt_need=self.quantity * cmp)

        # when both base and quote are in last zone, the one with less relative qty is chosen
        if is_base_last and is_quote_last:
            log.info(f'both base and quote are in last zone:')
            log.info(f'base_rel_dist: {base_rel_dist} quote_rel_dist: {quote_rel_dist}')
            # more relative distance means less liquidity
            if base_rel_dist > quote_rel_dist:
                # force buy
                shift = self.gap * 1.1 if self.gap != 0.0 else self.forced_shift
                log.info(f'forced buy (base) with shift {shift}')
                return True, shift
            else:
                # force sell
                shift = self.gap * 1.1 * (-1) if self.gap != 0.0 else self.forced_shift * (-1)
                log.info(f'forced sell (quote) with shift {shift}')
                return True, shift

        # when only one is in last zone
        if is_base_last:
            # force buy
            shift = self.gap * 1.1 if self.gap != 0.0 else self.forced_shift
            log.info(f'forced buy (base) with shift {shift}')
            return True, shift
        if is_quote_last:
            # force sell
            shift = self.gap * 1.1 * (-1) if self.gap != 0.0 else self.forced_shift * (-1)
            log.info(f'forced sell (quote) with shift {shift}')
            return True, shift

        # # 2. minimize span
        # all_orders = self.get_all_orders_for_symbol(symbol=symbol)
        # shift = self.strategy_manager.get_shift_to_minimize_span (all_orders=all_orders, cmp=cmp, gap=self.gap)
        # if shift != 0:
        #     return True, shift
        #
        # # 3. balance momentum
        # shift = self.strategy_manager.get_shift_to_balance_momentum(all_orders=all_orders, cmp=cmp, gap=self.gap)
        # return True, shift

        # Set shift based on predicted value
        if 0.0 not in self.cmp_pattern_short and 0.0 not in self.cmp_pattern_long:
            predicted_cmp = self.strategy_manager.get_tendency(cmp_pattern=self.cmp_pattern_short)
            shift_short = predicted_cmp - cmp
            print(f'cmp: {cmp} predicted value: {predicted_cmp} shift_short: {shift_short}')

            predicted_cmp = self.strategy_manager.get_tendency(cmp_pattern=self.cmp_pattern_long)
            shift_long = predicted_cmp - cmp
            print(f'cmp: {cmp} predicted value: {predicted_cmp} shift_long: {shift_long}')

            # set value as average from short and long
            short_weight = 0.5
            long_weight = 0.5
            shift = short_weight * shift_short + long_weight * shift_long
            print(f'applied shift: {shift}')

            return True, shift
        else:
            return True, 0.0

        # dynamic parameters:
        #   - inactivity time
        #   - neb/amount

    def get_all_orders_for_symbol(self, symbol: Symbol):
        isolated_orders = self.iom.get_isolated_orders(symbol_name=symbol.name)
        session_orders = self.ptm.get_orders_by_request(
            orders_status=[OrderStatus.MONITOR, OrderStatus.ACTIVE],
            pt_status=[PerfectTradeStatus.NEW, PerfectTradeStatus.BUY_TRADED,
                       PerfectTradeStatus.SELL_TRADED, PerfectTradeStatus.COMPLETED])
        all_orders = isolated_orders + session_orders
        return all_orders

    @staticmethod
    def add_cmp_to_pattern(new_cmp: float, pattern: List[float]):
        # shift left
        for i in range(0, len(pattern) - 1):
            pattern[i] = pattern[i + 1]
        # update last
        pattern[-1] = new_cmp
        # print(self.cmp_pattern)

