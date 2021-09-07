# sc_client_manager.py

import logging
import threading
from enum import Enum
from typing import Union, List, Dict, Callable, Optional
from binance.client import Client as BinanceSpotClient
from binance import ThreadedWebsocketManager

from config_manager import ConfigManager
from simulator.sc_fake_client import FakeClient
from simulator.thread_cmp_generator import ThreadCmpGenerator as Generator

log = logging.getLogger('log')


class ClientMode(Enum):
    CLIENT_MODE_BINANCE = 1
    CLIENT_MODE_SIMULATOR_GENERATOR = 2
    CLIENT_MODE_SIMULATOR_MANUAL = 3


class ClientManager:
    def __init__(self,
                 symbol_ticker_callback: Optional[Callable[[Dict], None]],
                 user_callback: Optional[Callable[[Dict], None]]
                 ):
        # callbacks
        self._symbol_ticker_callback: Optional[Callable[[Dict], None]] = symbol_ticker_callback
        self._user_callback: Optional[Callable[[Dict], None]] = user_callback

        self._config_manager = ConfigManager(config_file='config_new.ini')

        # get symbol names
        self.symbols_name = self._config_manager.get_symbol_names()

        # get app mode
        self._client_mode: ClientMode = ClientMode[self._config_manager.get_app_mode()]

        # define web sockets property
        self._twm: ThreadedWebsocketManager
        self._generators: List[Generator] = []  # cmp generators

        # set client
        self.client = self._setup_client(symbols_name=self.symbols_name)

    def stop(self) -> None:
        if self._client_mode == ClientMode.CLIENT_MODE_BINANCE:
            # stop all sockets
            self._twm.stop()

        elif self._client_mode == ClientMode.CLIENT_MODE_SIMULATOR_GENERATOR:
            [generator.terminate() for generator in self._generators]

    def hot_reconnect(self) -> None:
        self.stop()
        self._setup_client(symbols_name=self._config_manager.get_symbol_names())

    def on_button_step(self, symbol_name: str, step: float):
        if self._client_mode == ClientMode.CLIENT_MODE_SIMULATOR_MANUAL:
            self.client.update_cmp_from_button(symbol_name=symbol_name, step=step)

    def _symbol_ticker_socket_callback(self, msg: Dict):
        # coming from:
        #  - Binance socket in BINANCE MODE
        #  - Generator in SIMULATOR GENERATOR MODE

        # # update fake client cmp
        # if self._client_mode == ClientMode.CLIENT_MODE_SIMULATOR_GENERATOR:
        #     symbol_name = msg['s']
        #     new_cmp = float(msg['c'])
        #     self.client.update_cmp_from_generator(symbol_name=symbol_name, new_cmp=new_cmp)

        # check it is a valid reference
        if self._symbol_ticker_callback:
            self._symbol_ticker_callback(msg)

    def _user_socket_callback(self, msg: Dict):
        # check it is a valid reference
        if self._user_callback:
            self._user_callback(msg)

    def _setup_client(self, symbols_name: List[str]) -> Union[BinanceSpotClient, FakeClient]:
        # setup self.client depending on the client mode read from config.ini
        # and setup sockets (Binance) or generators (Simulator) for:
        #   - user data (events executionReport & outboundAccountPosition)
        #   - symbol ticker
        client: Union[BinanceSpotClient, FakeClient]

        if self._client_mode == ClientMode.CLIENT_MODE_BINANCE:
            # setup signature
            api = self._get_api_keys()
            client = BinanceSpotClient(api_key=api['key'], api_secret=api['secret'])

            # init socket manager
            self._twm = ThreadedWebsocketManager(api_key=api['key'], api_secret=api['secret'])
            self._twm.start()
            # # start user socket
            # self._twm.start_user_socket(callback=self._user_socket_callback)
            # # start ticker socket for each symbol
            # for symbol_name in symbols_name:
            #     self._twm.start_symbol_ticker_socket(symbol=symbol_name, callback=self._symbol_ticker_socket_callback)

        elif self._client_mode in [ClientMode.CLIENT_MODE_SIMULATOR_GENERATOR, ClientMode.CLIENT_MODE_SIMULATOR_MANUAL]:
            client = FakeClient(
                symbol_ticker_socket_callback=self._symbol_ticker_socket_callback,
                user_socket_callback=self._user_socket_callback
            )
            if self._client_mode == ClientMode.CLIENT_MODE_SIMULATOR_GENERATOR:
                # start ticker generator for each symbol and add to generators list
                for symbol_name in symbols_name:
                    new_generator = self._create_generator(symbol_name=symbol_name,
                                                           f_callback=client.update_cmp_from_generator)
                    self._generators.append(new_generator)

        else:
            raise Exception(f'client mode {self._client_mode.name} not accepted')
        return client

    def start_sockets(self):
        if self._client_mode == ClientMode.CLIENT_MODE_BINANCE:
            # start user socket
            self._twm.start_user_socket(callback=self._user_socket_callback)
            # start ticker socket for each symbol
            for symbol_name in self.symbols_name:
                self._twm.start_symbol_ticker_socket(symbol=symbol_name, callback=self._symbol_ticker_socket_callback)

    def _create_generator(self, symbol_name: str, f_callback: Callable[[Dict], None]) -> Generator:
        new_generator = Generator(
            symbol_name=symbol_name,
            interval=self._config_manager.get_simulator_update_rate(),
            f_callback=f_callback,
            # f_callback=self._symbol_ticker_socket_callback,
            choice_values=self._config_manager.get_simulator_choice_values(symbol_name=symbol_name),
            initial_cmp=self._config_manager.get_initial_cmp(symbol_name=symbol_name)
        )
        # start created generator
        x = threading.Thread(target=new_generator.run)
        x.start()
        return new_generator

    @staticmethod
    def _get_api_keys() -> Dict:
        return {
            "key": "JkbTNxP0s6x6ovKcHTWYzDzmzLuKLh6g9gjwHmvAdh8hpsOAbHzS9w9JuyYD9mPf",
            "secret": "IWjjdrYPyaWK4yMyYPIRhdiS0I7SSyrhb7HIOj4vjDcaFMlbZ1ygR6I8TZMUQ3mW"
        }
