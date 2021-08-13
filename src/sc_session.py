# sc_session.py

import logging
import time
from datetime import datetime
from enum import Enum

from typing import Optional
from binance import enums as k_binance

from sc_market import Market
from sc_order import Order, OrderStatus
from sc_account_balance import AccountBalance
from sc_balance_manager import BalanceManager
from sc_pt_manager import PTManager
from sc_perfect_trade import PerfectTradeStatus
from sc_pt_calculator import get_compensation

import configparser


log = logging.getLogger('log')


class QuitMode(Enum):
    CANCEL_ALL = 1
    PLACE_ALL_PENDING = 2
    TRADE_ALL_PENDING = 3


class Session:
    def __init__(self):
        print('session')
        self.market = Market(
            symbol_ticker_callback=self.symbol_ticker_callback,
            order_traded_callback=self.order_traded_callback,
            account_balance_callback=self.account_balance_callback
        )

        # read parameters from config.ini
        config = configparser.ConfigParser()
        config.read('config.ini')

        self.symbol = config['BINANCE']['symbol']
        self.target_total_net_profit = float(config['SESSION']['target_total_net_profit'])
        self.cycles_count_for_inactivity = int(config['SESSION']['cycles_count_for_inactivity'])
        self.new_pt_shift = float(config['SESSION']['new_pt_shift'])
        self.isolated_distance = float(config['SESSION']['isolated_distance'])
        self.compensation_distance = float(config['SESSION']['compensation_distance'])
        self.compensation_gap = float(config['SESSION']['compensation_gap'])
        self.fee = float(config['PT_CREATION']['fee'])
        self.quantity = float(config['PT_CREATION']['quantity'])
        self.net_eur_balance = float(config['PT_CREATION']['net_eur_balance'])

        # get filters that will be checked before placing an order
        self.symbol_filters = self.market.get_symbol_info(symbol=self.symbol)

        # ********** managers **********
        self.bm = BalanceManager(market=self.market)

        self.session_id = f'S_{datetime.now().strftime("%Y%m%d_%H%M")}'

        self.ptm = PTManager(
            symbol_filters=self.symbol_filters,
            session_id=self.session_id)

        # used in dashboard in the cmp line chart. initiated with current cmp
        self.cmps = [self.market.get_cmp(self.symbol)]
        self.orders_book_depth = []
        self.orders_book_span = []

        self.total_profit_series = [0.0]

        self.pt_created_count = 0
        self.buy_count = 0
        self.sell_count = 0
        self.cmp_count = 0
        self.cycles_from_last_trade = 0

        # todo: start manually from button
        # self.market.start_sockets()

    # ********** dashboard callback functions **********
    def get_last_cmp(self) -> float:
        if self.cmps:
            return self.cmps[-1]
        else:
            return 0

    def get_session_hours(self) -> float:
        return round(self.cmp_count / 3600, 2)

    def get_traded_orders_profit(self) -> str:
        # get profit only if buy_orders_count == sell_orders_count
        if self.buy_count == self.sell_count:
            return f'{self.ptm.get_traded_orders_profit():,.2f}'
        else:
            return 'N/A'

    # ********** Binance socket callback functions **********
    def symbol_ticker_callback(self, cmp: float) -> None:
        try:
            # 0.1: create first pt
            if self.cmp_count == 1:
                if self.allow_new_pt_creation(cmp=cmp):
                    self.ptm.create_new_pt(cmp=cmp)
                else:
                    log.critical("initial pt not allowed")
                    raise Exception("initial pt not allowed")

            # 0.2: update cmp count to control timely pt creation
            self.cmp_count += 1

            # these two lists will be used to plot
            self.cmps.append(cmp)
            # self.cycles_series.append(self.cmp_count)

            # self.last_cmp = cmp

            # counter used to detect inactivity
            self.cycles_from_last_trade += 1

            # loop through monitoring orders for compensation
            # self.check_monitor_orders_for_compensation(cmp=cmp)

            # it is important to check first the active list and then the monitor one
            # with this order we guarantee there is only one status change per cycle
            self.check_active_list_for_trading(cmp=cmp)

            # 4. loop through monitoring orders for activating
            self.check_monitor_list_for_activating(cmp=cmp)

            # 5. check inactivity & liquidity
            self.check_inactivity(cmp=cmp)

            # 8. check global net profit
            # return the total profit considering that all remaining orders are traded at current cmp
            total_profit = self.ptm.get_total_actual_profit(cmp=cmp)
            self.total_profit_series.append(total_profit)
            if total_profit > self.target_total_net_profit:
                self.quit_particular_session()
                # todo: start new session when target achieved
                raise Exception("Target achieved!!!")
            elif self.get_session_hours() > 24.0 and total_profit > -5.0:
                self.quit_particular_session()
                raise Exception("terminated to minimize loss")

        except AttributeError as e:
            print(e)

    def check_monitor_list_for_activating(self, cmp: float) -> None:
        for pt in self.ptm.perfect_trades:
            if pt.status != PerfectTradeStatus.COMPLETED:
                for order in pt.orders:
                    if order.status == OrderStatus.MONITOR and order.is_ready_for_activation(cmp=cmp):
                        order.set_status(OrderStatus.ACTIVE)

    def check_active_list_for_trading(self, cmp: float) -> None:
        for pt in self.ptm.perfect_trades:
            if pt.status != PerfectTradeStatus.COMPLETED:
                for order in pt.orders:
                    if order.status == OrderStatus.ACTIVE and order.is_ready_for_trading(cmp=cmp):
                        # MARKET trade
                        self._place_market_order(order=order)

    def check_inactivity(self, cmp):
        # a new pt is created if no order has been traded for a while
        # check elapsed time since last trade
        if self.cycles_from_last_trade > self.cycles_count_for_inactivity:
            # check liquidity
            if self.allow_new_pt_creation(cmp=cmp):
                self.ptm.create_new_pt(cmp=cmp, pt_type='FROM_INACTIVITY')
                self.cycles_from_last_trade = 0  # equivalent to trading but without a trade

    # ********** compensation (not used) **********
    def check_monitor_orders_for_compensation(self, cmp: float) -> None:
        # get monitor orders of pt with one order traded
        orders = self.ptm.get_orders_by_request(
            orders_status=[OrderStatus.MONITOR],
            pt_status=[PerfectTradeStatus.BUY_TRADED, PerfectTradeStatus.SELL_TRADED]
        )
        for order in orders:
            if order.order_id != 'CONCENTRATED' and order.get_abs_distance(cmp=cmp) > self.compensation_distance:
                # compensate
                b1, s1 = self.compensate_order(order=order, ref_mp=cmp, ref_gap=self.compensation_gap)
                # set values
                b1.sibling_order = None
                b1.pt = order.pt
                s1.sibling_order = None
                s1.pt = order.pt
                # add to pt orders list
                order.pt.orders.append(b1)
                order.pt.orders.append(s1)
                # change original order status
                order.status = OrderStatus.CANCELED
                # change pt type to avoid generating a new pt after trading the new orders
                order.pt.pt_type = 'FROM_COMPENSATION'

    def compensate_order(self, order: Order, ref_mp: float, ref_gap: float) -> (Order, Order):
        amount, total, _ = BalanceManager.get_balance_for_list([order])
        # get equivalent pair b1-s1
        s1_p, b1_p, s1_qty, b1_qty = get_compensation(
            cmp=ref_mp,
            gap=ref_gap,
            qty_bal=order.get_signed_amount(),
            price_bal=order.get_signed_total(),  # todo: assess whether it has to be signed or not
            buy_fee=self.fee,
            sell_fee=self.fee
        )
        # validate values received for b1 and s1
        if s1_p < 0 or b1_p < 0 or s1_qty < 0 or b1_qty < 0:
            raise Exception(f'negative value(s) after compensation: b1p: {b1_p} b1q: {b1_qty} 1p: {s1_p} s1q: {s1_qty}')
        else:
            # create both orders
            b1 = Order(
                order_id='CONCENTRATED',
                k_side=k_binance.SIDE_BUY,
                price=b1_p,
                amount=b1_qty,
                uid=Order.get_new_uid(),
                name='con-b1'
            )
            s1 = Order(
                order_id='CONCENTRATED',
                k_side=k_binance.SIDE_SELL,
                price=s1_p,
                amount=s1_qty,
                status=OrderStatus.MONITOR,
                uid=Order.get_new_uid(),
                name='con-s1'
            )
            return b1, s1

    def order_traded_callback(self, uid: str, order_price: float, bnb_commission: float) -> None:
        # print(f'********** ORDER TRADED:    price: {order_price} [EUR] - commission: {bnb_commission} [BNB]')
        log.info(f'order traded with uid: {uid}')
        # get the order by uid
        for pt in self.ptm.perfect_trades:
            if pt.status != PerfectTradeStatus.COMPLETED:
                for order in pt.orders:
                    if order.uid == uid:
                        # print(f'********** order traded: {order}')
                        log.info(f'confirmation of order traded {order}')

                        # set the cycle in which the order has been traded
                        order.traded_cycle = self.cmp_count

                        # reset counter
                        self.cycles_from_last_trade = 0

                        # update buy & sell count
                        if order.k_side == k_binance.SIDE_BUY:
                            self.buy_count += 1
                        else:
                            self.sell_count += 1

                        # set commission and price
                        order.set_bnb_commission(
                            commission=bnb_commission,
                            bnbeur_rate=self.market.get_cmp(symbol='BNBEUR'))

                        # set traded order price
                        order.price = order_price

                        # change status
                        order.set_status(status=OrderStatus.TRADED)

                        # update perfect trades list
                        self.ptm.order_traded(order=order)

                        # check condition for new pt:
                        # Once activated, if it is the last order to trade in the pt, then create a new pt
                        # only if it was created as NORMAL
                        # it is enough checking the sibling order because a compensated/split pt will have another type
                        if pt.pt_type == 'NORMAL' and order.sibling_order.status == OrderStatus.TRADED:
                            # check liquidity:
                            if self.allow_new_pt_creation(cmp=self.cmps[-1]):
                                # calculate shift depending on last traded order side

                                # todo: assess whether the following criteria is good or not
                                shift: float
                                if order.k_side == k_binance.SIDE_BUY:
                                    shift = self.new_pt_shift
                                else:
                                    shift = self.new_pt_shift * (-1)

                                # create pt with shift
                                self.ptm.create_new_pt(cmp=order_price + shift)
                                self.cycles_from_last_trade = 0  # equivalent to trading but without a trade

                        # since the traded orders has been identified, do not check more orders
                        break

    def allow_new_pt_creation(self, cmp: float) -> bool:
        # get total eur & btc needed to trade all alive orders at their own price
        eur_needed, btc_needed = self.ptm.get_total_eur_btc_needed()

        # check available liquidity (eur & btc) vs needed when trading both orders
        if self.market.get_asset_liquidity(asset='EUR') < eur_needed + (self.quantity * cmp):
            return False
        elif self.market.get_asset_liquidity(asset='BTC') < btc_needed + self.quantity:
            return False
        else:
            return True

    def account_balance_callback(self, ab: AccountBalance) -> None:
        # update of current balance from Binance
        self.bm.update_current(last_ab=ab)

    # ********** check methods **********
    def _place_market_order(self, order) -> None:  # (bool, Optional[str]):
        # raise an exception if the order is not placed in binance (probably due to not enough liquidity)
        # change order status (it will be update to TRADED once received through binance socket)
        order.set_status(OrderStatus.TO_BE_TRADED)
        # place order and check message received
        msg = self.market.place_market_order(order=order)
        if msg:
            order.set_binance_id(new_id=msg.get('binance_id'))
            log.info(f'********** MARKET ORDER PLACED **********      msg: {msg}')
        else:
            log.critical(f'market order not place in binance {order}')
            raise Exception("MARKET order not placed")

    def _place_limit_order(self, order: Order) -> None:  # (bool, Optional[str]):
        order.set_status(status=OrderStatus.TO_BE_TRADED)
        # place order
        msg = self.market.place_limit_order(order=order)
        if msg:
            order.set_binance_id(new_id=msg.get('binance_id'))
            log.debug(f'********** LIMIT ORDER PLACED **********      msg: {msg}')
        else:
            log.critical(f'error placing order {order}')
            raise Exception("LIMIT order not placed")

    def quit_particular_session(self, quit_mode: QuitMode):
        # trade all remaining orders
        log.info('session terminated')
        orders = self.ptm.get_orders_by_request(
            orders_status=[OrderStatus.MONITOR, OrderStatus.ACTIVE],
            pt_status=[PerfectTradeStatus.BUY_TRADED, PerfectTradeStatus.SELL_TRADED]
        )
        for order in orders:
            if quit_mode == QuitMode.PLACE_ALL_PENDING:
                self._place_limit_order(order=order)
                log.info(f'placing limit order {order.k_side} {order.status} {order.price}')
                time.sleep(0.1)
            elif quit_mode == QuitMode.TRADE_ALL_PENDING:
                self._place_market_order(order=order)
                log.info(f'trading market order {order.k_side} {order.status} {order.price}')
                time.sleep(0.1)
            elif quit_mode == QuitMode.CANCEL_ALL:
                pass

        # log final info
        self.ptm.log_perfect_trades_info()

        # todo: mark stop and delay for 3"
        self.market.stop()
