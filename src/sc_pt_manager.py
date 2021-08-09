# sc_pt_manager.py

from typing import Optional, List
from binance import enums as k_binance

from sc_order import Order
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

    def create_new_pt(self, cmp: float) -> float:
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
            new_pt = PerfectTrade(pt_id=pt_id, buy_order=b1, sell_order=s1)
            self.perfect_trades.append(new_pt)
        else:
            print('\n********** CRITICAL ERROR CREATING PT **********\n')
        return created_orders

    def order_traded(self, order: Order):
        # update status of the appropriate perfect trade
        for pt in self.perfect_trades:
            if pt.pt_id == order.pt_id:
                if order.k_side == k_binance.SIDE_BUY:
                    if pt.status == PerfectTradeStatus.NEW:
                        pt.status = PerfectTradeStatus.BUY_TRADED
                    elif pt.status == PerfectTradeStatus.SELL_TRADED:
                        pt.status = PerfectTradeStatus.COMPLETED
                    else:
                        # log error
                        pass
                elif order.k_side == k_binance.SIDE_SELL:
                    if pt.status == PerfectTradeStatus.NEW:
                        pt.status = PerfectTradeStatus.SELL_TRADED
                    elif pt.status == PerfectTradeStatus.BUY_TRADED:
                        pt.status = PerfectTradeStatus.COMPLETED
                    else:
                        # log error
                        pass
                else:
                    # log error
                    pass

                # once updated the pt, the loop through pt list is terminated
                break

    def show_pt_list_for_actual_cmp(self, cmp: float):
        print(f'cmp: {cmp}')
        for pt in self.perfect_trades:
            print(f'pt: {pt.pt_id}  value: {pt.get_actual_profit(cmp=cmp)}')

    def get_total_actual_profit(self, cmp: float) -> float:
        total = 0
        for pt in self.perfect_trades:
            total += pt.get_actual_profit(cmp=cmp)
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
                session_id=self.session_id,
                order_id=order_id,
                pt_id='PENDING',
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
                session_id=self.session_id,
                order_id=order_id,
                pt_id='PENDING',
                k_side=k_binance.SIDE_SELL,
                price=s1_price,
                amount=quantity,
                name='s1'
            )
        else:
            pass
            # log.critical(f'trying to create an order that do not meet limits: {dynamic_parameters}')

        return b1, s1
