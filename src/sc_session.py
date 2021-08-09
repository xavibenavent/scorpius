# sc_session.py

import logging
from datetime import datetime
from enum import Enum
import pandas as pd

from typing import Optional
from binance import enums as k_binance

from sc_market import Market
from sc_order import Order, OrderStatus
from sc_account_balance import AccountBalance
from sc_pending_orders_book import PendingOrdersBook
from sc_traded_orders_book import TradedOrdersBook
from sc_strategy_manager import StrategyManager
from sc_balance_manager import BalanceManager
from sc_concentrator import ConcentratorManager
from sc_pt_manager import PTManager
from sc_perfect_trade import PerfectTrade, PerfectTradeStatus

import configparser


log = logging.getLogger('log')


class QuitMode(Enum):
    CANCEL_ALL_PLACED = 1
    PLACE_ALL_PENDING = 2


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

        self._min_dist_for_placement = float(config['SESSION']['min_dist_for_placement'])
        self._max_dist_for_remaining_placed = float(config['SESSION']['max_dist_for_remaining_placed'])
        self._one_placement_for_cycle = config['SESSION'].getboolean('one_placement_for_cycle')
        self._pt_created_count_max = float(config['SESSION']['pt_created_count_max'])

        # get filters that will be checked before placing an order
        self.symbol_filters = self.market.get_symbol_info(symbol='BTCEUR')

        # ********** managers **********
        self.bm = BalanceManager(market=self.market)
        self.pob = PendingOrdersBook(orders=[])
        self.tob = TradedOrdersBook()
        self.cm = ConcentratorManager(pob=self.pob, tob=self.tob)
        self.sm = StrategyManager(pob=self.pob, cm=self.cm, bm=self.bm)

        self.session_id = f'S_{datetime.now().strftime("%Y%m%d_%H%M")}'

        self.ptm = PTManager(pob=self.pob,
                             symbol_filters=self.symbol_filters,
                             session_id=self.session_id)

        # *********** concentrator **********

        self.cmps = []
        self.cycles_serie = []  # TODO: change to series
        self.orders_book_depth = []
        self.orders_book_span = []

        self.pt_created_count = 0
        self.buy_count = 0
        self.sell_count = 0
        self.cmp_count = 0

        # self.dashboard = None

        self.new_pt_permission_granted = True

        self.cycles_from_last_trade = 0

        self.market.start_sockets()

        self.last_cmp = self.market.get_cmp('BTCEUR')

        self.ticker_count = 0

        # self.partial_traded_orders_count = 0

    # ********** dashboard callback functions **********
    def get_last_cmp(self):
        if len(self.cmps) > 0:
            return self.cmps[-1]
        else:
            return 0

    def get_all_orders_dataframe(self) -> pd.DataFrame:
        # get list with all orders: pending (monitor + placed) & traded (completed + pending_pt_id)
        all_orders = self.pob.get_pending_orders() + self.tob.get_all_traded_orders()
        # create dataframe
        df = pd.DataFrame([order.__dict__ for order in all_orders])
        # delete status column because it returns a tuple and raises an error in the dash callback
        df1 = df.drop(columns='status', axis=1)
        return df1

    def get_all_orders_dataframe_with_cmp(self) -> pd.DataFrame:
        df = self.get_all_orders_dataframe()
        # create cmp order-like and add to dataframe
        cmp_order = dict(pt_id='CMP', status_name='cmp', price=self.last_cmp)
        df1 = df.append(other=cmp_order, ignore_index=True)
        return df1

    # ********** Binance socket callback functions **********

    def symbol_ticker_callback(self, cmp: float) -> None:
        print(cmp)
        try:
            # 0.1: create first pt
            if self.ticker_count == 0 and cmp > 20000.0:
                # self.partial_traded_orders_count += self.ptm.create_new_pt(cmp=cmp)
                # self.ptm.create_new_pt(cmp=cmp)
                pass

            # 0.2: update cmp count to control timely pt creation
            self.cmp_count += 1
            self.ticker_count += 1

            # these two lists will be used to plot
            self.cmps.append(cmp)
            self.cycles_serie.append(self.cmp_count)

            self.last_cmp = cmp
            self.cycles_from_last_trade += 1

            # 2. loop through placed orders and move to monitor list if isolated
            # self.check_placed_list_for_move_back(cmp=cmp)

            # strategy manager and update of trades needed for new pt
            # self.partial_traded_orders_count += self.sm.assess_strategy_actions(cmp=cmp)
            self.sm.assess_strategy_actions(cmp=cmp)

            # todo: check active list for trading or parameters update
            # it is important to check first the active list and the the monitor one
            # with this order we guarantee there is only one status change per cycle
            self.check_active_list_for_trading(cmp=cmp)

            # 4. todo: loop through monitoring orders for activating
            self.check_monitor_list_for_activating(cmp=cmp)

            # 5. check inactivity & liquidity
            self.check_inactivity(cmp=cmp)

            # todo: check new feature regarding perfect trades
            # self.ptm.show_pt_list_for_actual_cmp(cmp=cmp)

        except AttributeError as e:
            print(e)

    def check_inactivity(self, cmp):
        if self.cycles_from_last_trade > 125:  # TODO: magic number (5')
            self.ptm.create_new_pt(cmp=cmp)
            self.cycles_from_last_trade = 0  # equivalent to trading but without a trade

    def check_monitor_list_for_activating(self, cmp: float) -> None:
        for order in self.pob.monitor:
            order.cycles_count += 1
            if order.is_ready_for_activation(cmp=cmp):
                self.pob.active_order(order=order)

    def check_active_list_for_trading(self, cmp: float) -> None:
        for order in self.pob.active:
            order.cycles_count += 1
            if order.is_ready_for_trading(cmp=cmp):
                # check whether it is the first order traded in the pt or not
                # pt = self.ptm.get_pt_by_pt_id(pt_id=order.pt_id)
                if order.pt.status == PerfectTradeStatus.NEW:
                    # todo: set the other order price and price parameters (C, L, T)
                    if order.k_side == k_binance.SIDE_BUY:
                        order.pt.status = PerfectTradeStatus.BUY_TRADED
                        order.sibling_order.price = cmp + 100.0
                    elif order.k_side == k_binance.SIDE_SELL:
                        order.pt.status = PerfectTradeStatus.SELL_TRADED
                        order.sibling_order.price = cmp - 100.0
                    pass
                self.pob.trade_order(order=order)

    def _process_place_order(self, order: Order) -> bool:
        new_placement_allowed = True
        self.pob.place_order(order=order)
        is_order_placed, new_status = self._place_order(order=order)
        # new_status can be FILLED, if the order was traded right after being placed
        if is_order_placed:
            # 2. placed: (s: PLACED, t: pending_orders, l: placed)
            if new_status == 'NEW':
                order.set_status(status=OrderStatus.PLACED)
            elif new_status == 'FILLED':
                order.set_status(status=OrderStatus.TRADED)
                if order in self.pob.placed:
                    log.critical('order removed from placed')
                    self.pob.placed.remove(order)
            # to control one new placement per cycle mode
            if self._one_placement_for_cycle:
                new_placement_allowed = False
        else:
            self.pob.place_back_order(order=order)
            log.critical(f'for unknown reason the order has not been placed: {order}')
        return new_placement_allowed

    def order_traded_callback(self, uid: str, order_price: float, bnb_commission: float) -> None:
        # print(f'********** ORDER TRADED:    price: {order_price} [EUR] - commission: {bnb_commission} [BNB]')
        # get the order by uid
        for order in self.pob.placed:
            if order.uid == uid:
                print(f'********** order traded: {order}')
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
                    bnbbtc_rate=self.market.get_cmp(symbol='BNBBTC'))
                order.price = order_price
                # change status
                order.set_status(status=OrderStatus.TRADED)
                # remove from placed list
                self.pob.placed.remove(order)
                # add to traded list (once removed from placed list) depending on whether is pt_id completed or not
                if self.pob.has_completed_pt_id(order=order):
                    # completed
                    self.tob.add_completed(order=order)
                else:
                    self.tob.add_pending(order=order)

                # todo: update perfect trades list
                self.ptm.order_traded(order=order)

                # update counter for next pt
                # self.partial_traded_orders_count += 1
                # check whether a new pt is allowed or not
                # if self.pt_created_count < PT_CREATED_COUNT_MAX and self.partial_traded_orders_count >= 0:
                #     self.partial_traded_orders_count += self.ptm.create_new_pt(cmp=self.last_cmp)
                if self.pt_created_count < self._pt_created_count_max and len(self.pob.get_pending_orders()) == 0:
                    self.ptm.create_new_pt(cmp=self.last_cmp)
                else:
                    log.info('no new pt created after the last traded order')
                # since the traded orders has been identified, do not check more orders
                break

    def account_balance_callback(self, ab: AccountBalance) -> None:
        # update of current balance from Binance
        self.bm.update_current(last_ab=ab)

    # ********** check methods **********
    def _place_order(self, order) -> (bool, Optional[str]):
        order_placed = False
        status_received = None
        # place order
        d = self.market.place_order(order=order)
        if d:
            order_placed = True
            order.set_binance_id(new_id=d.get('binance_id'))
            status_received = d.get('status')
            # log.debug(f'********** ORDER PLACED **********      msg: {d}')
        else:
            log.critical(f'error placing {order}')
        return order_placed, status_received

    def quit(self, quit_mode: QuitMode):
        # action depending upon quit mode
        if quit_mode == QuitMode.CANCEL_ALL_PLACED:
            print('********** CANCELLING ALL PLACED ORDERS **********')
            self.market.cancel_orders(self.pob.placed)
        elif quit_mode == QuitMode.PLACE_ALL_PENDING:
            print('********** PLACE ALL PENDING ORDERS **********')
            for order in self.pob.monitor:
                self.market.place_order(order)

        # check for correct cancellation of all orders
        btc_bal = self.market.get_asset_balance(asset='BTC',
                                                tag='check for zero locked')
        eur_bal = self.market.get_asset_balance(asset='EUR',
                                                tag='check for zero locked')
        if btc_bal.locked != 0 or eur_bal.locked != 0:
            log.critical('after cancellation of all orders, locked balance should be 0')
            log.critical(btc_bal)
            log.critical(eur_bal)
        else:
            log.info(f'LOCKED BALANCE CHECK CORRECT: btc_balance: {btc_bal} - eur_balance: {eur_bal}')

        self.market.stop()
