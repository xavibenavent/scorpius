# sc_pt_manager.py

from typing import Optional, List
from binance import enums as k_binance
import configparser

from sc_order import Order, OrderStatus
from sc_pending_orders_book import PendingOrdersBook
from sc_pt_calculator import get_prices_given_neb  # get_pt_values
from sc_perfect_trade import PerfectTrade, PerfectTradeStatus


class PTManager:
    def __init__(self, pob: PendingOrdersBook, symbol_filters, session_id: str):
        self.pob = pob
        self.symbol_filters = symbol_filters
        self.session_id = session_id
        self.pt_created_count = 0

        # list with all the perfect trades created
        self.perfect_trades: List[PerfectTrade] = []

        # read config.ini
        config = configparser.ConfigParser()
        config.read('config.ini')
        self.distance_to_target_price = float(config['SESSION']['distance_to_target_price'])

    def create_new_pt(self, cmp: float, pt_type='NORMAL') -> float:
        created_orders = 0

        # create new orders
        b1, s1 = self._get_b1s1(mp=cmp)

        if b1 and s1:
            # add orders to list
            self.pob.monitor.append(b1)
            self.pob.monitor.append(s1)

            # ********** update control variables **********
            # increase created counter
            self.pt_created_count += 1
            # set pt_id based on created counter
            pt_id = f'{self.pt_created_count:03}'
            b1.pt_id = pt_id
            s1.pt_id = pt_id
            # set number of trades needed for next pt creation
            created_orders = -2

            # create new perfect trade from orders and add to list
            # new_pt = PerfectTrade(pt_id=pt_id, buy_order=b1, sell_order=s1, pt_type=pt_type)
            new_pt = PerfectTrade(pt_id=pt_id, orders=[b1, s1], pt_type=pt_type)
            self.perfect_trades.append(new_pt)

            # set order references
            b1.sibling_order = s1
            s1.sibling_order = b1
            b1.pt = new_pt
            s1.pt = new_pt
        else:
            print('\n********** CRITICAL ERROR CREATING PT **********\n')
        return created_orders

    def order_traded(self, order: Order):
        # update status of the appropriate perfect trade depending on order side
        pt = order.pt
        so = order.sibling_order

        # check whether it is the first order traded in the pt or not
        if pt.status == PerfectTradeStatus.NEW:
            # update the other order price and target_price
            # update perfect trade status
            # get approximate gap * 2
            b1_price, s1_price, quantity = get_prices_given_neb(mp=order.price)
            gap = s1_price - b1_price
            print(f'gap: {gap}')

            if order.k_side == k_binance.SIDE_BUY:
                pt.status = PerfectTradeStatus.BUY_TRADED
                so.price = order.price + gap # price
                so.target_price = so.price + self.distance_to_target_price  # target price
            elif order.k_side == k_binance.SIDE_SELL:
                pt.status = PerfectTradeStatus.SELL_TRADED
                so.price = order.price - gap
                so.target_price = so.price - self.distance_to_target_price

        # check whether the pt is partially traded or completed
        elif pt.status in [PerfectTradeStatus.BUY_TRADED, PerfectTradeStatus.SELL_TRADED]:
            completed = True
            # check if all orders have been traded
            for order in pt.orders:
                if order.status != OrderStatus.TRADED:
                    completed = False
                    break

            if completed:
                pt.status = PerfectTradeStatus.COMPLETED

    def get_total_actual_profit(self, cmp: float) -> float:
        # return the total profit considering that all remaining orders are traded at current cmp
        total = 0
        for pt in self.perfect_trades:
            total += pt.get_actual_profit(cmp=cmp)
        return total

    def get_pt_completed_profit(self) -> float:
        # return the total profit considering only the completed perfect trades
        total = 0
        for pt in self.perfect_trades:
            if pt.status == PerfectTradeStatus.COMPLETED:
                # since the pt is completed, the cmp value does not matter
                total += pt.get_actual_profit(cmp=0)
        return total

    def _get_b1s1(self,
                  mp: float,
                  ) -> (Optional[Order], Optional[Order]):
        b1 = None
        s1 = None

        order_id = 'NA'

        # get perfect trade
        b1_price, s1_price, quantity = get_prices_given_neb(mp=mp)

        # check filters before creating order
        if Order.is_filter_passed(filters=self.symbol_filters, qty=quantity, price=b1_price):
            # create orders
            b1 = Order(
                order_id=order_id,
                k_side=k_binance.SIDE_BUY,
                price=b1_price,
                amount=quantity,
                name='b1'
            )
        else:
            pass
            # log.critical(f'trying to create an order that do not meet limits: {dynamic_parameters}')

        if Order.is_filter_passed(filters=self.symbol_filters, qty=quantity, price=s1_price):
            s1 = Order(
                order_id=order_id,
                k_side=k_binance.SIDE_SELL,
                price=s1_price,
                amount=quantity,
                name='s1'
            )
        else:
            pass
            # log.critical(f'trying to create an order that do not meet limits: {dynamic_parameters}')

        return b1, s1
