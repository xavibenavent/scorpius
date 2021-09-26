# sc_market_sockets_in.py

from typing import Optional, Callable, List, Dict
import logging

from managers.sc_account_manager import Account

log = logging.getLogger('log')


class MarketSocketsIn:
    B_BALANCE_ARRAY = 'B'
    B_ASSET_NAME = 'a'
    B_FREE = 'f'
    B_LOCKED = 'l'

    def __init__(self,
                 order_traded_callback: Optional[Callable[[str, str, float, float], None]],
                 account_balance_callback: Optional[Callable[[List[Account]], None]],
                 symbol_ticker_callback: Callable[[str, float], None],
                 update_previous_callback: Callable[[], None],
                 order_canceled_callback: Callable[[str, str, str, float, float], None]
                 ):

        # the three callback functions are in the Session Manager class
        self.order_traded_callback: Callable[[str, str, float, float], None] = order_traded_callback
        self.account_balance_callback: Callable[[List[Account]], None] = account_balance_callback
        self.symbol_ticker_callback: Callable[[str, float], None] = symbol_ticker_callback
        self.update_previous_callback: Callable[[], None] = update_previous_callback
        self.order_canceled_callback: Callable[[str, str, str, float, float], None] = order_canceled_callback

    def binance_user_socket_callback(self, msg: Dict) -> None:
        # depending on the event type, it will call the right callback function
        # in session manager
        event_type = msg['e']

        if event_type == 'executionReport':
            if (msg['x'] == 'TRADE') and (msg["X"] == 'FILLED'):
                # order traded
                symbol = msg['s']
                uid = str(msg['c'])
                order_price = float(msg['L'])
                bnb_commission = float(msg['n'])

                # ********** order traded callback **********
                self.order_traded_callback(symbol, uid, order_price, bnb_commission)

            # to force get all open orders and update dashboard
            if msg['x'] in ['NEW', 'TRADE']:
                self.update_previous_callback()

            if msg['x'] == 'CANCELED':
                self.update_previous_callback()

                symbol_name = msg['s']
                uid = str(msg['c'])
                k_side = msg['S']
                price = float(msg['p'])
                qty = float(msg['q'])
                self.order_canceled_callback(symbol_name, uid, k_side, price, qty)

        elif event_type == 'outboundAccountPosition':
            binance_accounts = msg[self.B_BALANCE_ARRAY]
            # convert to list of accounts
            accounts = [
                Account(name=ba[self.B_ASSET_NAME], free=float(ba[self.B_FREE]), locked=float(ba[self.B_LOCKED]))
                for ba in binance_accounts]

            # ********** account balance callback **********
            self.account_balance_callback(accounts)

    def binance_symbol_ticker_callback(self, msg: Dict) -> None:
        # called from Binance API each time the cmp is updated
        event_type = msg['e']

        if event_type == 'error':
            log.critical(f'symbol ticker socket error: {msg["m"]}')

        elif event_type == '24hrTicker':
            # get symbol & check it
            symbol_name = msg['s']
            if symbol_name not in ['BTCEUR', 'BNBEUR', 'ETHBTC']:
                raise Exception(f'wrong symbol name {symbol_name}')

            # get last market price
            last_market_price = float(msg['c'])

            # **********  symbol ticker callback **********
            self.symbol_ticker_callback(symbol_name, last_market_price)

        else:
            log.critical(f'event type not expected: {event_type}')
