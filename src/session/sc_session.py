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
from managers.sc_db_manager import DBManager
from managers.sc_orders_manager import OrdersManager
from session.sc_helpers import Helpers
from session.sc_checks_manager import ChecksManager
from session.sc_off_mode_manager import OffModeManager

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
                 dbm: DBManager,
                 isolated_order_traded_callback: Callable[[Symbol, float, float], None],
                 get_liquidity_needed_callback: Callable[[Asset], float],
                 consolidated_profit: float,
                 orders_manager: OrdersManager
                 ):

        self.symbol = symbol
        self.session_id = session_id
        self.iom = isolated_orders_manager
        self.market = market
        self.am = account_manager
        self.dbm = dbm

        self.orders_manager = orders_manager

        # isolated manager callbacks
        self.isolated_order_traded_callback = isolated_order_traded_callback

        # liquidity needed callback
        self._get_liquidity_needed_callback = get_liquidity_needed_callback

        self.session_active = True

        # parameters from config.ini
        config = self.symbol.config_data
        self.cycles_count_for_inactivity = int(config['cycles_count_for_inactivity'])  # use as variable

        self.P_COMMISSION_RATE_SYMBOL = config['commission_rate_symbol']
        self.P_REF_CYCLES_INACTIVITY = self.cycles_count_for_inactivity
        self.P_QUANTITY = float(config['quantity'])
        self.P_NET_QUOTE_BALANCE = float(config['net_quote_balance'])
        self.P_TIME_BETWEEN_SUCCESSIVE_PT_CREATION_TRIES = float(config['time_between_successive_pt_creation_tries'])
        self.P_FORCED_SHIFT = float(config['forced_shift'])

        self.consolidated_profit = consolidated_profit

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
            quantity=self.P_QUANTITY,
            market_api_out=self.market,
            isolated_orders_manager=self.iom,
            helpers=self.helpers,
            get_liquidity_needed_callback=get_liquidity_needed_callback
        )

        self.checks_manager = ChecksManager(
            iom=self.iom,
            strategy_manager=self.strategy_manager,
            ptm=self.ptm,
            helpers=self.helpers,
            market_api_out=self.market,
            config=config,
            symbol=symbol
        )

        self.off_mode_manager = OffModeManager(
            symbol=symbol,
            iom=self.iom,
            strategy_manager=self.strategy_manager,
            helpers=self.helpers,
            ptm=self.ptm,
            market_api_out=self.market,
            config=config
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

        self.is_active = True

    # *******************************************************
    # ********** Binance socket callback functions **********
    # *******************************************************

    def symbol_ticker_callback(self, cmp: float) -> None:
        if self.session_active:
            try:
                self.is_active = self.off_mode_manager.check_to_update_activation_flag(cmp=cmp)
                # self.off_mode_manager.check_monitor_order(cmp=cmp)
                # if not self.is_active:
                #     # try to create shifted pt
                #     orders = self.iom.isolated_orders + self.ptm.get_all_alive_orders()
                #     buy_span, sell_span = self.helpers.get_span_from_list(orders=orders, cmp=cmp)
                #     if buy_span == 0.0 and sell_span > 0.0:
                #         # force sell
                #         shifted_cmp = cmp - self.P_FORCED_SHIFT
                #         if self.strategy_manager.is_liquidity_enough(cmp=cmp, symbol=self.symbol):
                #             self.ptm.create_new_pt(cmp=shifted_cmp, symbol=self.symbol)
                #             created_remaining_order = self.ptm.perfect_trades[-1].orders[0]
                #             print(f'created remaining order: {created_remaining_order}')
                #             # self.off_mode_manager.monitor_order = created_remaining_order  # buy order
                #
                #     elif buy_span > 0.0 and sell_span == 0.0:
                #         # force buy
                #         shifted_cmp = cmp + self.P_FORCED_SHIFT
                #         if self.strategy_manager.is_liquidity_enough(cmp=cmp, symbol=self.symbol):
                #             self.ptm.create_new_pt(cmp=shifted_cmp, symbol=self.symbol)
                #             created_remaining_order = self.ptm.perfect_trades[-1].orders[1]
                #             log.info(f'created remaining order: {created_remaining_order}')
                #             # self.off_mode_manager.monitor_order = created_remaining_order  # sell order

                # 0.1: create first pt
                if self.cmp_count == 5:
                    if self._try_new_pt_creation(cmp=cmp):
                        self.gap = self.ptm.get_first_gap()
                    else:
                        # log.critical("initial pt not allowed, it will be tried again after inactivity period")
                        pass

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
                # self._check_active_orders_for_trading(cmp=cmp)
                self.checks_manager.check_active_orders_for_trading(cmp=cmp)

                # 4. loop through monitoring orders for activating
                # self._check_monitor_orders_for_activating(cmp=cmp)
                self.checks_manager.check_monitor_orders_for_activating(cmp=cmp)

                # 5. check inactivity
                self._check_inactivity(cmp=cmp)

                # 6. check pending orders to place if close to be traded
                # self._check_pending_orders()
                self.checks_manager.check_pending_orders(cmp=cmp, consolidated_profit=self.consolidated_profit)

                # ********** SESSION EXIT POINT ********
                self.checks_manager.check_exit_conditions(cmp=cmp, session_id=self.session_id, cmp_count=self.cmp_count)

                # self.checks_manager.check_trade_at_loss(cmp=cmp)

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
                    bnb_quote_rate=self.market.get_cmp(symbol_name=self.P_COMMISSION_RATE_SYMBOL))

                # set traded order price
                order.price = order_price

                # change status
                order.set_status(status=OrderStatus.TRADED)

                # update perfect trades list & pt status
                self.ptm.order_traded(order=order)

                # check condition for new pt:
                if order.pt.status == PerfectTradeStatus.COMPLETED:
                    self._try_new_pt_creation(cmp=self.cmp)

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

    def _try_new_pt_creation(self, cmp: float) -> bool:
        if self.is_active:
            # is_allowed, forced_shift = self._allow_new_pt_creation(cmp=self.cmp, symbol=self.symbol)
            is_allowed, forced_shift = self.checks_manager.allow_new_pt_creation(
                cmp=self.cmp,
                consolidated_profit=self.consolidated_profit,
                gap=self.gap,
                cmp_pattern_short=self.cmp_pattern_short,
                cmp_pattern_long=self.cmp_pattern_long
            )
            if is_allowed:
                shifted_cmp = cmp + forced_shift
                # create pt
                b1, s1 = self.ptm.create_new_pt(cmp=shifted_cmp, symbol=self.symbol)

                self.orders_manager.orders.append(b1)
                self.orders_manager.orders.append(s1)
                # self.orders_manager.show_orders()

                # update inactivity counters
                self.cycles_from_last_trade = 0
                self.cycles_count_for_inactivity = self.strategy_manager.get_new_inactivity_cycles(
                    buy_count=self.buy_count,
                    sell_count=self.sell_count,
                    ref_cycles=self.P_REF_CYCLES_INACTIVITY)
            return is_allowed
        else:
            return False

    def _check_inactivity(self, cmp):
        # a new pt is created if no order has been traded for a while
        # check elapsed time since last trade
        if self.cycles_from_last_trade > self.cycles_count_for_inactivity:
            if not self._try_new_pt_creation(cmp=cmp):
                log.info('new perfect trade creation is not allowed. it will be tried again after 60"')
                # update inactivity counter to try again after 60 cycles if inactivity continues
                self.cycles_from_last_trade -= self.P_TIME_BETWEEN_SUCCESSIVE_PT_CREATION_TRIES

    def manually_create_new_pt(self):
        # called from the button in the dashboard
        self._try_new_pt_creation(cmp=self.cmp)

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
