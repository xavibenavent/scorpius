# sc_market.py

import logging
from typing import Callable, Any, Optional, List

from sc_order import Order
from sc_account_manager import Account
from config_manager import ConfigManager
from sc_market_out import MarketOut
from sc_client_manager import ClientManager

log = logging.getLogger('log')


class MarketApiOut:

    B_BALANCE_ARRAY = 'B'
    B_ASSET_NAME = 'a'
    B_FREE = 'f'
    B_LOCKED = 'l'

    def __init__(self,
                 # order_traded_callback: Optional[Callable[[str, str, float, float], None]],
                 # account_balance_callback: Optional[Callable[[List[Account]], None]],
                 # symbol_ticker_callback: Callable[[str, float], None]
                 client_manager: ClientManager
                 ):
        self.client_manager = client_manager

        # the three callback functions are in the Session Manager class
        # self.order_traded_callback: Callable[[str, str, float, float], None] = order_traded_callback
        # self.account_balance_callback: Callable[[List[Account]], None] = account_balance_callback
        # self.symbol_ticker_callback: Callable[[str, float], None] = symbol_ticker_callback

        # get app parameters from config.ini
        config_manager = ConfigManager(config_file='config_new.ini')

        # create market out for callings to Binance API
        self._api = MarketOut(
            client=self.client_manager.client,
            hot_reconnect_callback=self.client_manager.hot_reconnect
        )

    # ********** callback functions **********


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
