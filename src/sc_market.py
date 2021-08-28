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
from sc_account_manager import Account
# from sc_balance_manager import Account, Asset
from config_manager import ConfigManager
from sc_market_out import MarketOut

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
                 order_traded_callback: Optional[Callable[[str, float, float], None]],
                 # account_balance_callback: Optional[Callable[[List[Account]], None]]
                 ):

        self.order_traded_callback: Callable[[str, float, float], None] = order_traded_callback
        self.account_balance_callback: Callable[[List[Account]], None]
        # self.account_balance_callback: Callable[[List[Account]], None] = account_balance_callback

        # get app parameters from config.ini
        config_manager = ConfigManager(config_file='config_new.ini')

        # BINANCE or SIMULATOR
        client_mode = config_manager.get_app_mode()
        self.client_mode = ClientMode[client_mode]

        self._is_binance_socket_manager_started = False

        # set the dict that will hold the cmp callback to each session
        # each value will be set when starting particular symbol ticker sockets
        self.symbol_ticker_callbacks: Dict[str, Callable[[float], None]] = {}

        # create client depending on client_mode parameter
        self.client: Union[Client, FakeClient] = self._set_client(client_mode=self.client_mode)

        # create market out for callings to Binance API
        self._api = MarketOut(
            client=self.client,
            hot_reconnect_callback=self.hot_reconnect
        )

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
            # stop all
            self._bsm.stop()

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
                symbol = msg['s']
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

    def binance_symbol_ticker_callback(self, msg: Any) -> None:
        # called from Binance API each time the cmp is updated
        if msg['e'] == 'error':
            log.critical(f'symbol ticker socket error: {msg["m"]}')
        elif msg['e'] == '24hrTicker':
            symbol_name = msg['s']
            if symbol_name not in ['BTCEUR', 'BNBEUR']:
                raise Exception(f'wrong symbol name {symbol_name}')
            # trigger actions for new market price
            cmp = float(msg['c'])
            # self.symbol_ticker_callbacks['BTCEUR'](cmp)
            self.symbol_ticker_callbacks[symbol_name](cmp)
        else:
            log.critical(f'event type not expected: {msg["e"]}')

    # ********** calls to binance api through MarketOut class **********

    def place_limit_order(self, order: Order) -> Optional[dict]:
        return self._api.place_limit_order(order=order)

    def place_market_order(self, order: Order) -> Optional[dict]:
        return self._api.place_market_order(order=order)

    def get_symbol_info(self, symbol_name: str) -> Optional[dict]:
        return self._api.get_symbol_info(symbol_name=symbol_name)

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

    # ********** simulator mode only **********

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
            client = FakeClient(
                user_socket_callback=self.binance_user_socket_callback,
                symbol_ticker_callback=self.binance_symbol_ticker_callback,
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

        # user socket
        self._bsm.start_user_socket(
            callback=self.binance_user_socket_callback
        )

    def start_symbol_ticker_socket(self, symbol_name: str, callback: Callable[[Any], None]) -> None:
        # check flag
        if self._is_binance_socket_manager_started:
            # add to dictionary the callback to be called from binance_symbol_ticker_callback
            # to send the cmp to the right session
            self.symbol_ticker_callbacks[symbol_name] = callback

            # start socket and set callback to self dictionary
            if self.client_mode == ClientMode.CLIENT_MODE_BINANCE:
                # start socket
                self._bsm.start_symbol_ticker_socket(
                    symbol=symbol_name,
                    callback=self.binance_symbol_ticker_callback
                )
            elif self.client_mode == ClientMode.CLIENT_MODE_SIMULATOR:
                # set the callback in FakeSimulator
                # todo: convert to dict if simulator allowed for multiple symbol sessions
                self.client.symbol_ticker_callback = self.binance_symbol_ticker_callback

        else:
            raise Exception(f'Binance Socket Manager not started before starting user ticker socket for {symbol_name}')
