# sc_fake_client.py

import logging
import time
from typing import List, Callable, Dict
from enum import Enum
from random import choice
import threading

from sc_account_manager import Account, AccountManager
from config_manager import ConfigManager
from simulator.thread_cmp_generator import ThreadCmpGenerator
from simulator.sc_fake_simulator_out import FakeSimulatorOut
from sc_symbol import Symbol, Asset

log = logging.getLogger('log')


class FakeCmpMode(Enum):
    MODE_MANUAL = 0  # in this mode two buttons (+, -) control the market price
    MODE_GENERATOR = 1  # every K_UPDATE_RATE seconds generates a new cmp


class FakeOrder:
    def __init__(self, uid: str, side: str, price: float, quantity: float, symbol_name: str):
        self.uid = uid
        self.side = side
        self.price = price
        self.quantity = quantity
        self.symbol_name = symbol_name

    def get_total(self) -> float:
        return self.price * self.quantity


class FakeClient:
    def __init__(self,
                 user_socket_callback,
                 symbol_ticker_callback
                 ):

        self._user_socket_callback = user_socket_callback
        self.symbol_ticker_callback = symbol_ticker_callback

        # DATA
        self._placed_orders: List[FakeOrder] = []
        self._placed_orders_count = 0

        self.symbols: Dict[str, Symbol] = {}
        self.generators: List[ThreadCmpGenerator] = []  # cmp generators
        self.choice_values: Dict[str, List[float]] = {}
        self.cmp: Dict[str, float] = {}

        # set configuration manager
        self.cm = ConfigManager(config_file='config_new.ini')

        # set fake simulator out
        self.fso = FakeSimulatorOut(config_manager=self.cm)

        # FAKE CMP MODE SETTING
        simulator_mode = self.cm.get_fake_cmp_mode()
        self._fake_cmp_mode: FakeCmpMode = FakeCmpMode[simulator_mode]

        # get symbols simulator data dictionary: cmp & choice values
        symbols_name = self.cm.get_symbol_names()
        for symbol_name in symbols_name:
            self.choice_values[symbol_name] = self.cm.get_simulator_choice_values(symbol_name=symbol_name)
            self.cmp[symbol_name] = self.cm.get_initial_cmp(symbol_name=symbol_name)
            self.symbols[symbol_name] = self._get_symbol(symbol_name=symbol_name)

        # set accounts list
        msg = self.fso.get_account()
        binance_accounts = msg['balances']
        accounts: List[Account] = [
            Account(name=account['asset'], free=float(account['free']), locked=float(account['locked']))
            for account in binance_accounts
            if float(account['free']) > 0 or float(account['locked']) > 0
        ]
        self.account_manager = AccountManager(accounts=accounts)

        self.update_rate: float = self.cm.get_simulator_update_rate()
        self._FEE: float = float(self.cm.get_simulator_global_data()['fee'])

        # self.api_key = ''
        # self.api_secret = ''

    def _get_symbol(self, symbol_name: str) -> Symbol:
        # get filters from Binance API
        symbol_filters = self.fso.get_symbol_info(symbol_name=symbol_name)

        # get session data from config.ini
        symbol_config_data = self.cm.get_symbol_data(symbol_name=symbol_name)

        # fix Binance mistake in EUR precision by reading the values from config.ini
        symbol_filters['baseAssetPrecision'] = int(symbol_config_data['base_pt'])
        symbol_filters['quoteAssetPrecision'] = int(symbol_config_data['quote_pt'])

        # set symbol to pass at sessions start
        symbol = Symbol(
            name=symbol_name,
            base_asset=Asset(
                name=symbol_filters.get('baseAsset'),
                pv=int(symbol_config_data['base_pv'])
            ),
            quote_asset=Asset(
                name=symbol_filters.get('quoteAsset'),
                pv=int(symbol_config_data['quote_pv'])
            ),
            symbol_info=symbol_filters,
            config_data=symbol_config_data
        )
        return symbol

    # ********** cmp generator **********

    def create_start_generator(self, symbol_name: str):
        if self._fake_cmp_mode == FakeCmpMode.MODE_GENERATOR:
            # create
            new_generator = ThreadCmpGenerator(
                symbol_name=symbol_name,
                interval=self.update_rate,
                f_callback=self._update_cmp,
                choice_values=self.cm.get_simulator_choice_values(symbol_name=symbol_name)
            )
            # start
            x = threading.Thread(target=new_generator.run)
            x.start()

            # add to list
            self.generators.append(new_generator)

    def stop_cmp_generator(self):
        if self._fake_cmp_mode == FakeCmpMode.MODE_GENERATOR:
            # stop all generators
            [generator.terminate() for generator in self.generators]

    def update_cmp_from_dashboard(self, step: float, symbol_name: str):
        if self._fake_cmp_mode == FakeCmpMode.MODE_MANUAL:
            self._update_cmp(step=step, symbol_name=symbol_name)
        else:
            log.warning('trying to manually update cmp in GENERATOR MODE')

    def _update_cmp(self, step: float, symbol_name: str):
        # when in MANUAL mode the cmp is updated from the dashboard
        self.cmp[symbol_name] += step
        self._process_cmp_change(symbol_name=symbol_name)

    def get_mode(self) -> FakeCmpMode:
        return self._fake_cmp_mode

    # ********** orders trading **********

    def order_market_buy(self, **kwargs) -> dict:
        symbol_name = kwargs.get('symbol')
        order = FakeOrder(
            uid=kwargs.get('newClientOrderId'),
            side='BUY',
            price=self.cmp[symbol_name],
            quantity=kwargs.get('quantity'),
            symbol_name=symbol_name
        )
        status = 'NEW'

        # get account free value from symbol name
        base_account, quote_account = self._get_accounts(symbol_name=symbol_name)

        # check enough balance
        if order.side == 'BUY' and quote_account.free < order.get_total():
            log.critical(f'not enough balance to place the order')
            return {}
        elif order.side == 'SELL' and base_account.free < order.quantity:
            log.critical(f'not enough amount to place the order')
            return {}

        # place
        self._placed_orders_count += 1
        self._place_order(order=order)
        self._trade_order(order=order)
        status = 'FILLED'

        return {
            "symbol": symbol_name,
            "orderId": self._placed_orders_count,
            "clientOrderId": order.uid,
            "transactTime": 1507725176595,
            "price": order.price,
            "origQty": order.quantity,
            "executedQty": '0.0',
            "status": status,
            "timeInForce": "GTC",
            "type": "LIMIT",
            "side": order.side
        }

    def _get_accounts(self, symbol_name: str) -> (float, float):
        # 1. get base asset & quote asset from symbols
        base_asset = self.symbols[symbol_name].base_asset()
        quote_asset = self.symbols[symbol_name].quote_asset()

        # 2. get accounts from account manager
        base_account = self.account_manager.get_account(name=base_asset.name())
        quote_account = self.account_manager.get_account(name=quote_asset.name())
        return base_account, quote_account

    def order_market_sell(self, **kwargs) -> dict:
        symbol_name = kwargs.get('symbol')
        order = FakeOrder(
            uid=kwargs.get('newClientOrderId'),
            side='SELL',
            price=self.cmp[symbol_name],
            quantity=kwargs.get('quantity'),
            symbol_name=symbol_name
        )
        status = 'NEW'

        # get account free value from symbol name
        base_account, quote_account = self._get_accounts(symbol_name=symbol_name)

        # check enough balance
        if order.side == 'BUY' \
                and quote_account.free < order.get_total():
            log.critical(f'not enough balance to place the order')
            return {}
        elif order.side == 'SELL' \
                and base_account.free < order.quantity:
            log.critical(f'not enough amount to place the order')
            return {}

        # place
        self._placed_orders_count += 1
        self._place_order(order=order)
        self._trade_order(order=order)
        status = 'FILLED'

        return {
            "symbol": symbol_name,
            "orderId": self._placed_orders_count,
            "clientOrderId": order.uid,
            "transactTime": 1507725176595,
            "price": order.price,
            "origQty": order.quantity,
            "executedQty": '0.0',
            "status": status,
            "timeInForce": "GTC",
            "type": "LIMIT",
            "side": order.side
        }

    def create_order(self, **kwargs) -> dict:
        symbol_name = kwargs.get('symbol')
        order = FakeOrder(
            uid=kwargs.get('newClientOrderId'),
            side=kwargs.get('side'),
            price=float(kwargs.get('price').replace(',', '')),
            quantity=kwargs.get('quantity'),
            symbol_name=symbol_name
        )
        status = 'NEW'

        # check whether it has already been placed
        for placed_order in self._placed_orders:
            if placed_order.uid == order.uid:
                log.critical(f'order with uid {placed_order.uid} has already been placed')
                return {}

        # get account free value from symbol name
        base_account, quote_account = self._get_accounts(symbol_name=symbol_name)

        # check enough balance
        if order.side == 'BUY' \
                and quote_account.free < order.get_total():
            log.critical(f'not enough balance to place the order')
            return {}
        elif order.side == 'SELL' \
                and base_account.free < order.quantity:
            log.critical(f'not enough amount to place the order')
            return {}

        # place
        self._placed_orders_count += 1
        self._place_order(order=order)

        # check if the order has to be placed immediately:
        if order.side == 'BUY' and self.cmp[symbol_name] < order.price:
            log.info(f'the order has been traded when placing it')
            self._trade_order(order=order)
            status = 'FILLED'
        elif order.side == 'SELL' and self.cmp[symbol_name] > order.price:
            log.info(f'the order has been traded when placing it')
            self._trade_order(order=order)
            status = 'FILLED'

        return {
                "symbol": symbol_name,
                "orderId": self._placed_orders_count,
                "clientOrderId": order.uid,
                "transactTime": 1507725176595,
                "price": order.price,
                "origQty": order.quantity,
                "executedQty": '0.0',
                "status": status,
                "timeInForce": "GTC",
                "type": "LIMIT",
                "side": order.side
            }

    def cancel_order(self, symbol: str, origClientOrderId: str) -> dict:
        # TODO: check that the order exist in list and remove from it
        for order in self._placed_orders:
            if order.uid == origClientOrderId:
                self._placed_orders.remove(order)

                # get account free value from symbol name
                base_account, quote_account = self._get_accounts(symbol_name=symbol)

                # update balance
                if order.side == 'BUY':
                    quote_account.free += order.get_total()
                    quote_account.locked -= order.get_total()
                else:
                    base_account.free += order.quantity
                    base_account.locked -= order.quantity
                # call user socket callback
                self._call_user_socket_balance_update()
                return {
                        "symbol": symbol,
                        "origClientOrderId": origClientOrderId,
                        "orderId": 1,
                        "clientOrderId": "cancelMyOrder1"
                    }
        # if not found
        log.critical(f'trying to cancel an order not placed {origClientOrderId}')
        return {}

    # ********** symbol, account & balance **********

    def get_symbol_info(self, symbol: str) -> dict:
        return self.fso.get_symbol_info(symbol_name=symbol)

    def get_account(self):
        return self.fso.get_account()

    def get_asset_balance(self, asset: str) -> dict:
        return self.fso.get_asset_balance(asset=asset, account_manager=self.account_manager)

    def get_avg_price(self, symbol: str) -> dict:
        if symbol in self.symbols.keys():
            return {'mins': 5, 'price': str(self.cmp[symbol])}
        else:
            price = str(0.0)
            log.critical(f'symbol not in simulator, returning {price}')
            return {'mins': 5, 'price': str(0.0)}

    def _process_cmp_change(self, symbol_name: str):
        self._check_placed_orders_for_trading()
        msg = dict(
            e='24hrTicker',
            s=symbol_name,
            c=str(self.cmp[symbol_name])
        )
        self.symbol_ticker_callback(msg)

    def _check_placed_orders_for_trading(self):
        for order in self._placed_orders:
            symbol_name = order.symbol_name
            if order.side == 'BUY' and self.cmp[symbol_name] <= order.price:
                self._trade_order(order=order)
            elif order.side == 'SELL' and self.cmp[symbol_name] >= order.price:
                self._trade_order(order=order)

    def _place_order(self, order: FakeOrder):
        self._placed_orders.append(order)

        symbol_name = order.symbol_name
        base_account, quote_account = self._get_accounts(symbol_name=symbol_name)

        if order.side == 'BUY':
            quote_account.free -= order.get_total()
            quote_account.locked += order.get_total()
        else:
            base_account.free -= order.quantity
            base_account.locked += order.quantity
        # call user socket callback
        self._call_user_socket_balance_update()

    def _trade_order(self, order: FakeOrder):
        if order in self._placed_orders:
            self._placed_orders.remove(order)

            symbol_name = order.symbol_name
            base_account, quote_account = self._get_accounts(symbol_name=symbol_name)
            bnb_account = self.account_manager.get_account(name='BNB')

            bnb_base_rate = self.get_bnb_base_rate(order=order)

            # update account balance
            if order.side == 'BUY':
                quote_account.locked -= order.get_total()
                base_account.free += order.quantity
            else:
                base_account.locked -= order.quantity
                quote_account.free += order.get_total()

            # set bnb commission
            base_commission = order.quantity * self._FEE  # K_FEE
            bnb_commission = base_commission / bnb_base_rate  # K_BNBBTC
            bnb_account.free -= bnb_commission

            # call binance user socket twice
            # call for order traded
            self._call_user_socket_order_traded(order=order)
            # call for balance update
            self._call_user_socket_balance_update()
        else:
            log.critical(f'trying to trade an order not placed {order.uid}')

    def _call_user_socket_order_traded(self, order: FakeOrder):
        bnb_base_rate = self.get_bnb_base_rate(order=order)

        base_commission = order.quantity * self._FEE  # K_FEE
        bnb_commission = base_commission / bnb_base_rate  # K_BNBBTC

        msg = dict(
            e='executionReport',
            s=order.symbol_name,
            x='TRADE',
            X='FILLED',
            c=order.uid,
            L=str(order.price),
            n=str(bnb_commission)  # n: bnb commission
        )
        self._user_socket_callback(msg)

    def get_bnb_base_rate(self, order: FakeOrder) -> float:
        bnb_base_rate: float
        # get symbol for commission name from config.ini
        symbol_for_commission_name = self.cm.get_symbol_for_commission_name(symbol_name=order.symbol_name)

        # if exist as a symbol, then use the existing cmp generator value, otherwise use the value in config.ini
        if symbol_for_commission_name in self.symbols.keys():
            bnb_base_rate = self.cmp[symbol_for_commission_name]
        else:
            bnb_base_rate = self.cm.get_symbol_for_commission_rate(symbol_name=order.symbol_name)
        return bnb_base_rate

    def _call_user_socket_balance_update(self):
        # call for balance update
        msg = dict(
            e='outboundAccountPosition',
            B=[dict(a=value.name, f=value.free, l=value.locked) for value in self.account_manager.accounts.values()]
            # B=[
        )
        self._user_socket_callback(msg)
