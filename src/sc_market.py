# sc_market.py

import sys
import logging
import time
from typing import Callable, Union, Any, Optional, List, Dict
from binance.client import Client
from binance import ThreadedWebsocketManager
from binance import enums as k_binance
from enum import Enum
from binance.exceptions import *

from urllib3.exceptions import ProtocolError
import socket

from requests.exceptions import ConnectionError, ReadTimeout

from sc_order import Order
from sc_fake_client import FakeClient
from sc_balance_manager import Account
from config_manager import ConfigManager

import configparser

log = logging.getLogger('log')


class ClientMode(Enum):
    CLIENT_MODE_BINANCE = 1
    CLIENT_MODE_SIMULATOR = 2


class Market:

    B_BALANCE_ARRAY = 'B'
    B_ASSET_NAME = 'a'
    B_FREE = 'f'
    B_LOCKED = 'l'

    def __init__(self,
                 # symbol_ticker_callback: Optional[Callable[[float], None]],
                 order_traded_callback: Optional[Callable[[str, float, float], None]],
                 account_balance_callback: Optional[Callable[[List[Account]], None]]):

        # self.symbol_ticker_callback: Callable[[float], None] = symbol_ticker_callback
        self.order_traded_callback: Callable[[str, float, float], None] = order_traded_callback
        self.account_balance_callback: Callable[[List[Account]], None] = account_balance_callback

        # get app parameters from config.ini
        config_manager = ConfigManager(config_file='config_new.ini')

        # BINANCE or SIMULATOR
        client_mode = config_manager.get_app_mode()
        self.client_mode = ClientMode[client_mode]

        # Usually BTCEUR
        # raise Exception('fix it')
        # self.symbol = config['BINANCE']['symbol']
        # self.symbol = 'BTCEUR'
        self._is_binance_socket_manager_started = False

        self.symbol_ticker_callbacks: Dict[str, Callable[[Any], None]] = {}

        # create client depending on client_mode parameter
        self.client: Union[Client, FakeClient] = self._set_client(client_mode=self.client_mode)


    def hot_reconnect(self):
        log.critical("hot re-connection to Binance")
        print("hot re-connection to Binance")

        self.client = self._set_client(client_mode=self.client_mode)
        self.start_sockets()

        log.critical('sockets re-connected')
        print('sockets re-connected')

    def start_sockets(self):
        time.sleep(1)
        if self.client_mode == ClientMode.CLIENT_MODE_BINANCE:  # not self.simulator_mode:
            # sockets only started in binance mode (not in simulator mode)
            self._start_sockets()
        elif self.client_mode == ClientMode.CLIENT_MODE_SIMULATOR:
            self.client.start_cmp_generator()
        self._is_binance_socket_manager_started = True
        log.info(f'client initiated in {self.client_mode} mode')

    def stop(self):
        if self.client_mode == ClientMode.CLIENT_MODE_BINANCE:
            self._bsm.stop_socket(self._symbol_ticker_s)
            self._bsm.stop_socket(self._user_s)

            # properly close the WebSocket, only if it is running
            # trying to stop it when it is not running, will raise an error
            # if reactor.running:
            #     reactor.stop()

        elif self.client_mode == ClientMode.CLIENT_MODE_SIMULATOR:
            self.client.stop_cmp_generator()

        # todo: it does not work
        # sys.exit()

    # ********** callback functions **********

    def binance_user_socket_callback(self, msg) -> None:
        # called from Binance API each time an order is traded and
        # each time the account balance changes
        event_type: str = msg['e']
        # print(event_type)
        if event_type == 'executionReport':
            if (msg['x'] == 'TRADE') and (msg["X"] == 'FILLED'):
                # order traded
                uid = str(msg['c'])
                order_price = float(msg['L'])
                bnb_commission = float(msg['n'])
                # trigger actions for traded order in session
                self.order_traded_callback(uid, order_price, bnb_commission)
            elif (msg['x'] == 'NEW') and (msg["X"] == 'NEW'):
                # order accepted (PLACE confirmation)
                # not used by the moment
                pass

        elif event_type == 'outboundAccountPosition':
            binance_accounts = msg[self.B_BALANCE_ARRAY]
            # convert to list of accounts
            accounts = [
                Account(name=ba[self.B_ASSET_NAME], free=float(ba[self.B_FREE]), locked=float(ba[self.B_LOCKED]))
                for ba in binance_accounts]

            self.account_balance_callback(accounts)

    # def binance_symbol_ticker_callback(self, msg: Any) -> None:
    #     # called from Binance API each time the cmp is updated
    #     if msg['e'] == 'error':
    #         log.critical(f'symbol ticker socket error: {msg["m"]}')
    #     elif msg['e'] == '24hrTicker':
    #         # trigger actions for new market price
    #         cmp = float(msg['c'])
    #         self.symbol_ticker_callback(cmp)
    #     else:
    #         log.critical(f'event type not expected: {msg["e"]}')

    # ********** calls to binance api **********

    def place_limit_order(self, order: Order) -> Optional[dict]:
        try:
            # msg = {}
            msg = self.client.create_order(
                # symbol=self.symbol,
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
            self.hot_reconnect()
        return None  # msg['orderId'], msg['status'] == 'FILLED' or 'NEW'

    def place_market_order(self, order: Order) -> Optional[dict]:
        try:
            msg = {}
            if order.k_side == k_binance.SIDE_BUY:
                msg = self.client.order_market_buy(
                    symbol=order.symbol.name,
                    # symbol=self.symbol,
                    quantity=order.get_amount(signed=False),
                    newClientOrderId=order.uid)
            elif order.k_side == k_binance.SIDE_SELL:
                msg = self.client.order_market_sell(
                    symbol=order.symbol.name,
                    # symbol=self.symbol,
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
            self.hot_reconnect()
        return None  # msg['orderId'], msg['status'] == 'FILLED' or 'NEW'

    def get_symbol_info(self, symbol_name: str) -> Optional[dict]:
        # return dict with the required values for checking order values
        try:
            d = self.client.get_symbol_info(symbol_name)
            if d:
                base_asset = d.get('baseAsset')
                quote_asset = d.get('quoteAsset')
                base_precision = int(d.get('baseAssetPrecision'))  # symbol 1
                max_price = float(d.get('filters')[0].get('maxPrice'))
                min_price = float(d.get('filters')[0].get('minPrice'))
                max_qty = float(d.get('filters')[2].get('maxQty'))
                min_qty = float(d.get('filters')[2].get('minQty'))
                min_notional = float(d.get('filters')[3].get('minNotional'))  # price * qty
                quote_precision = int(d.get('quoteAssetPrecision'))  # symbol 2
                return dict(base_precision=base_precision,
                            max_price=max_price,
                            min_price=min_price,
                            max_qty=max_qty,
                            min_qty=min_qty,
                            min_notional=min_notional,
                            quote_precision=quote_precision,
                            base_asset=base_asset,
                            quote_asset=quote_asset)
            else:
                log.critical(f'no symbol info from Binance for {symbol_name}')
        except (BinanceAPIException, BinanceRequestException) as e:
            log.critical(e)
        except (ConnectionError, ReadTimeout, ProtocolError, socket.error) as e:
            log.critical(e)
            self.hot_reconnect()
        return None

    def get_account_info(self) -> Optional[List[Account]]:
        try:
            msg = self.client.get_account()
            binance_accounts = msg['balances']
            # convert to list of accounts
            accounts = [
                Account(name=ba['asset'], free=float(ba['free']), locked=float(ba['locked']))
                for ba in binance_accounts
                # if ba['asset'] in ['BTC', 'EUR', 'BNB']
                if float(ba['free']) > 0 or float(ba['locked']) > 0
            ]
            for a in accounts:
                print(f'{a.name} {a.free} {a.locked}')
            return accounts
        except (BinanceAPIException, BinanceRequestException) as e:
            log.critical(e)
        except (ConnectionError, ReadTimeout, ProtocolError, socket.error) as e:
            log.critical(e)
            self.hot_reconnect()
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
            self.hot_reconnect()
        return None

    def get_asset_liquidity(self, asset: str) -> float:
        # return free
        return self.get_asset_balance(asset_name=asset).free

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
            self.hot_reconnect()

    def cancel_orders(self, orders: List[Order]):
        log.info('********** CANCELLING PLACED ORDER(S) **********')
        for order in orders:
            try:
                # self.client.cancel_order(symbol='BTCEUR', origClientOrderId=order.uid)
                self.client.cancel_order(symbol=order.symbol.name, origClientOrderId=order.uid)
                log.info(f'** ORDER CANCELLED IN BINANCE {order}')
            except (BinanceAPIException, BinanceRequestException) as e:
                log.critical(e)
            except (ConnectionError, ReadTimeout, ProtocolError, socket.error) as e:
                log.critical(e)
                self.hot_reconnect()

    def update_fake_client_cmp(self, step: float):
        # only in SIMULATOR mode
        if self.client_mode == ClientMode.CLIENT_MODE_SIMULATOR:
            self.client.update_cmp_from_dashboard(step=step)

    # ********** binance configuration methods **********

    def _set_client(self, client_mode) -> (Union[Client, FakeClient], bool):
        client: Union[Client, FakeClient]

        if client_mode == ClientMode.CLIENT_MODE_BINANCE:  # 'binance':
            api_keys = {
                "key": "JkbTNxP0s6x6ovKcHTWYzDzmzLuKLh6g9gjwHmvAdh8hpsOAbHzS9w9JuyYD9mPf",
                "secret": "IWjjdrYPyaWK4yMyYPIRhdiS0I7SSyrhb7HIOj4vjDcaFMlbZ1ygR6I8TZMUQ3mW"
            }
            client = Client(api_keys['key'], api_keys['secret'])

        elif client_mode == ClientMode.CLIENT_MODE_SIMULATOR:  # 'simulated':
            self.symbol_ticker_callbacks['BTCEUR'] = self._fake_symbol_ticker_callback
            client = FakeClient(
                user_socket_callback=self.binance_user_socket_callback,
                # symbol_ticker_callback=self.binance_symbol_ticker_callback,
                symbol_ticker_callback=self.symbol_ticker_callbacks['BTCEUR'],
            )
        else:
            log.critical(f'client_mode {client_mode} not accepted')
            sys.exit()
        return client

    def _fake_symbol_ticker_callback(self, msg: Any):
        pass

    def _start_sockets(self):
        # init socket manager
        self._bsm = ThreadedWebsocketManager(api_key=self.client.API_KEY, api_secret=self.client.API_SECRET)
        self._bsm.start()

        # set flag
        # self._is_binance_socket_manager_started = True

        # _symbol_ticker_s and _user_s strings will be used to stop the sockets
        # self.start_symbol_ticker_socket()

        # user socket
        self._user_s = self._bsm.start_user_socket(
            callback=self.binance_user_socket_callback
        )

    def start_symbol_ticker_socket(self, symbol_name: str, callback: Callable[[Any], None]) -> str:
        # check flag
        if self._is_binance_socket_manager_started:
            # add to dictionary
            if symbol_name in self.symbol_ticker_callbacks.keys():
                self.symbol_ticker_callbacks[symbol_name] = callback
            else:
                self.symbol_ticker_callbacks[symbol_name] = callback

            # start socket and set callback to self dictionary
            symbol_ticker_s = self._bsm.start_symbol_ticker_socket(
                symbol=symbol_name,
                callback=self.symbol_ticker_callbacks[symbol_name]  # method in session
            )
            return symbol_ticker_s
        else:
            raise Exception(f'Binance Socket Manager not started before starting user ticker socket for {symbol_name}')
