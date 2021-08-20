# sc_session.py

import logging
import time
from datetime import datetime
from enum import Enum

from typing import Optional, Callable
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
    def __init__(self,
                 session_id: str,
                 session_stopped_callback: Callable[[str, float, int, int], None],
                 market: Market,
                 balance_manager: BalanceManager
                 ):

        self.session_id = session_id
        self.session_stopped_callback = session_stopped_callback
        self.market = market
        self.bm = balance_manager

        print('session')

        self.session_active = True

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
        self.max_negative_profit_allowed = float(config['SESSION']['max_negative_profit_allowed'])

        # get filters that will be checked before placing an order
        self.symbol_filters = self.market.get_symbol_info(symbol=self.symbol)

        self.ptm = PTManager(
            symbol_filters=self.symbol_filters,
            session_id=self.session_id)

        # used in dashboard in the cmp line chart. initiated with current cmp
        self.cmps = [self.market.get_cmp(self.symbol)]
        # self.orders_book_depth = []
        # self.orders_book_span = []

        self.total_profit_series = [0.0]

        self.pt_created_count = 0
        self.buy_count = 0
        self.sell_count = 0
        self.cmp_count = 0
        self.cycles_from_last_trade = 0

        self.modal_alert_messages = []

    # ********** dashboard callback functions **********
    def get_info(self):
        # return a dictionary with data convenient for the dashboard
        session_data = dict(
            session_id=self.session_id,
            last_cmp=self.cmps[-1] if self.cmps else 0,
            elapsed_hours=round(self.cmp_count / 3600, 2),
            pt_created_count=self.pt_created_count,
            buy_count= self.buy_count,
            sell_count=self.sell_count,
            cmp_count=self.cmp_count,
            cycles_from_last_trade=self.cycles_from_last_trade,
            momentum=self._get_momentum()
        )
        return session_data

    def _get_momentum(self) -> (float, float, float):
        # get orders
        buy_momentum_orders = self.ptm.get_orders_by_request(
            orders_status=[OrderStatus.MONITOR, OrderStatus.ACTIVE],
            pt_status=[PerfectTradeStatus.SELL_TRADED]
        )
        sell_momentum_orders = self.ptm.get_orders_by_request(
            orders_status=[OrderStatus.MONITOR, OrderStatus.ACTIVE],
            pt_status=[PerfectTradeStatus.BUY_TRADED]
        )
        # calculate momentum
        buy_momentum = sum([order.get_momentum(cmp=self.cmps[-1]) for order in buy_momentum_orders])
        sell_momentum = sum([order.get_momentum(cmp=self.cmps[-1]) for order in sell_momentum_orders])
        return sell_momentum - buy_momentum, buy_momentum, sell_momentum

    def get_traded_orders_profit(self) -> str:
        # get profit only if buy_orders_count == sell_orders_count
        if self.buy_count == self.sell_count:
            return f'{self.ptm.get_traded_orders_profit():,.2f}'
        else:
            return 'N/A'

    # ********** Binance socket callback functions **********
    def symbol_ticker_callback(self, cmp: float) -> None:
        if self.session_active:
            try:
                # 0.1: create first pt
                if self.cmp_count == 1:
                    if self.allow_new_pt_creation(cmp=cmp):
                        self.ptm.create_new_pt(cmp=cmp)
                    else:
                        log.critical("initial pt not allowed, it will be tried again after inactivity period")
                        # raise Exception("initial pt not allowed")

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
                self._check_active_orders_for_trading(cmp=cmp)

                # 4. loop through monitoring orders for activating
                self._check_monitor_orders_for_activating(cmp=cmp)

                # 5. check inactivity & liquidity
                self._check_inactivity(cmp=cmp)

                # 6. check dynamic parameters
                self._check_dynamic_parameters()

                # ********** SESSION EXIT POINT ********
                self._check_exit_conditions(cmp)

            except AttributeError as e:
                print(e)

    def _check_dynamic_parameters(self):
        # neb (increase)
        neb_target_rate = int(self.target_total_net_profit / self.net_eur_balance)
        print(neb_target_rate, self.ptm.pt_created_count)
        if self.ptm.pt_created_count > neb_target_rate + 1:  # todo: move to parameter
            self.target_total_net_profit += self.net_eur_balance

    def _check_exit_conditions(self, cmp):
        # 8. check global net profit
        # return the total profit considering that all remaining orders are traded at current cmp
        total_profit = self.ptm.get_total_actual_profit(cmp=cmp)
        self.total_profit_series.append(total_profit)
        if total_profit > self.target_total_net_profit:
            self.session_active = False
            self.quit_particular_session(quit_mode=QuitMode.TRADE_ALL_PENDING)
            # todo: start new session when target achieved
            # raise Exception("Target achieved!!!")
        elif total_profit < self.max_negative_profit_allowed:  # todo: move to parameter at config.ini
            self.session_active = False
            self.quit_particular_session(quit_mode=QuitMode.PLACE_ALL_PENDING)
            # raise Exception("terminated to minimize loss")
        # elif self.get_session_hours() > 2.0 and total_profit > -5.0:
        #     self.quit_particular_session()
        #     raise Exception("terminated to minimize loss")

    def _check_monitor_orders_for_activating(self, cmp: float) -> None:
        # get orders
        monitor_orders = self.ptm.get_orders_by_request(
            orders_status=[OrderStatus.MONITOR],
            pt_status=[PerfectTradeStatus.NEW, PerfectTradeStatus.BUY_TRADED, PerfectTradeStatus.SELL_TRADED]
        )
        # change status MONITOR -> ACTIVE
        [order.set_status(OrderStatus.ACTIVE) for order in monitor_orders if order.is_ready_for_activation(cmp=cmp)]

    def _check_active_orders_for_trading(self, cmp: float) -> None:
        # get orders
        active_orders = self.ptm.get_orders_by_request(
            orders_status=[OrderStatus.ACTIVE],
            pt_status=[PerfectTradeStatus.NEW, PerfectTradeStatus.BUY_TRADED, PerfectTradeStatus.SELL_TRADED]
        )
        # trade at market price active orders ready for trading
        [self._place_market_order(order=order) for order in active_orders if order.is_ready_for_trading(cmp=cmp)]

    def _check_inactivity(self, cmp):
        # a new pt is created if no order has been traded for a while
        # check elapsed time since last trade
        if self.cycles_from_last_trade > self.cycles_count_for_inactivity:
            # check liquidity
            if self.allow_new_pt_creation(cmp=cmp):
                self.ptm.create_new_pt(cmp=cmp, pt_type='FROM_INACTIVITY')
                self.cycles_from_last_trade = 0  # equivalent to trading but without a trade
            else:
                log.info('new perfect trade creation is not allowed. it will be tried again after 60"')
                # update inactivity counter to try again after 60 cycles if inactivity continues
                self.cycles_from_last_trade -= 60  # todo: move to parameter

    # ********** compensation (not used) **********
    def _check_monitor_orders_for_compensation(self, cmp: float) -> None:
        # get monitor orders of pt with one order traded
        orders = self.ptm.get_orders_by_request(
            orders_status=[OrderStatus.MONITOR],
            pt_status=[PerfectTradeStatus.BUY_TRADED, PerfectTradeStatus.SELL_TRADED]
        )
        for order in orders:
            if order.order_id != 'CONCENTRATED' and order.get_abs_distance(cmp=cmp) > self.compensation_distance:
                # compensate
                b1, s1 = self._compensate_order(order=order, ref_mp=cmp, ref_gap=self.compensation_gap)
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

    def _compensate_order(self, order: Order, ref_mp: float, ref_gap: float) -> (Order, Order):
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
        print(f'********** ORDER TRADED:    price: {order_price} [EUR] - commission: {bnb_commission} [BNB]')
        log.info(f'order traded with uid: {uid}')
        # get orders
        orders_to_be_traded = self.ptm.get_orders_by_request(
            orders_status=[OrderStatus.TO_BE_TRADED],
            pt_status=[PerfectTradeStatus.NEW, PerfectTradeStatus.BUY_TRADED, PerfectTradeStatus.SELL_TRADED]
        )
        # for pt in self.ptm.perfect_trades:
        #     if pt.status != PerfectTradeStatus.COMPLETED:
        #         for order in pt.orders:
        for order in orders_to_be_traded:
            # check uid
            if order.uid == uid:
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

                # update perfect trades list & pt status
                self.ptm.order_traded(order=order)

                # # prepare modal alert in the dashboard
                # self.modal_alert_messages.append(f'{order.pt_id} {order.k_side}')

                # check condition for new pt:
                # Once activated, if it is the last order to trade in the pt, then create a new pt
                # only if it was created as NORMAL
                # it is enough checking the sibling order because a compensated/split pt will have another type
                if order.pt.pt_type == 'NORMAL' and order.sibling_order.status == OrderStatus.TRADED:
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
                    else:
                        # nothing to do, it will be assessed again after another order is traded an PT completed
                        pass

                # since the traded orders has been identified, do not check more orders
                break

    def allow_new_pt_creation(self, cmp: float) -> bool:
        # get total eur & btc needed to trade all alive orders at their own price
        eur_needed, btc_needed = self.ptm.get_total_eur_btc_needed()

        # 1. liquidity
        # 2. monitor + active count
        # 3. span / depth
        # 2. momentum

        # dynamic parameters:
        #   - inactivity time
        #   - neb/amount

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
        log.info(f'********** STOP {quit_mode.name} **********')
        log.info('session terminated')

        # ACTIVE orders (trade all at market price no matter the quit mode)
        active_orders = self.ptm.get_orders_by_request(
            orders_status=[OrderStatus.ACTIVE],
            pt_status=[PerfectTradeStatus.BUY_TRADED, PerfectTradeStatus.SELL_TRADED]
        )
        log.info('ACTIVE orders:')
        for order in active_orders:
            if quit_mode in [QuitMode.PLACE_ALL_PENDING, QuitMode.TRADE_ALL_PENDING]:
                self._place_market_order(order=order)
                log.info(f'trading market order {order.k_side} {order.status} {order.price}')
                time.sleep(0.1)
            elif quit_mode == QuitMode.CANCEL_ALL:
                pass

        # MONITOR orders (depending on the quit mode will be traded at market price or placed at order price)
        monitor_orders = self.ptm.get_orders_by_request(
            orders_status=[OrderStatus.MONITOR],
            pt_status=[PerfectTradeStatus.BUY_TRADED, PerfectTradeStatus.SELL_TRADED]
        )
        log.info('MONITOR orders:')
        diff = 0
        if quit_mode == QuitMode.PLACE_ALL_PENDING:  # place all monitor orders
            for order in monitor_orders:
                self._place_limit_order(order=order)
                log.info(f'trading limit order {order.k_side} {order.status} {order.price}')
                time.sleep(0.1)

        elif quit_mode == QuitMode.TRADE_ALL_PENDING:  # trade diff orders at reference side (BUY or SELL)
            # get diff to know at which side to trade & set reference orders
            buy_orders = []
            sell_orders = []
            for order in monitor_orders:
                if order.k_side == k_binance.SIDE_BUY:
                    buy_orders.append(order)
                    diff += 1
                elif order.k_side == k_binance.SIDE_SELL:
                    sell_orders.append(order)
                    diff -= 1

            log.info(f'diff: {diff}')
            # trade only diff count orders at market price (cmp), at the right side
            if diff == 0:
                pass
            elif diff > 0:  # BUY SIDE
                log.info('BUY SIDE')
                for i in range(diff):
                    order = buy_orders[i]
                    self._place_market_order(order=order)
                    log.info(f'trading reference market order {order.k_side} {order.status}')
                    time.sleep(0.1)
            elif diff < 0:  # SELL SIDE
                log.info('SELL SIDE')
                for i in range(-diff):
                    order = sell_orders[i]
                    self._place_market_order(order=order)
                    log.info(f'trading reference market order {order.k_side} {order.status}')
                    time.sleep(0.1)

        # log final info
        self.ptm.log_perfect_trades_info()

        net_profit = self.ptm.get_stop_cmp_profit(cmp=self.cmps[-1])

        log.info(f'session {self.session_id} stopped with net profit: {net_profit:,.2f}')

        self.session_stopped_callback(
            self.session_id,
            net_profit if abs(net_profit) < 3 else 0,
            self.cmp_count,
            abs(diff)  # number of orders placed at its own price
        )
