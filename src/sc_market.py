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
                 client_manager: ClientManager
                 ):
        self.client_manager = client_manager

        # get app parameters from config.ini
        config_manager = ConfigManager(config_file='config_new.ini')

        # create market out for callings to Binance API
        self._api = MarketOut(
            client=self.client_manager.client,
            hot_reconnect_callback=self.client_manager.hot_reconnect
        )

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
