# sc_market.py

import logging
from typing import Callable, Any, Optional, List

from sc_order import Order
from sc_account_manager import Account
from config_manager import ConfigManager
from sc_market_out import MarketOut
from sc_client_manager import ClientManager

log = logging.getLogger('log')


class Market:

    B_BALANCE_ARRAY = 'B'
    B_ASSET_NAME = 'a'
    B_FREE = 'f'
    B_LOCKED = 'l'

    def __init__(self,
                 order_traded_callback: Optional[Callable[[str, str, float, float], None]],
                 account_balance_callback: Optional[Callable[[List[Account]], None]],
                 symbol_ticker_callback: Callable[[str, float], None]
                 ):

        self.client_manager = ClientManager(
            symbol_ticker_callback=self.binance_symbol_ticker_callback,
            user_callback=self.binance_user_socket_callback
        )

        # the three callback functions are in the Session Manager class
        self.order_traded_callback: Callable[[str, str, float, float], None] = order_traded_callback
        self.account_balance_callback: Callable[[List[Account]], None] = account_balance_callback
        self.symbol_ticker_callback: Callable[[str, float], None] = symbol_ticker_callback

        # get app parameters from config.ini
        config_manager = ConfigManager(config_file='config_new.ini')

        # create market out for callings to Binance API
        self._api = MarketOut(
            client=self.client_manager.client,
            hot_reconnect_callback=self.client_manager.hot_reconnect
        )

    # ********** callback functions **********

    def binance_user_socket_callback(self, msg) -> None:
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

        elif event_type == 'outboundAccountPosition':
            binance_accounts = msg[self.B_BALANCE_ARRAY]
            # convert to list of accounts
            accounts = [
                Account(name=ba[self.B_ASSET_NAME], free=float(ba[self.B_FREE]), locked=float(ba[self.B_LOCKED]))
                for ba in binance_accounts]

            # ********** account balance callback **********
            self.account_balance_callback(accounts)

    def binance_symbol_ticker_callback(self, msg: Any) -> None:
        # called from Binance API each time the cmp is updated
        event_type = msg['e']

        if event_type == 'error':
            log.critical(f'symbol ticker socket error: {msg["m"]}')

        elif event_type == '24hrTicker':
            # get symbol & check it
            symbol_name = msg['s']
            if symbol_name not in ['BTCEUR', 'BNBEUR']:
                raise Exception(f'wrong symbol name {symbol_name}')

            # get last market price
            last_market_price = float(msg['c'])

            # **********  symbol ticker callback **********
            self.symbol_ticker_callback(symbol_name, last_market_price)

        else:
            log.critical(f'event type not expected: {event_type}')

    # ********** calls to binance api through MarketOut class **********

    def place_limit_order(self, order: Order) -> Optional[dict]:
        return self._api.place_limit_order(order=order)

    def place_market_order(self, order: Order) -> Optional[dict]:
        return self._api.place_market_order(order=order)

    def get_symbol_info(self, symbol_name: str) -> Optional[dict]:
        return self._api.get_all_symbol_info(symbol_name=symbol_name)

    def get_account_info(self) -> Optional[List[Account]]:
        return self._api.get_account_info()

    def get_asset_balance(self, asset_name: str) -> Optional[Account]:
        return self._api.get_asset_balance(asset_name=asset_name)

    def get_asset_liquidity(self, asset_name: str) -> float:
        return self._api.get_asset_liquidity(asset_name=asset_name)

    def get_cmp(self, symbol_name: str) -> float:
        return self._api.get_cmp(symbol_name=symbol_name)

    def cancel_orders(self, orders: List[Order]):
        return self._api.cancel_orders(orders=orders)
