# pp_order.py

import logging
import secrets
from enum import Enum
from binance import enums as k_binance
from typing import Union, Optional
import configparser

log = logging.getLogger('log')

K_ACTIVATION_DISTANCE = 25.0


# todo: review available status
class OrderStatus(Enum):
    # in use
    MONITOR = 1
    ACTIVE = 8
    TO_BE_TRADED = 9  # status when it is sent for trading (market)
    TRADED = 3  # status when trading has been confirmed
    CANCELED = 4


class Order:
    def __init__(self,
                 order_id: str,  # not actually used
                 k_side: k_binance,
                 price: float,
                 amount: float,
                 status: OrderStatus = OrderStatus.MONITOR,
                 bnb_commission=0.0,
                 binance_id=0,  # int
                 name=''
                 ):

        # read config.ini
        config = configparser.ConfigParser()
        config.read('config.ini')
        self.over_activation_shift = float(config['SESSION']['over_activation_shift'])
        self.distance_to_target_price = float(config['SESSION']['distance_to_target_price'])
        self.fee = float(config['PT_CREATION']['fee'])

        self.order_id = order_id
        self.name = name
        self.k_side = k_side
        self.price = price
        self.amount = amount
        self.status = status
        self.bnb_commission = bnb_commission
        self.binance_id = binance_id

        self.uid = secrets.token_hex(8)  # set random uid of 16 characters

        # set theoretical eur commission, it will be updated when the order is traded
        self.eur_commission = self.price * self.amount * self.fee

        # both are set during pt creation, when both orders and pt are known
        self.sibling_order: Optional[Order] = None
        self.pt = None  # it should be Optional[None], but there is a crossed reference problem with PerfectTrade

        # set target price
        sign = 1 if self.k_side == k_binance.SIDE_SELL else -1
        self.target_price = self.price + (sign * self.distance_to_target_price)

    def to_dict_for_df(self):
        # get a dictionary from the object able to use in dash (through a df)
        d = {}
        for k, v in self.__dict__.items():
            if k not in ['sibling_order', 'pt']:  # variables that are references to other objects
                d[k] = v
        d['pt_id'] = self.pt.pt_id
        d['status'] = self.status.name.lower()
        d['total'] = abs(self.get_signed_total_at_cmp(cmp=self.price, with_commission=False))
        return d

    @staticmethod
    def get_new_uid() -> str:
        return secrets.token_hex(8)

    def is_ready_for_activation(self, cmp: float) -> bool:
        if self.k_side == k_binance.SIDE_BUY and cmp < self.price - self.over_activation_shift:
            return True
        elif self.k_side == k_binance.SIDE_SELL and cmp > self.price + self.over_activation_shift:
            return True
        return False

    def is_ready_for_trading(self, cmp: float) -> bool:
        if self.k_side == k_binance.SIDE_BUY:
            if cmp > self.price:
                return True
            # if target_price < cmp < price does nothing
            elif cmp < self.target_price:
                self.price = self.target_price
                self.target_price -= self.distance_to_target_price
        elif self.k_side == k_binance.SIDE_SELL:
            if cmp < self.price:
                return True
            # if price < cmp < target_price does nothing
            elif cmp > self.target_price:
                self.price = self.target_price
                self.target_price += self.distance_to_target_price

        return False

    def get_distance(self, cmp: float) -> float:
        if self.k_side == k_binance.SIDE_BUY:
            return cmp - self.price
        else:
            return self.price - cmp

    def get_price_str(self, precision: int = 2) -> str:
        return f'{self.price:0.0{precision}f}'

    def get_amount(self, precision: int = 6) -> float:
        return round(self.amount, precision)  # 6 for BTC

    def get_signed_amount(self) -> float:
        if self.k_side == k_binance.SIDE_BUY:
            return self.amount
        else:
            return - self.amount

    # ********** total methods **********

    def _get_total_at_cmp(self, cmp: float) -> float:
        # total
        return cmp * self.amount

    def _get_signed_total_at_cmp(self, cmp: float) -> float:
        # signed total
        if self.k_side == k_binance.SIDE_BUY:
            return - self._get_total_at_cmp(cmp=cmp)
        elif self.k_side == k_binance.SIDE_SELL:
            return + self._get_total_at_cmp(cmp=cmp)
        else:
            raise Exception(f'wrong k_side: {self.k_side}')

    def get_signed_total_at_cmp(self, cmp: float, with_commission: bool, precision=2):
        # set commission depending on net total or gross total request
        commission = self.get_eur_commission(cmp=cmp) if with_commission else 0.0
        return round(self._get_signed_total_at_cmp(cmp=cmp) - commission, precision)

    # ********** end of total methods **********

    def get_eur_commission(self, cmp: float) -> float:
        if self.status == OrderStatus.TRADED:
            return self.eur_commission
        else:
            return cmp * self.amount * self.fee

    def get_momentum(self, cmp: float):
        return abs(self.amount * (cmp - self.price))

    def set_bnb_commission(self, commission: float, bnbeur_rate: float) -> None:
        self.bnb_commission = commission
        self.eur_commission = commission * bnbeur_rate

    def set_status(self, status: OrderStatus):
        old_status = self.status
        self.status = status
        log.info(f'** ORDER STATUS CHANGED FROM {old_status.name} TO {status.name} - {self}')

    def set_binance_id(self, new_id: int):
        self.binance_id = new_id

    def __repr__(self):
        return (
                f'{self.k_side:4} - {self.pt.pt_id:5} - '
                f'{self.name:5} - {self.order_id:5} - {self.price:10,.2f} '
                f'- {self.amount:12,.6f} - {self.bnb_commission:12,.6f} - {self.status.name:10}'
                f'- {self.binance_id} - {self.uid}'
        )

    @staticmethod
    def is_filter_passed(filters: dict, qty: float, price: float) -> bool:
        if not filters.get('min_qty') <= qty <= filters.get('max_qty'):
            log.critical(f'qty out of min/max limits: {qty}')
            log.critical(f"min: {filters.get('min_qty')} - max: {filters.get('max_qty')}")
            return False
        elif not filters.get('min_price') <= price <= filters.get('max_price'):
            log.critical(f'buy price out of min/max limits: {price}')
            log.critical(f"min: {filters.get('min_price')} - max: {filters.get('max_price')}")
            return False
        elif not (qty * price) > filters.get('min_notional'):
            log.critical(f'buy total (price * qty) under minimum: {qty * price}')
            log.critical(f'min notional: {filters.get("min_notional")}')
            return False
        return True
