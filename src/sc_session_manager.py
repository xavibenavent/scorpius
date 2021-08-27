# sc_session_manager.py

from datetime import datetime
from typing import Optional, List, Dict
import logging
import os
import signal

# import configparser
from config_manager import ConfigManager

from sc_session import Session
from sc_market import Market
from sc_balance_manager import BalanceManager, Account
from sc_isolated_manager import IsolatedOrdersManager
from sc_order import Order
from sc_symbol import Symbol, Asset

log = logging.getLogger('log')


class SessionManager:
    def __init__(self):
        print('session manager')

        self.iom = IsolatedOrdersManager()

        self.market = Market(
            symbol_ticker_callback=self._fake_symbol_socket_callback,
            order_traded_callback=self._fake_order_socket_callback,
            account_balance_callback=self._fake_account_socket_callback)

        # session will be started within start_session method
        self.active_sessions: Dict[str, Optional[Session]] = {}
        self.terminated_sessions: Dict[str, Dict] = {}

        # get initial accounts to create the balance manager (all own accounts managed in Binance)
        accounts = self.market.get_account_info()
        self.bm = BalanceManager(accounts=accounts)

        # get list of symbols info from config.ini & market
        symbols = self._get_symbols()

        # global sessions info
        self.session_count = 0

        # todo: start sockets for this symbol
        self.market.start_sockets()

        # start first sessions
        for symbol in symbols:
            self._init_global_data(symbol=symbol)
            self.active_sessions[symbol.name] = self.start_new_session(symbol=symbol)

            # start ticker socket for each symbol
            self.market.start_symbol_ticker_socket(
                symbol_name=symbol.name,
                # send the usual callback function
                callback=self.active_sessions[symbol.name].symbol_ticker_callback)

    def _get_symbols(self) -> List[Symbol]:
        # list to return
        symbols: List[Symbol] = []

        cm = ConfigManager(config_file='config_new.ini')
        symbols_name = cm.get_symbol_names()

        for symbol_name in symbols_name:
            symbol_filters = self.market.get_symbol_info(symbol_name=symbol_name)

            # fix Binance mistake in EUR precision (originally 8 and it is enough with 2)
            if symbol_filters.get('quote_asset') == 'EUR':
                symbol_filters['quote_precision'] = 2

            symbol_config_data = cm.get_symbol_data(symbol_name=symbol_name)

            # set symbol to pass at sessions start
            symbol = Symbol(
                name=symbol_name,
                base_asset=Asset(
                    name=symbol_filters.get('base_asset'),
                    precision_for_visualization=6),  # BTC
                quote_asset=Asset(
                    name=symbol_filters.get('quote_asset'),
                    precision_for_visualization=2),  # EUR
                filters=symbol_filters,
                config_data=symbol_config_data
            )
            # update list
            symbols.append(symbol)
        return symbols

    def _update_global_profit(self, symbol: Symbol, consolidated: float, expected: float):
        # update
        if symbol.name in self.terminated_sessions.keys():
            self.terminated_sessions[symbol.name]['global_consolidated_profit'] += consolidated
            # subtraction because expected is calculated as an absolut value
            self.terminated_sessions[symbol.name]['global_expected_profit'] -= expected

        # log
        log.info(f'********** global profit updated for symbol {symbol.name} **********')
        log.info(f'consolidated: {consolidated:,.2f} expected: {expected:,.2f}')
        log.info('*****************************************************************************')

    def _session_stopped_callback(self,
                                  symbol: Symbol,
                                  session_id: str,
                                  is_session_fully_consolidated: bool,
                                  consolidated_profit: float,
                                  expected_profit: float,
                                  cmp_count: int,
                                  market_orders_count_at_cmp: int,
                                  placed_orders_count_at_price: int
                                  ) -> None:

        # update terminated sessions or create if first session terminated
        if symbol.name in self.terminated_sessions.keys():
            self.terminated_sessions[symbol.name]['global_consolidated_session_count'] += \
                1 if is_session_fully_consolidated else 0
            self.terminated_sessions[symbol.name]['global_expected_session_count'] += \
                1 if not is_session_fully_consolidated else 0
            self.terminated_sessions[symbol.name]['global_cmp_count'] += cmp_count
            self.terminated_sessions[symbol.name]['global_consolidated_profit'] += consolidated_profit
            self.terminated_sessions[symbol.name]['global_expected_profit'] += expected_profit
            self.terminated_sessions[symbol.name]['global_market_orders_count_at_cmp'] += market_orders_count_at_cmp
            self.terminated_sessions[symbol.name]['global_placed_orders_count_at_price'] += placed_orders_count_at_price
            self.terminated_sessions[symbol.name]['global_placed_pending_orders_count'] += placed_orders_count_at_price
        else:
            raise Exception(f'global data for {symbol.name} should already exist')

        # check for session manager end
        if self.session_count < 1000:
            self.active_sessions[symbol.name] = self.start_new_session(symbol=symbol)
        else:
            self.stop_global_session()
            # self.market.stop()
            # raise Exception('********** GLOBAL SESSION MANAGER FINISHED **********')

    def _init_global_data(self, symbol: Symbol):
        self.terminated_sessions[symbol.name] = {}
        self.terminated_sessions[symbol.name]['global_consolidated_session_count'] = 0
        self.terminated_sessions[symbol.name]['global_expected_session_count'] = 0
        self.terminated_sessions[symbol.name]['global_cmp_count'] = 0
        self.terminated_sessions[symbol.name]['global_consolidated_profit'] = 0.0
        self.terminated_sessions[symbol.name]['global_expected_profit'] = 0.0
        self.terminated_sessions[symbol.name]['global_market_orders_count_at_cmp'] = 0
        self.terminated_sessions[symbol.name]['global_placed_orders_count_at_price'] = 0
        self.terminated_sessions[symbol.name]['global_placed_pending_orders_count'] = 0

    def start_new_session(self, symbol: Symbol) -> Session:
        # to avoid errors of socket calling None during Session init
        self.market.symbol_ticker_callback = self._fake_symbol_socket_callback
        self.market.order_traded_callback = self._fake_order_socket_callback
        self.market.account_balance_callback = self._fake_account_socket_callback

        session_id = f'S_{datetime.now().strftime("%Y%m%d_%H%M")}'

        session = Session(
            symbol=symbol,
            session_id=session_id,
            session_stopped_callback=self._session_stopped_callback,
            market=self.market,
            balance_manager=self.bm,
            check_isolated_callback=self._check_isolated_callback,
            placed_isolated_callback=self._placed_isolated_callback,
            # global_profit_update_callback=self._global_profit_update_callback,
            try_to_get_liquidity_callback=self._try_to_get_liquidity_callback
        )

        # after having the session created, set again the callback functions that were None
        self.market.symbol_ticker_callback = session.symbol_ticker_callback
        self.market.order_traded_callback = session.order_traded_callback
        self.market.account_balance_callback = session.account_balance_callback

        # set callback function in session to be called when it is finished
        # session.session_stop_callback = self._session_stopped_callback

        self.session_count += 1

        # info
        print(f'\n\n******** NEW SESSION STARTED: {session_id}********\n')
        log.info(f'\n\n******** NEW SESSION STARTED: {session_id}********\n')

        return session

    def stop_global_session(self):
        # stop market (binance sockets)
        self.market.stop()

        log.critical("********** SESSION TERMINATED FROM BUTTON ********")

        # send SIGINT to own app (identical to CTRL-C)
        pid = os.getpid()
        os.kill(pid, signal.SIGINT)

        # exit
        raise Exception("********** SESSION TERMINATED, PRESS CTRL-C ********")

    def _check_isolated_callback(self, symbol: Symbol, uid: str, order_price: float):
        # check the isolated orders and, in case an order from previous session have been traded,
        # return the variation in profit (consolidated & expected), otherwise return zero
        is_known_order, consolidated, expected = \
            self.iom.check_isolated_orders(uid=uid, traded_price=order_price)

        # update actual orders placed count, decrementing in one unit
        if is_known_order:
            if symbol.name in self.terminated_sessions.keys():
                self.terminated_sessions[symbol.name]['global_placed_pending_orders_count'] -= 1

        # update profit
        self._update_global_profit(symbol=symbol, consolidated=consolidated, expected=expected)

    def _placed_isolated_callback(self, order: Order):
        # once the order have been placed in Binance, it is appended to the list
        self.iom.isolated_orders.append(order)

    def _try_to_get_liquidity_callback(self, symbol: Symbol, side: str, cmp: float):
        # called from session
        log.info(f'try to get liquidity callback called with side: {side}')

        order = self.iom.try_to_get_asset_liquidity(cmp=cmp, k_side=side)

        if order:
            # place at MARKET price
            log.info(f'order to place at market price with loss: {order}')
            # sanity check
            if order.symbol.name != symbol.name:
                raise Exception(f'{symbol.name} and {order.symbol.name} have to be equals')
            else:
                self.active_sessions[symbol.name].place_isolated_order(order=order)

            # cancel in Binance the previously placed order
            self.market.cancel_orders([order])

    def _fake_symbol_socket_callback(self, foo: float):
        pass

    def _fake_order_socket_callback(self, foo_1: str, foo_2: float, foo_3: float):
        pass

    def _fake_account_socket_callback(self, foo: List[Account]):
        pass
