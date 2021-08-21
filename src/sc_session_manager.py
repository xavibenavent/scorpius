# sc_session_manager.py

from datetime import datetime
from typing import Optional, List
import logging
import os
import signal

from sc_session import Session
from sc_market import Market
# from sc_account_balance import AccountBalance
from sc_balance_manager import BalanceManager, Account

log = logging.getLogger('log')


class SessionManager:
    def __init__(self):
        print('session manager')
        self.market = Market(
            symbol_ticker_callback=self._fake_symbol_socket_callback,
            order_traded_callback=self._fake_order_socket_callback,
            account_balance_callback=self._fake_account_socket_callback)

        self.session: Optional[Session] = None

        self.bm = BalanceManager(market=self.market, account_names=['BTC', 'EUR', 'BNB'])

        # global sessions info
        self.session_count = 0

        # self.global_profit = 0
        self.global_consolidated_profit = 0
        self.global_expected_profit = 0
        self.global_cmp_count = 0
        self.placed_orders_count = 0

        self.placed_orders_from_previous_sessions = []

        # todo: not sure whether it will work
        self.market.start_sockets()

        # start first session
        self.start_new_session()

    def _global_profit_update_callback(self, consolidated, expected):
        # called when an order from a previous session is traded in Binance
        self.global_consolidated_profit += consolidated
        self.global_expected_profit -= expected
        print('check are equals:')
        log.info('********** global profit updated **********')
        log.info(f'consolidated: {consolidated} expected: {expected}')
        log.info('*****************************************************************************')
        [print(order) for order in self.placed_orders_from_previous_sessions]

    def _session_stopped_callback(self,
                                  session_id: str,
                                  consolidated_profit: float,
                                  expected_profit: float,
                                  cmp_count: int,
                                  placed_orders_count: int,
                                  ) -> None:
        print(f'session stopped with id: {session_id} consolidated profit: {consolidated_profit}')
        print(f'session stopped with id: {session_id} expected profit: {expected_profit}')
        log.info(f'session stopped with id: {session_id} consolidated profit: {consolidated_profit}')
        log.info(f'session stopped with id: {session_id} expected profit: {expected_profit}')

        # self.global_profit += net_profit
        self.global_consolidated_profit += consolidated_profit
        self.global_expected_profit += expected_profit

        self.global_cmp_count += cmp_count
        self.placed_orders_count += placed_orders_count

        print(f'********** sessions count: {self.session_count} **********')
        print(f'********** partial cmp count: {self.global_cmp_count / 3600.0:,.2f} [hours]')
        print(f'********** global consolidated profit: {self.global_consolidated_profit:,.2f} **********')
        print(f'********** global expected profit: {self.global_expected_profit:,.2f} **********')
        print(f'********** placed orders count: {self.placed_orders_count} **********')

        print('placed orders:')
        [print(order) for order in self.placed_orders_from_previous_sessions]

        if self.session_count < 1000:
            self.start_new_session()
        else:
            self.stop_global_session()
            # self.market.stop()
            # raise Exception('********** GLOBAL SESSION MANAGER FINISHED **********')

    def start_new_session(self):
        # to avoid errors of socket calling None during Session init
        self.market.symbol_ticker_callback = self._fake_symbol_socket_callback
        self.market.order_traded_callback = self._fake_order_socket_callback
        self.market.account_balance_callback = self._fake_account_socket_callback

        session_id = f'S_{datetime.now().strftime("%Y%m%d_%H%M")}'

        self.session = Session(
            session_id=session_id,
            session_stopped_callback=self._session_stopped_callback,
            market=self.market,
            balance_manager=self.bm,
            placed_orders_from_previous_sessions=self.placed_orders_from_previous_sessions,
            global_profit_update_callback=self._global_profit_update_callback
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

    def _fake_symbol_socket_callback(self, foo: float):
        pass

    def _fake_order_socket_callback(self, foo_1: str, foo_2: float, foo_3: float):
        pass

    def _fake_account_socket_callback(self, foo: List[Account]):
        pass
