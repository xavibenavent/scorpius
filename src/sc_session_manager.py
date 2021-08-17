# sc_session_manager.py

from datetime import datetime
from typing import Optional
import logging
import os
import signal

from sc_session import Session
from sc_market import Market
from sc_account_balance import AccountBalance
from sc_balance_manager import BalanceManager

log = logging.getLogger('log')


class SessionManager:
    def __init__(self):
        print('session manager')
        self.market = Market(
            symbol_ticker_callback=self.fake_symbol_socket_callback,
            order_traded_callback=self.fake_order_socket_callback,
            account_balance_callback=self.fake_account_socket_callback)

        self.session: Optional[Session] = None

        self.bm = BalanceManager(market=self.market)

        # global sessions info
        self.session_count = 0

        self.global_profit = 0
        self.global_cmp_count = 0
        self.placed_orders_count = 0

        # todo: not sure whether it will work
        self.market.start_sockets()

        # start first session
        self.start_new_session()

    def session_stopped(self, session_id: str, net_profit: float, cmp_count: int, placed_orders_count: int) -> None:
        print(f'session stopped with id: {session_id} net profit: {net_profit}')
        log.info(f'session stopped with id: {session_id} net profit: {net_profit}')

        self.global_profit += net_profit
        self.global_cmp_count += cmp_count
        self.placed_orders_count += placed_orders_count

        print(f'********** sessions count: {self.session_count} **********')
        print(f'********** partial cmp count: {self.global_cmp_count / 3600.0:,.2f} [hours]')
        print(f'********** partial global profit: {self.global_profit:,.2f} **********')
        print(f'********** placed orders count: {self.placed_orders_count} **********')

        if self.session_count < 100:
            self.start_new_session()
        else:
            self.market.stop()
            raise Exception('********** GLOBAL SESSION MANAGER FINISHED **********')

    def start_new_session(self):
        # to avoid errors of socket calling None during Session init
        self.market.symbol_ticker_callback = self.fake_symbol_socket_callback
        self.market.order_traded_callback = self.fake_order_socket_callback
        self.market.account_balance_callback = self.fake_account_socket_callback

        session_id = f'S_{datetime.now().strftime("%Y%m%d_%H%M")}'

        self.session = Session(
            session_id=session_id,
            session_stopped_callback=self.session_stopped,
            market=self.market,
            balance_manager=self.bm
        )

        # after having the session created, set again the callback functions that were None
        self.market.symbol_ticker_callback = self.session.symbol_ticker_callback
        self.market.order_traded_callback = self.session.order_traded_callback
        self.market.account_balance_callback = self.session.account_balance_callback

        # set callback function in session to be called when it is finished
        self.session.session_stop_callback = self.session_stopped

        self.session_count += 1

        # info
        log.info(f'******** NEW SESSION ********')
        log.info(f'{session_id}')
        print()
        print(f'******** NEW SESSION ********')
        print(f'{session_id}')

    def stop_global_session(self):
        # todo: improve force quit
        self.market.stop()
        # self.session = None

        log.critical("********** SESSION TERMINATED FROM BUTTON ********")

        # send SIGINT to own app (identical to CTRL-C)
        pid = os.getpid()
        os.kill(pid, signal.SIGINT)

        # exit
        raise Exception("********** SESSION TERMINATED, PRESS CTRL-C ********")

    def fake_symbol_socket_callback(self, foo: float):
        pass

    def fake_order_socket_callback(self, foo_1: str, foo_2: float, foo_3: float):
        pass

    def fake_account_socket_callback(self, foo: AccountBalance):
        pass
