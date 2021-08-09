# sc_fake_client.py

import logging
import time
from typing import List, Callable
from enum import Enum
from random import choice
import threading

from sc_account_balance import AssetBalance, AccountBalance

# from config import SIMULATOR_MODE and parameters
import configparser

log = logging.getLogger('log')


class ThreadCmpGenerator:
    def __init__(self, interval: float, f_callback: Callable[[float], None]):
        self._running = True
        self.f_callback = f_callback
        self._interval = interval

    def terminate(self):
        print('cmp thread terminated')
        self._running = False

    def run(self):
        # generate a new cmp every _interval seconds and send it to update_cmp
        print('thread started')
        while self._running:
            # print(f'cmp thread running: {self._running}')
            time.sleep(self._interval)
            new_cmp = choice([-20, -10, -5, 0, 5, 10, 20])
            self.f_callback(new_cmp)


class FakeCmpMode(Enum):
    MODE_MANUAL = 0  # in this mode two buttons (+, -) control the market price
    MODE_GENERATOR = 1  # every K_UPDATE_RATE seconds generates a new cmp


class FakeOrder:
    def __init__(self, uid: str, side: str, price: float, quantity: float):
        self.uid = uid
        self.side = side
        self.price = price
        self.quantity = quantity

    def get_total(self) -> float:
        return self.price * self.quantity


class FakeClient:
    def __init__(self, user_socket_callback,
                 symbol_ticker_callback):
        self._user_socket_callback = user_socket_callback
        self._symbol_ticker_callback = symbol_ticker_callback
        self._placed_orders: List[FakeOrder] = []
        self._placed_orders_count = 0

        # FAKE CMP MODE SETTING
        config = configparser.ConfigParser()
        config.read('config.ini')
        sm = config['FAKE_CMP_MODE']['simulator_mode']

        self._fake_cmp_mode = FakeCmpMode[sm]
        initial_btc = float(config['SIMULATOR']['initial_btc'])
        initial_eur = float(config['SIMULATOR']['initial_eur'])
        initial_bnb = float(config['SIMULATOR']['initial_bnb'])
        update_rate = float(config['SIMULATOR']['update_rate'])

        # initial cmp
        self._cmp: float = float(config['SIMULATOR']['initial_cmp'])
        # cmp historical list
        self._cmp_sequence: List[float] = [self._cmp]

        self._FEE = float(config['SIMULATOR']['fee'])
        self._BNBBTC = float(config['SIMULATOR']['bnb_btc'])
        self._BNBEUR = float(config['SIMULATOR']['bnb_eur'])

        self.api_key = ''
        self.api_secret = ''

        self._account_balance = AccountBalance(
            d=dict(
                s1=AssetBalance(name='btc', free=initial_btc, locked=0.0),
                s2=AssetBalance(name='eur', free=initial_eur, locked=0.0, precision=2),
                bnb=AssetBalance(name='bnb', free=initial_bnb, locked=0.0)
            ))

        self.tcg = ThreadCmpGenerator(interval=update_rate, f_callback=self._update_cmp)

    def start_cmp_generator(self):
        if self._fake_cmp_mode == FakeCmpMode.MODE_GENERATOR:
            x = threading.Thread(target=self.tcg.run)
            x.start()

    def stop_cmp_generator(self):
        if self._fake_cmp_mode == FakeCmpMode.MODE_GENERATOR:
            self.tcg.terminate()

    def update_cmp_from_dashboard(self, step: float):
        if self._fake_cmp_mode == FakeCmpMode.MODE_MANUAL:
            self._update_cmp(step=step)
        else:
            log.warning('trying to manually update cmp in GENERATOR MODE')

    def _update_cmp(self, step: float):
        # when in MANUAL mode the cmp is update from the dashboard
        self._cmp += step
        self._process_cmp_change()

    def get_mode(self) -> FakeCmpMode:
        return self._fake_cmp_mode

    def order_market_buy(self, **kwargs) -> dict:
        order = FakeOrder(
            uid=kwargs.get('newClientOrderId'),
            side='BUY',
            price=self._cmp,
            quantity=kwargs.get('quantity')
        )
        status = 'NEW'

        # check enough balance
        if order.side == 'BUY' \
                and self._account_balance.get_free_price_s2() < order.get_total():
            log.critical(f'not enough balance to place the order')
            return {}
        elif order.side == 'SELL' \
                and self._account_balance.get_free_amount_s1() < order.quantity:
            log.critical(f'not enough amount to place the order')
            return {}

        # place
        self._placed_orders_count += 1
        self._place_order(order=order)
        self._trade_order(order=order)
        status = 'FILLED'

        return {
            "symbol": kwargs.get('symbol'),
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

    def order_market_sell(self, **kwargs) -> dict:
        order = FakeOrder(
            uid=kwargs.get('newClientOrderId'),
            side='SELL',
            price=self._cmp,
            quantity=kwargs.get('quantity')
        )
        status = 'NEW'

        # check enough balance
        if order.side == 'BUY' \
                and self._account_balance.get_free_price_s2() < order.get_total():
            log.critical(f'not enough balance to place the order')
            return {}
        elif order.side == 'SELL' \
                and self._account_balance.get_free_amount_s1() < order.quantity:
            log.critical(f'not enough amount to place the order')
            return {}

        # place
        self._placed_orders_count += 1
        self._place_order(order=order)
        self._trade_order(order=order)
        status = 'FILLED'

        return {
            "symbol": kwargs.get('symbol'),
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
        order = FakeOrder(
            uid=kwargs.get('newClientOrderId'),
            side=kwargs.get('side'),
            price=float(kwargs.get('price')),
            quantity=kwargs.get('quantity')
        )
        status = 'NEW'

        # check whether it has already been placed
        for placed_order in self._placed_orders:
            if placed_order.uid == order.uid:
                log.critical(f'order with uid {placed_order.uid} has already been placed')
                return {}

        # check enough balance
        if order.side == 'BUY' \
                and self._account_balance.get_free_price_s2() < order.get_total():
            log.critical(f'not enough balance to place the order')
            return {}
        elif order.side == 'SELL' \
                and self._account_balance.get_free_amount_s1() < order.quantity:
            log.critical(f'not enough amount to place the order')
            return {}

        # place
        self._placed_orders_count += 1
        self._place_order(order=order)

        # check if the order has to be placed immediately:
        if order.side == 'BUY' and self._cmp < order.price:
            log.info(f'the order has been traded when placing it')
            self._trade_order(order=order)
            status = 'FILLED'
        elif order.side == 'SELL' and self._cmp > order.price:
            log.info(f'the order has been traded when placing it')
            self._trade_order(order=order)
            status = 'FILLED'

        return {
                "symbol": kwargs.get('symbol'),
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
                # update balance
                if order.side == 'BUY':
                    self._account_balance.s2.free += order.get_total()
                    self._account_balance.s2.locked -= order.get_total()
                else:
                    self._account_balance.s1.free += order.quantity
                    self._account_balance.s1.locked -= order.quantity
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

    def get_symbol_info(self, symbol: str) -> dict:
        if symbol == 'BTCEUR':
            return {
                "symbol": symbol,
                "status": "TRADING",
                "baseAsset": "BTC",
                "baseAssetPrecision": 8,
                "quoteAsset": "EUR",
                "quoteAssetPrecision": 8,
                "orderTypes": ["LIMIT", "MARKET"],
                "icebergAllowed": True,
                'filters':
                    [
                        {'filterType': 'PRICE_FILTER', 'minPrice': '0.01000000', 'maxPrice': '1000000.00000000',
                         'tickSize': '0.01000000'},
                        {'filterType': 'PERCENT_PRICE', 'multiplierUp': '5', 'multiplierDown': '0.2', 'avgPriceMins': 5},
                        {'filterType': 'LOT_SIZE', 'minQty': '0.00000100', 'maxQty': '9000.00000000',
                         'stepSize': '0.00000100'},
                        {'filterType': 'MIN_NOTIONAL', 'minNotional': '10.00000000', 'applyToMarket': True,
                         'avgPriceMins': 5}, {'filterType': 'ICEBERG_PARTS', 'limit': 10},
                        {'filterType': 'MARKET_LOT_SIZE', 'minQty': '0.00000000', 'maxQty': '53.77006166',
                         'stepSize': '0.00000000'}, {'filterType': 'MAX_NUM_ORDERS', 'maxNumOrders': 200},
                        {'filterType': 'MAX_NUM_ALGO_ORDERS', 'maxNumAlgoOrders': 5}
                    ],
                'permissions': ['SPOT', 'MARGIN']
            }
        else:
            log.critical(f'wrong symbol {symbol}')
            return {}

    def get_asset_balance(self, asset: str) -> dict:
        if asset == 'BTC':
            free = self._account_balance.s1.free
            locked = self._account_balance.s1.locked
        elif asset == 'EUR':
            free = self._account_balance.s2.free
            locked = self._account_balance.s2.locked
        elif asset == 'BNB':
            free = self._account_balance.bnb.free
            locked = self._account_balance.bnb.locked
        else:
            log.critical(f'wrong asset')
            return {}
        return {
                "asset": asset,
                "free": str(free),
                "locked": str(locked)
            }

    def get_avg_price(self, symbol: str) -> dict:
        if symbol == 'BTCEUR':
            price = str(self._cmp)
        elif symbol == 'BNBBTC':
            price = str(self._BNBBTC)
        elif symbol == 'BNBEUR':
            price = str(self._BNBEUR)
        else:
            price = str(0.0)
            log.critical(f'symbol not in simulator, returning {price}')
        return {
                "mins": 5,
                "price": price
            }

    def _process_cmp_change(self):
        self._check_placed_orders_for_trading()
        msg = dict(
            e='24hrTicker',
            c=str(self._cmp)
        )
        self._symbol_ticker_callback(msg)

    def _check_placed_orders_for_trading(self):
        for order in self._placed_orders:
            if order.side == 'BUY' and self._cmp <= order.price:
                self._trade_order(order=order)
            elif order.side == 'SELL' and self._cmp >= order.price:
                self._trade_order(order=order)

    def _place_order(self, order: FakeOrder):
        self._placed_orders.append(order)
        if order.side == 'BUY':
            self._account_balance.s2.free -= order.get_total()
            self._account_balance.s2.locked += order.get_total()
        else:
            self._account_balance.s1.free -= order.quantity
            self._account_balance.s1.locked += order.quantity
        # call user socket callback
        self._call_user_socket_balance_update()

    # def _place_market_order(self, order: FakeOrder):
    #     self._placed_orders.append(order)
    #     if order.side == 'BUY':
    #         self._account_balance.s2.free -= order.get_total()
    #         self._account_balance.s2.locked += order.get_total()
    #     else:
    #         self._account_balance.s1.free -= order.quantity
    #         self._account_balance.s1.locked += order.quantity
    #     # call user socket callback
    #     self._call_user_socket_balance_update()
    #
    #     # trade immediately
    #     self._trade_order(order=order)

    def _trade_order(self, order: FakeOrder):
        if order in self._placed_orders:
            self._placed_orders.remove(order)
            # update account balance
            if order.side == 'BUY':
                self._account_balance.s2.locked -= order.get_total()
                self._account_balance.s1.free += order.quantity
            else:
                self._account_balance.s1.locked -= order.quantity
                self._account_balance.s2.free += order.get_total()
            # eur_commission = order.get_total() * K_FEE
            btc_commission = order.quantity * self._FEE  # K_FEE
            bnb_commission = btc_commission / self._BNBBTC  # K_BNBBTC
            self._account_balance.bnb.free -= bnb_commission
            # print(f'fee: {order.get_total() * K_FEE}')
            # call binance user socket twice
            # call for order traded
            self._call_user_socket_order_traded(order=order)
            # call for balance update
            self._call_user_socket_balance_update()
        else:
            log.critical(f'trying to trade an order not placed {order.uid}')

    def _call_user_socket_order_traded(self, order: FakeOrder):
        btc_commission = order.quantity * self._FEE  # K_FEE
        bnb_commission = btc_commission / self._BNBBTC  # K_BNBBTC
        msg = dict(
            e='executionReport',
            x='TRADE',
            X='FILLED',
            c=order.uid,
            L=str(order.price),
            n=str(bnb_commission)  # n: bnb commission
        )
        self._user_socket_callback(msg)

    def _call_user_socket_balance_update(self):
        # call for balance update
        msg = dict(
            e='outboundAccountPosition',
            B=[
                dict(
                    a='BTC',
                    f=self._account_balance.s1.free,
                    l=self._account_balance.s1.locked
                ),
                dict(
                    a='EUR',
                    f=self._account_balance.s2.free,
                    l=self._account_balance.s2.locked
                ),
                dict(
                    a='BNB',
                    f=self._account_balance.bnb.free,
                    l=self._account_balance.bnb.locked
                )
            ]
        )
        self._user_socket_callback(msg)
