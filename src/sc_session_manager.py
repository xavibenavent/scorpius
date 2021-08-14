# sc_session_manager.py

from datetime import datetime
from typing import Optional
import logging

from sc_session import Session
from sc_market import Market
from sc_account_balance import AccountBalance

log = logging.getLogger('log')


class SessionManager:
    def __init__(self):
        print('session manager')
        self.market = Market(symbol_ticker_callback=None, order_traded_callback=None, account_balance_callback=None)

        self.session: Optional[Session] = None

        self.session_count = 0
        self.global_profit = 0
        self.global_cmp_count = 0

        # todo: not sure whether it will work
        self.market.start_sockets()

        # start first session
        self.start_new_session()

    def session_stopped(self, session_id: str, net_profit: float, cmp_count: float):
        print(f'session stopped with id: {session_id} net profit: {net_profit}')
        log.info(f'session stopped with id: {session_id} net profit: {net_profit}')

        self.global_profit += net_profit
        self.global_cmp_count += cmp_count

        print(f'********** sessions count: {self.session_count} **********')
        print(f'********** partial cmp count: {self.global_cmp_count / 3600:,.2f} [hours]')
        print(f'********** partial global profit: {self.global_profit:,.2f} **********')

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
            market=self.market
        )

        self.market.symbol_ticker_callback = self.session.symbol_ticker_callback
        self.market.order_traded_callback = self.session.order_traded_callback
        self.market.account_balance_callback = self.session.account_balance_callback

        self.session.session_stop_callback = self.session_stopped

        self.session_count += 1
        log.info(f'******** NEW SESSION ********')
        log.info(f'{session_id}')

    def fake_symbol_socket_callback(self, foo: float):
        pass

    def fake_order_socket_callback(self, foo_1: str, foo_2: float, foo_3: float):
        pass

    def fake_account_socket_callback(self, foo: AccountBalance):
        pass
