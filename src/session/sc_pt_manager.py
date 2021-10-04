# sc_pt_manager.py

from typing import Optional, List
from binance import enums as k_binance
import logging

from basics.sc_order import Order, OrderStatus
from session.sc_pt_calculator import get_prices_given_neb  # get_pt_values
from basics.sc_perfect_trade import PerfectTrade, PerfectTradeStatus
from basics.sc_symbol import Symbol

log = logging.getLogger('log')


class PTManager:
    # def __init__(self, symbol_filters, session_id: str):
    def __init__(self, session_id: str, symbol: Symbol):
        self.session_id = session_id
        self.symbol = symbol
        self.pt_created_count = 0

        # list with all the perfect trades created
        self.perfect_trades: List[PerfectTrade] = []

        config = symbol.config_data
        self.distance_to_target_price = float(config['distance_to_target_price'])
        self.fee = float(config['fee'])
        self.net_quote_balance = float(config['net_quote_balance'])

    def create_new_pt(self, cmp: float, symbol: Symbol, pt_type='NORMAL') -> (Order, Order):
        # create and get new orders
        b1, s1 = self._get_b1s1(symbol=symbol, mp=cmp)

        if b1 and s1:
            # increase created counter
            self.pt_created_count += 1

            # set pt_id based on created counter
            pt_id = f'{self.pt_created_count:03}'

            # create new perfect trade from orders and add it to perfect trades list
            new_pt = PerfectTrade(pt_id=pt_id, orders=[b1, s1], pt_type=pt_type)
            self.perfect_trades.append(new_pt)
            return b1, s1
        else:
            raise Exception('********** CRITICAL ERROR CREATING PT **********')

    def get_first_gap(self) -> float:
        if len(self.perfect_trades) > 0:
            return self.perfect_trades[0].get_gap()
        else:
            return 0.0

    def order_traded(self, order: Order) -> None:
        # update status of the appropriate perfect trade depending on order side
        pt = order.pt
        so = order.sibling_order

        # check whether it is the first order traded in the pt or not
        if pt.status == PerfectTradeStatus.NEW:
            # update the other order price and target_price
            # update perfect trade status
            # get approximate gap * 2
            b1_price, s1_price, quantity = get_prices_given_neb(mp=order.price, symbol=self.symbol)
            gap = s1_price - b1_price

            if order.k_side == k_binance.SIDE_BUY:
                pt.status = PerfectTradeStatus.BUY_TRADED
                so.price = order.price + gap  # price
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

    def get_total_actual_profit_at_cmp(self, cmp: float) -> float:
        # return the total profit considering that all remaining orders are traded at current cmp
        # perfect trades with status NEW are not considered
        total = 0
        for pt in self.perfect_trades:
            total += pt.get_actual_profit_at_cmp(cmp=cmp)
        return total

    def get_stop_price_profit(self, cmp: float) -> float:
        # return the total profit considering that all remaining orders are traded at its own price
        # perfect trades with status NEW are not considered
        # MONITOR orders are considered to be traded at their price
        total = 0
        orders = self.get_orders_by_request(
            orders_status=[OrderStatus.ACTIVE, OrderStatus.MONITOR, OrderStatus.TRADED],
            pt_status=[PerfectTradeStatus.BUY_TRADED, PerfectTradeStatus.SELL_TRADED, PerfectTradeStatus.COMPLETED]
        )
        for order in orders:
            if order.status == OrderStatus.MONITOR:
                total += order.get_total_at_cmp(cmp=order.price)
            elif order.status == OrderStatus.ACTIVE:
                total += order.get_total_at_cmp(cmp=cmp)
            elif order.status == OrderStatus.TRADED:
                total += order.get_total_at_cmp(cmp=order.price)
        return total

    def get_consolidated_profit(self) -> float:
        return sum([pt.get_consolidated_profit() for pt in self.perfect_trades])

    def get_expected_profit(self) -> float:
        return sum([pt.get_original_expected_profit()
                    for pt in self.perfect_trades
                    if pt.status in [PerfectTradeStatus.BUY_TRADED, PerfectTradeStatus.SELL_TRADED]])

    def get_orders_by_request(self, orders_status: List[OrderStatus], pt_status: List[PerfectTradeStatus]):
        requested_orders: List[Order] = []
        # get list of perfect trades that match the condition
        requested_pts = [pt for pt in self.perfect_trades if pt.status in pt_status]
        for pt in requested_pts:
            for order in pt.orders:
                if order.status in orders_status:
                    requested_orders.append(order)
        return requested_orders

    def get_pt_by_request(self, pt_status: List[PerfectTradeStatus]) -> List[PerfectTrade]:
        return [pt for pt in self.perfect_trades if pt.status in pt_status]

    def get_all_alive_orders(self) -> List[Order]:
        # 0. get 'alive' buy & sell orders (monitor + active)
        orders_alive = self.get_orders_by_request(
            orders_status=[OrderStatus.MONITOR, OrderStatus.ACTIVE],
            pt_status=[PerfectTradeStatus.NEW, PerfectTradeStatus.BUY_TRADED, PerfectTradeStatus.SELL_TRADED]
        )
        return orders_alive

    def get_symbol_liquidity_needed(self) -> (float, float):
        # return the quote & base needed to trade all 'alive' orders at its own price
        alive_orders = self.get_all_alive_orders()
        # get total quote needed to trade all alive buy orders
        quote_asset_needed = sum([order.get_total_at_cmp(cmp=order.price, with_commission=False, signed=False)
                                  for order in alive_orders
                                  if order.k_side == k_binance.SIDE_BUY])
        # get total base needed to trade all alive sell orders
        base_asset_needed = sum([order.get_amount(signed=False)
                                 for order in alive_orders
                                 if order.k_side == k_binance.SIDE_SELL])

        return quote_asset_needed, base_asset_needed

    def get_momentum(self, cmp: float) -> (float, float, float):
        # get orders
        buy_momentum_orders = self.get_orders_by_request(
            orders_status=[OrderStatus.MONITOR, OrderStatus.ACTIVE],
            pt_status=[PerfectTradeStatus.SELL_TRADED]
        )
        sell_momentum_orders = self.get_orders_by_request(
            orders_status=[OrderStatus.MONITOR, OrderStatus.ACTIVE],
            pt_status=[PerfectTradeStatus.BUY_TRADED]
        )
        # calculate momentum
        buy_momentum = sum([order.momentum(cmp=cmp) for order in buy_momentum_orders])
        sell_momentum = sum([order.momentum(cmp=cmp) for order in sell_momentum_orders])
        return sell_momentum - buy_momentum, buy_momentum, sell_momentum

    def _get_b1s1(self,
                  symbol: Symbol,
                  mp: float,
                  ) -> (Optional[Order], Optional[Order]):

        order_id = f'{self.pt_created_count + 1:03d}' + self.session_id

        # get perfect trade
        b1_price, s1_price, quantity = get_prices_given_neb(mp=mp, symbol=self.symbol)

        # create orders
        b1 = Order(
            symbol=symbol,
            order_id='BUYY' + order_id,
            k_side=k_binance.SIDE_BUY,
            price=b1_price,
            amount=quantity,
            name='b1'
        )
        s1 = Order(
            symbol=symbol,
            order_id='SELL' + order_id,
            k_side=k_binance.SIDE_SELL,
            price=s1_price,
            amount=quantity,
            name='s1'
        )
        return b1, s1

    def log_perfect_trades_info(self):
        for pt in self.perfect_trades:
            log.info(f'perfect trade {pt.id} {pt.pt_type} {pt.status.name}')
            for order in pt.orders:
                log.info(f'  order {order.k_side} {order.get_amount(signed=False)} '
                         f'{order.get_price_str()} {order.status.name}')
