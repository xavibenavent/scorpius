# sc_pt_manager.py
from typing import Optional
from binance import enums as k_binance

from sc_order import Order
from sc_pending_orders_book import PendingOrdersBook
from sc_pt_calculator import get_pt_values

PT_NET_AMOUNT_BALANCE = 0.00002  # 0.000020
PT_S1_AMOUNT = 0.023  # 0.022
PT_BUY_FEE = 0.08 / 100
PT_SELL_FEE = 0.08 / 100
PT_GROSS_EUR_BALANCE = 0.0


class PTManager:
    def __init__(self, pob: PendingOrdersBook, symbol_filters, session_id: str):
        self.pob = pob
        self.symbol_filters = symbol_filters
        self.session_id = session_id
        self.pt_created_count = 0

    def create_new_pt(self, cmp: float) -> float:
        created_orders = 0
        # get parameters
        dp = dict(
            mp=cmp,
            nab=PT_NET_AMOUNT_BALANCE,
            s1_qty=PT_S1_AMOUNT,
            buy_fee=PT_BUY_FEE,
            sell_fee=PT_SELL_FEE,
            geb=PT_GROSS_EUR_BALANCE)

        # create new orders
        b1, s1 = self.get_b1s1(dynamic_parameters=dp)

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
        else:
            # log.critical('the pt (b1, s1) can not be created:')
            # log.critical(f'b1: {b1}')
            # log.critical(f's1: {s1}')
            print('\n********** CRITICAL ERROR CREATING PT **********\n')
        return created_orders

    def get_b1s1(self,
                 dynamic_parameters: dict,
                 ) -> (Optional[Order], Optional[Order]):
        b1 = None
        s1 = None

        order_id = 'NA'

        # get perfect trade
        b1_qty, b1_price, s1_price, g = get_pt_values(**dynamic_parameters)
        s1_qty = dynamic_parameters.get('s1_qty')

        # check filters before creating order
        if Order.is_filter_passed(filters=self.symbol_filters, qty=b1_qty, price=b1_price):
            # create orders
            b1 = Order(
                session_id=self.session_id,
                order_id=order_id,
                pt_id='PENDING',
                k_side=k_binance.SIDE_BUY,
                price=b1_price,
                amount=b1_qty,
                name='b1'
            )
        else:
            pass
            # log.critical(f'trying to create an order that do not meet limits: {dynamic_parameters}')

        if Order.is_filter_passed(filters=self.symbol_filters, qty=s1_qty, price=s1_price):
            s1 = Order(
                session_id=self.session_id,
                order_id=order_id,
                pt_id='PENDING',
                k_side=k_binance.SIDE_SELL,
                price=s1_price,
                amount=s1_qty,
                name='s1'
            )
        else:
            pass
            # log.critical(f'trying to create an order that do not meet limits: {dynamic_parameters}')

        return b1, s1
