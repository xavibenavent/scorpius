# pp_strategy_manager.py

from typing import List
import logging
from binance import enums as k_binance
from sc_order import Order
from sc_pending_orders_book import PendingOrdersBook
from sc_concentrator import ConcentratorManager
from sc_balance_manager import BalanceManager

log = logging.getLogger('log')

K_MIN_CYCLES_FOR_FIRST_SPLIT = 100  # the rationale for this parameter is to give time to complete (b1, s1)
K_DISTANCE_FOR_FIRST_CHILDREN = 200  # 150
K_DISTANCE_FOR_SECOND_CHILDREN = 300
K_DISTANCE_INTER_FIRST_CHILDREN = 50.0  # 50
K_DISTANCE_INTER_SECOND_CHILDREN = 50.0
K_DISTANCE_FIRST_COMPENSATION = 200  # 200.0
K_DISTANCE_SECOND_COMPENSATION = 350.0
K_GAP_FIRST_COMPENSATION = 50  # 50.0
K_GAP_SECOND_COMPENSATION = 120.0

# K_SPAN_FOR_CONCENTRATION = 500
K_DISTANCE_FOR_CONCENTRATION = 350
K_GAP_CONCENTRATION = 50
K_INTERDISTANCE_AFTER_CONCENTRATION = 25.0

PT_BUY_FEE = 0.08 / 100
PT_SELL_FEE = 0.08 / 100


class StrategyManager:
    def __init__(self,
                 pob: PendingOrdersBook,
                 cm: ConcentratorManager,
                 bm: BalanceManager):
        self.pob = pob
        self.cm = cm
        self.bm = bm

    def assess_strategy_actions(self, cmp: float) -> int:
        # main strategy
        trades_to_new_pt_delta = 0

        # # 0. asses balance needed
        # if self.bm.is_s1_below_buffer():
        #     # force BUY
        #     self._force_buy(cmp=cmp)
        #     pass
        # elif self.bm.is_s2_below_buffer():
        #     # force SELL
        #     self._force_sell(cmp=cmp)
        #     pass

        # 1. assess n-child in monitor list
        # trades_to_new_pt_delta += self.check_monitor_list_for_n_child(cmp=cmp)

        # 2. assess compensation in monitor list
        # trades_to_new_pt_delta += self.check_monitor_list_for_compensation(cmp=cmp)
        self.check_monitor_orders_for_compensation(cmp=cmp)

        # 3. assess extreme pairs b1-s1 to concentrate
        # TODO: implement it

        # 4. assess isolated side orders to balance
        # trades_to_new_pt_delta += self.check_side_balance(last_cmp=cmp)

        return trades_to_new_pt_delta

    def force_buy(self, cmp: float):
        # order monitor by price from higher to lower
        sorted_orders = sorted(self.pob.monitor, key=lambda x: x.price, reverse=True)
        for order in sorted_orders:
            print(order)
        # get lower
        lower_order = sorted_orders[-1]
        # concentrate it
        self.cm.concentrate_for_liquidity(order=lower_order, ref_mp=cmp + 110, ref_gap=100)

    def force_sell(self, cmp: float):
        # order monitor by price, from higher to lower
        sorted_orders = sorted(self.pob.monitor, key=lambda x: x.price, reverse=True)
        print(sorted_orders)
        # get lower
        higher_order = sorted_orders[0]
        # concentrate it
        self.cm.concentrate_for_liquidity(order=higher_order, ref_mp=cmp - 110, ref_gap=100)

    def _get_liquidity(self, cmp: float):
        # check whether there are orders in both sides or not
        is_one_side, side = self.pob.is_one_side()
        if is_one_side:
            pass
            # compensate the farthest order
        else:
            # select orders to concentrate based on momentum
            sorted_by_momentum = self.pob.get_monitor_sorted_by_momentum(cmp=cmp)

    def check_monitor_orders_for_compensation(self, cmp: float) -> None:
        pass

    def check_monitor_list_for_compensation(self, cmp: float) -> int:
        trades_to_new_pt_delta = 0
        for order in self.pob.monitor:
            # first compensation
            if order.compensation_count == 0 \
                    and order.split_count == 1 \
                    and order.get_distance(cmp=cmp) > K_DISTANCE_FIRST_COMPENSATION:  # 200
                # compensate
                if self.cm.concentrate_orders(  # return true if compensation Ok
                        orders=[order],
                        ref_mp=cmp,
                        ref_gap=K_GAP_FIRST_COMPENSATION):
                    # decrease only if compensation Ok
                    trades_to_new_pt_delta -= 1
                else:
                    log.critical(f'compensation failed!!! {order}')
        return trades_to_new_pt_delta

    def check_monitor_list_for_n_child(self, cmp: float) -> int:
        trades_to_new_pt_delta = 0
        for order in self.pob.monitor:
            # first split
            if order.cycles_count > K_MIN_CYCLES_FOR_FIRST_SPLIT \
                    and order.compensation_count == 0 \
                    and order.split_count == 0 \
                    and order.get_distance(cmp=cmp) > K_DISTANCE_FOR_FIRST_CHILDREN:  # 150
                # split into n children
                child_count = 2
                self.cm.split_n_order(
                    order=order,
                    inter_distance=K_DISTANCE_INTER_FIRST_CHILDREN,
                    child_count=child_count,
                )
                trades_to_new_pt_delta -= (child_count - 1)
        return trades_to_new_pt_delta

    def assess_concentration(self, last_cmp: float) -> float:
        # sell_count = 0
        # buy_count = 0
        # orders_to_concentrate: List[Order] = []
        # # get number of orders for each side with distance > K_DISTANCE_FOR_CONCENTRATION
        # for order in check_orders:
        #     if order.k_side == k_binance.SIDE_BUY and order.get_distance(last_cmp) > K_DISTANCE_FOR_CONCENTRATION:
        #         buy_count += 1
        #         orders_to_concentrate.append(order)
        #     elif order.k_side == k_binance.SIDE_SELL and order.get_distance(last_cmp) > K_DISTANCE_FOR_CONCENTRATION:
        #         sell_count += 1
        #         orders_to_concentrate.append(order)
        #
        # # concentration only if orders in both sides
        # if buy_count > 0 and sell_count > 0:
        #     return orders_to_concentrate
        # return []
        pass

    def check_side_balance(self, last_cmp: float) -> float:
        trades_to_new_pt_delta = 0  # return value
        sell_count = 0
        buy_count = 0
        orders_to_balance: List[Order] = []
        orders: List[Order] = []
        child_count = 0
        # get number of orders for each side with distance > K_DISTANCE_FOR_CONCENTRATION
        for order in self.pob.monitor:
            if order.concentration_count == 0:  # check it
                if order.k_side == k_binance.SIDE_BUY:
                    buy_count += 1
                    if order.get_distance(last_cmp) > 200:
                        orders.append(order)
                elif order.k_side == k_binance.SIDE_SELL:
                    sell_count += 1
                    if order.get_distance(last_cmp) > 200:
                        orders.append(order)

        # concentration only if at least 3 orders in one single side with d>150
        if buy_count == 0 and len(orders) > 2:
            orders_to_balance.extend(orders)
        elif sell_count == 0 and len(orders) > 2:
            orders_to_balance.extend(orders)

        if len(orders_to_balance) > 0:
            if self.cm.concentrate_orders(
                    orders=orders_to_balance,
                    ref_mp=last_cmp,
                    ref_gap=100,  # TODO: to parameter
                    ):
                # decrease only if compensation Ok
                # TODO: correct it
                trades_to_new_pt_delta += len(orders_to_balance) - 2 - child_count
                log.info('SIDE BALANCE OK')
            else:
                log.critical('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
                for order in orders_to_balance:
                    log.critical(f'SIDE BALANCE failed for concentration reasons!!! {order}')

        return trades_to_new_pt_delta
