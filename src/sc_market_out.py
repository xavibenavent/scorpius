# sc_market_out.py
import pprint

from binance.client import Client
from binance import enums as k_binance
from binance.exceptions import *
from typing import Callable, Optional, List, Dict
from requests.exceptions import ConnectionError, ReadTimeout
from urllib3.exceptions import ProtocolError
import socket
import logging

from sc_order import Order
from sc_account_manager import Account


log = logging.getLogger('log')


class MarketOut:
    def __init__(self,
                 client: Client,
                 hot_reconnect_callback: Callable[[], None]
                 ):
        self.client = client
        self.hot_reconnect_callback = hot_reconnect_callback

    def get_all_symbol_info(self, symbol_name: str) -> Optional[dict]:
        # return dict with the required values for checking order values
        try:
            d = self.client.get_symbol_info(symbol_name)
            if d:
                return d
            else:
                log.critical(f'no symbol info from Binance for {symbol_name}')
        except (BinanceAPIException, BinanceRequestException) as e:
            log.critical(e)
        except (ConnectionError, ReadTimeout, ProtocolError, socket.error) as e:
            log.critical(e)
            self.hot_reconnect_callback()
        return None

    def place_limit_order(self, order: Order) -> Optional[dict]:
        try:
            msg = self.client.create_order(
                symbol=order.symbol.name,
                side=order.k_side,
                type=k_binance.ORDER_TYPE_LIMIT,
                timeInForce=k_binance.TIME_IN_FORCE_GTC,
                quantity=order.get_amount(signed=False),
                price=order.get_price_str(),
                newClientOrderId=order.uid)
            if msg:
                d = dict(binance_id=msg['orderId'], status=msg.get('status'))
                return d
            else:
                log.critical(f'error when placing order {order}')
        except (
                BinanceRequestException, BinanceAPIException,
                BinanceOrderException, BinanceOrderMinAmountException,
                BinanceOrderMinPriceException, BinanceOrderMinTotalException,
                BinanceOrderUnknownSymbolException,
                BinanceOrderInactiveSymbolException) as e:
            log.critical(e)
        except (ConnectionError, ReadTimeout, ProtocolError, socket.error) as e:
            log.critical(e)
            self.hot_reconnect_callback()
        return None  # msg['orderId'], msg['status'] == 'FILLED' or 'NEW'

    def place_market_order(self, order: Order) -> Optional[dict]:
        try:
            msg = {}
            if order.k_side == k_binance.SIDE_BUY:
                msg = self.client.order_market_buy(
                    symbol=order.symbol.name,
                    quantity=order.get_amount(signed=False),
                    newClientOrderId=order.uid)
            elif order.k_side == k_binance.SIDE_SELL:
                msg = self.client.order_market_sell(
                    symbol=order.symbol.name,
                    quantity=order.get_amount(signed=False),
                    newClientOrderId=order.uid)
            if msg:
                d = dict(binance_id=msg['orderId'], status=msg.get('status'))
                return d
            else:
                log.critical(f'error when placing order {order}')
        except (
                BinanceRequestException, BinanceAPIException,
                BinanceOrderException, BinanceOrderMinAmountException,
                BinanceOrderMinPriceException, BinanceOrderMinTotalException,
                BinanceOrderUnknownSymbolException,
                BinanceOrderInactiveSymbolException) as e:
            log.critical(e)
        except (ConnectionError, ReadTimeout, ProtocolError, socket.error) as e:
            log.critical(e)
            self.hot_reconnect_callback()
        return None  # msg['orderId'], msg['status'] == 'FILLED' or 'NEW'

    def get_account_info(self) -> Optional[List[Account]]:
        try:
            msg = self.client.get_account()
            # check permissions
            if not msg['canTrade']:
                raise Exception(f'trading is no allowed by Binance: {msg}')
            binance_accounts = msg['balances']
            # convert to list of accounts
            accounts = [
                Account(name=ba['asset'], free=float(ba['free']), locked=float(ba['locked']))
                for ba in binance_accounts
                if float(ba['free']) > 0 or float(ba['locked']) > 0
            ]
            return accounts
        except (BinanceAPIException, BinanceRequestException) as e:
            log.critical(e)
        except (ConnectionError, ReadTimeout, ProtocolError, socket.error) as e:
            log.critical(e)
            self.hot_reconnect_callback()
        return None

    def get_asset_balance(self, asset_name: str) -> Optional[Account]:
        try:
            d = self.client.get_asset_balance(asset=asset_name)
            free = float(d.get('free'))
            locked = float(d.get('locked'))
            return Account(name=asset_name, free=free, locked=locked)
        except (BinanceAPIException, BinanceRequestException) as e:
            log.critical(e)
        except (ConnectionError, ReadTimeout, ProtocolError, socket.error) as e:
            log.critical(e)
            self.hot_reconnect_callback()
        return None

    def get_asset_liquidity(self, asset_name: str) -> float:
        return self.get_asset_balance(asset_name=asset_name).free

    def get_cmp(self, symbol_name: str) -> float:
        try:
            cmp = self.client.get_avg_price(symbol=symbol_name)
            if cmp:
                return float(cmp['price'])
            else:
                return 0.0
        except (BinanceAPIException, BinanceRequestException) as e:
            log.critical(e)
        except (ConnectionError, ReadTimeout, ProtocolError, socket.error) as e:
            log.critical(e)
            self.hot_reconnect_callback()

    def cancel_orders(self, orders: List[Order]):
        log.info('********** CANCELLING PLACED ORDER(S) **********')
        for order in orders:
            try:
                self.client.cancel_order(symbol=order.symbol.name, origClientOrderId=order.uid)
                log.info(f'** ORDER CANCELLED IN BINANCE {order}')
            except (BinanceAPIException, BinanceRequestException) as e:
                log.critical(e)
            except (ConnectionError, ReadTimeout, ProtocolError, socket.error) as e:
                log.critical(e)
                self.hot_reconnect_callback()
