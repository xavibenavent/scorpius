# sc_session_manager.py

import pprint
from datetime import datetime
from typing import Optional, List
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

        self.session: Optional[Session] = None

        # get initial accounts to create the balance manager
        accounts = self.market.get_account_info()
        self.bm = BalanceManager(accounts=accounts)

        # get symbols info from config.ini & Binance
        cm = ConfigManager(config_file='config_new.ini')
        symbols_name = cm.get_symbol_names()

        # looping this list items a first session will be created for each symbol
        symbols: List[Symbol] = []

        for symbol_name in symbols_name:
            symbol_filters = self.market.get_symbol_info(symbol=symbol_name)
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

            symbols.append(symbol)

        # global sessions info
        self.session_count = 0

        self.global_consolidated_session_count = 0
        self.global_expected_session_count = 0
        self.global_consolidated_profit = 0.0
        self.global_expected_profit = 0.0

        self.global_cmp_count = 0
        # number of orders traded at market price (cmp): quit mode TRADE_ALL_PENDING
        self.market_orders_count_at_cmp = 0

        # number of orders placed at order price: quit mode PLACE_ALL_PENDING
        self.placed_orders_count_at_price = 0

        # current number of pending orders placed at order price (initially placed - traded)
        self.placed_pending_orders_count = 0

        # todo: not sure whether it will work
        self.market.start_sockets()

        # start first sessions
        [self.start_new_session(symbol=symbol) for symbol in symbols]

    def _global_profit_update_callback(self, consolidated, expected):
        # called when an order from a previous session is traded in Binance
        self._update_global_profit(consolidated=consolidated, expected=expected)

    def _update_global_profit(self, consolidated: float, expected: float):
        # update
        self.global_consolidated_profit += consolidated
        self.global_expected_profit -= expected  # subtraction because expected is calculated as an absolut value

        # log
        log.info('********** global profit updated **********')
        log.info(f'consolidated: {consolidated} expected: {expected}')
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
        print(f'session stopped with id: {session_id} consolidated profit: {consolidated_profit}')
        print(f'session stopped with id: {session_id} expected profit: {expected_profit}')
        log.info(f'session stopped with id: {session_id} consolidated profit: {consolidated_profit}')
        log.info(f'session stopped with id: {session_id} expected profit: {expected_profit}')

        if is_session_fully_consolidated:
            self.global_consolidated_session_count += 1
        else:
            self.global_expected_session_count += 1

        self.global_consolidated_profit += consolidated_profit
        self.global_expected_profit += expected_profit

        # update global cmp count
        self.global_cmp_count += cmp_count

        # update number of orders traded at cmp in quit mode TRADE_ALL_PENDING
        self.market_orders_count_at_cmp += market_orders_count_at_cmp

        # both increased with the number of orders placed in quit mode PLACE_ALL_PENDING
        self.placed_orders_count_at_price += placed_orders_count_at_price
        # this will be diminished when a placed order is later traded (in other session)
        self.placed_pending_orders_count += placed_orders_count_at_price

        print(f'********** sessions count: {self.session_count} **********')
        print(f'********** partial cmp count: {self.global_cmp_count / 3600.0:,.2f} [hours]')
        print(f'********** global consolidated profit: {self.global_consolidated_profit:,.2f} **********')
        print(f'********** global expected profit: {self.global_expected_profit:,.2f} **********')
        print(f'********** placed orders count: {self.market_orders_count_at_cmp} **********')

        print('placed orders:')
        [print(order) for order in self.iom.isolated_orders]

        if self.session_count < 1000:
            self.start_new_session(symbol=symbol)
        else:
            self.stop_global_session()
            # self.market.stop()
            # raise Exception('********** GLOBAL SESSION MANAGER FINISHED **********')

    def start_new_session(self, symbol: Symbol):
        # to avoid errors of socket calling None during Session init
        self.market.symbol_ticker_callback = self._fake_symbol_socket_callback
        self.market.order_traded_callback = self._fake_order_socket_callback
        self.market.account_balance_callback = self._fake_account_socket_callback

        session_id = f'S_{datetime.now().strftime("%Y%m%d_%H%M")}'

        self.session = Session(
            symbol=symbol,
            session_id=session_id,
            session_stopped_callback=self._session_stopped_callback,
            market=self.market,
            balance_manager=self.bm,
            check_isolated_callback=self._check_isolated_callback,
            placed_isolated_callback=self._placed_isolated_callback,
            global_profit_update_callback=self._global_profit_update_callback,
            try_to_get_liquidity_callback=self._try_to_get_liquidity_callback
        )

        # after having the session created, set again the callback functions that were None
        self.market.symbol_ticker_callback = self.session.symbol_ticker_callback
        self.market.order_traded_callback = self.session.order_traded_callback
        self.market.account_balance_callback = self.session.account_balance_callback

        # set callback function in session to be called when it is finished
        self.session.session_stop_callback = self._session_stopped_callback

        self.session_count += 1

        # info
        print(f'\n\n******** NEW SESSION STARTED: {session_id}********\n')
        log.info(f'\n\n******** NEW SESSION STARTED: {session_id}********\n')

    def stop_global_session(self):
        # stop market (binance sockets)
        self.market.stop()

        log.critical("********** SESSION TERMINATED FROM BUTTON ********")

        # send SIGINT to own app (identical to CTRL-C)
        pid = os.getpid()
        os.kill(pid, signal.SIGINT)

        # exit
        raise Exception("********** SESSION TERMINATED, PRESS CTRL-C ********")

    def _check_isolated_callback(self, uid: str, order_price: float):
        # check the isolated orders and, in case an order from previous session have been traded,
        # return the variation in profit (consolidated & expected), otherwise return zero
        is_known_order, consolidated, expected = \
            self.iom.check_isolated_orders(uid=uid, traded_price=order_price)

        # update actual orders placed count
        if is_known_order:
            self.placed_pending_orders_count -= 1

        # update profit
        self._update_global_profit(consolidated=consolidated, expected=expected)

    def _placed_isolated_callback(self, order: Order):
        # once the order have been placed in Binance, it is appended to the list
        self.iom.isolated_orders.append(order)

    def _try_to_get_liquidity_callback(self, side: str, cmp: float):
        log.info(f'try to get liquidity callback called with side: {side}')

        order = self.iom.try_to_get_asset_liquidity(cmp=cmp, k_side=side)

        if order:
            # place at MARKET price
            log.info(f'order to place at market price with loss: {order}')
            self.session.place_isolated_order(order=order)

            # cancel in Binance the previously placed order
            self.market.cancel_orders([order])

    def _fake_symbol_socket_callback(self, foo: float):
        pass

    def _fake_order_socket_callback(self, foo_1: str, foo_2: float, foo_3: float):
        pass

    def _fake_account_socket_callback(self, foo: List[Account]):
        pass
