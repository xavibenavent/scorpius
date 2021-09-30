# sc_checks_manager.py

import logging
from binance import enums as k_binance
from typing import List

from managers.sc_isolated_manager import IsolatedOrdersManager
from managers.sc_strategy_manager import StrategyManager
from session.sc_pt_manager import PTManager, PerfectTradeStatus
from session.sc_helpers import Helpers, QuitMode
from basics.sc_order import Order, OrderStatus
from market.sc_market_api_out import MarketAPIOut
from basics.sc_symbol import Symbol
from basics.sc_action import Action


log = logging.getLogger('log')


class ChecksManager:
    def __init__(self,
                 iom: IsolatedOrdersManager,
                 strategy_manager: StrategyManager,
                 ptm: PTManager,
                 helpers: Helpers,
                 market_api_out: MarketAPIOut,
                 config: dict,
                 symbol: Symbol):
        self.iom = iom
        self.strategy_manager = strategy_manager
        self.ptm = ptm
        self.helpers = helpers
        self.market_api_out = market_api_out
        self.symbol = symbol

        # parameters needed from config.ini
        self.P_TARGET_TOTAL_NET_PROFIT = float(config['target_total_net_profit'])
        self.P_MAX_NEGATIVE_PROFIT_ALLOWED = float(config['max_negative_profit_allowed'])
        self.P_DISTANCE_FOR_REPLACING_ORDER = float(config['distance_for_replacing_order'])
        self.P_CONSOLIDATED_VS_ACTIONS_COUNT_RATE = float(config['consolidated_vs_actions_count_rate'])
        self.P_CANCEL_MAX = int(config['cancel_max'])
        self.P_QUANTITY = float(config['quantity'])
        self.P_TRIES_TO_FORCE_GET_LIQUIDITY = int(config['tries_to_force_get_liquidity'])
        self.P_MIN_DISTANCE_FOR_CANCELING_ORDER = float(config['min_distance_for_canceling_order'])
        self.P_FORCED_SHIFT = float(config['forced_shift'])

        self.base_negative_try_count = 0
        self.quote_negative_try_count = 0

    def check_monitor_orders_for_activating(self, cmp: float):
        # get orders
        monitor_orders = self.ptm.get_orders_by_request(
            orders_status=[OrderStatus.MONITOR],
            pt_status=[PerfectTradeStatus.NEW, PerfectTradeStatus.BUY_TRADED, PerfectTradeStatus.SELL_TRADED]
        )
        # change status MONITOR -> ACTIVE
        [order.set_status(OrderStatus.ACTIVE) for order in monitor_orders if order.is_ready_for_activation(cmp=cmp)]

    def check_active_orders_for_trading(self, cmp: float) -> None:
        # get orders
        active_orders = self.ptm.get_orders_by_request(
            orders_status=[OrderStatus.ACTIVE],
            pt_status=[PerfectTradeStatus.NEW, PerfectTradeStatus.BUY_TRADED, PerfectTradeStatus.SELL_TRADED]
        )
        # trade at market price active orders ready for trading
        [self.helpers.place_market_order(order=order) for order in active_orders if order.is_ready_for_trading(cmp=cmp)]

    def check_exit_conditions(self, cmp: float, session_id: str, cmp_count: int):
        # check profit only if orders are stable (no ACTIVE nor TO_BE_TRADED)
        orders = self.ptm.get_orders_by_request(
            orders_status=[OrderStatus.ACTIVE, OrderStatus.TO_BE_TRADED],
            pt_status=[PerfectTradeStatus.NEW, PerfectTradeStatus.BUY_TRADED, PerfectTradeStatus.SELL_TRADED]
        )
        if len(orders) == 0:
            # 8. check global net profit
            # return the total profit considering that all remaining orders are traded at current cmp
            total_profit = self.ptm.get_total_actual_profit_at_cmp(cmp=cmp)

            # exit point 1: target achieved
            if total_profit > self.P_TARGET_TOTAL_NET_PROFIT:
                log.info('exit point #1: TRADE_ALL_PENDING')

                # todo: check whether it works without it
                # self.session_active = False

                # self.quit_particular_session(quit_mode=QuitMode.TRADE_ALL_PENDING)
                self.helpers.quit_particular_session(quit_mode=QuitMode.TRADE_ALL_PENDING,
                                                     session_id=session_id,
                                                     symbol=self.symbol,
                                                     cmp=cmp,
                                                     iom=self.iom,
                                                     cmp_count=cmp_count)

            # exit point 2: reached maximum allowed loss
            elif total_profit < self.P_MAX_NEGATIVE_PROFIT_ALLOWED:
                log.info('exit point #2: PLACE_ALL_PENDING by max negative profit reached')

                # todo: check whether it works without it
                # self.session_active = False

                self.helpers.quit_particular_session(quit_mode=QuitMode.PLACE_ALL_PENDING,
                                                     session_id=session_id,
                                                     symbol=self.symbol,
                                                     cmp=cmp,
                                                     iom=self.iom,
                                                     cmp_count=cmp_count)

            # exit point 3: reached target with completed pt
            else:
                completed_pt = self.ptm.get_pt_by_request(pt_status=[PerfectTradeStatus.COMPLETED])
                if sum([pt.get_actual_profit_at_cmp(cmp=cmp) for pt in completed_pt]) > self.P_TARGET_TOTAL_NET_PROFIT:
                    log.info('exit point #3: PLACE_ALL_PENDING by target reached with completed pt')

                    # todo: check whether it works without it
                    # self.session_active = False

                    self.helpers.quit_particular_session(quit_mode=QuitMode.PLACE_ALL_PENDING,
                                                         session_id=session_id,
                                                         symbol=self.symbol,
                                                         cmp=cmp,
                                                         iom=self.iom,
                                                         cmp_count=cmp_count)

    def check_pending_orders(self, cmp: float, consolidated_profit: float):
        # get pending orders that meet the criteria for re-placing
        pending_orders = [order for order in self.iom.get_all_orders(symbol_name=self.symbol.name)
                          if order.status == OrderStatus.CANCELED
                          and order.get_distance(cmp=cmp) < self.P_DISTANCE_FOR_REPLACING_ORDER]
        for order in pending_orders:
            log.info(f'pending order {order} to be processed')
            # set asset & liquidity needed depending upon k_side
            if order.k_side == k_binance.SIDE_SELL:
                asset = self.symbol.base_asset()
                counter_asset = self.symbol.quote_asset()
                liquidity_needed = order.amount
                counter_liquidity_needed = order.amount * order.price
            else:
                asset = self.symbol.quote_asset()
                counter_asset = self.symbol.base_asset()
                liquidity_needed = order.amount * order.price
                counter_liquidity_needed = order.amount

            log.info(f'PENDING_ORDER: asset: {asset.name()} liquidity needed: {liquidity_needed}')

            # check whether there is enough liquidity for placing it
            if self.strategy_manager.is_asset_liquidity_enough(asset=asset, new_pt_need=liquidity_needed):
                # place, change status & delete from database
                log.info(f'PENDING_ORDER: place, change status & delete from database')
                self.market_api_out.place_limit_order(order=order)
                order.status = OrderStatus.TO_BE_TRADED
                if order in self.iom.canceled_orders:
                    self.iom.canceled_orders.remove(order)
                else:
                    raise Exception(f'order {order} not in canceled_orders list')
                # self.dbm.delete_pending_order(pending_order_uid=order.uid)
            else:
                # since there will be no further orders of the same side to cancel and get liquidity
                # the only way is buying or selling depending upon the order side
                # check there is liquidity of the counter side to trade
                log.info(f'PENDING_ORDER: trying to buy/sell to get enough liquidity for canceling')
                counter_k_side = k_binance.SIDE_BUY if order.k_side == k_binance.SIDE_SELL else k_binance.SIDE_SELL

                # check rate condition to limit the number of created actions based on consolidated profit
                buy_actions, sell_actions, _ = self.get_actions_balance()
                actions_count = buy_actions if counter_k_side == k_binance.SIDE_BUY else sell_actions
                consolidated_actions_rate = consolidated_profit / (actions_count + 1)
                is_rate_ok = consolidated_actions_rate > self.P_CONSOLIDATED_VS_ACTIONS_COUNT_RATE

                if is_rate_ok and self.strategy_manager.is_asset_liquidity_enough(asset=counter_asset,
                                                                                  new_pt_need=counter_liquidity_needed):
                    # prepare & place market order
                    new_qty = order.amount / 2.0
                    new_order = Order(symbol=self.symbol,
                                      order_id='NO_ID',
                                      k_side=counter_k_side,
                                      price=order.price,
                                      amount=new_qty,
                                      status=OrderStatus.TO_BE_TRADED)
                    log.info(f'PENDING_ORDER: MARKET place order: {new_order}')
                    self.market_api_out.place_market_order(order=new_order)
                    # self.dbm.add_action(action=Action(
                    self.iom.actions.append(Action(
                        action_id='ACTION_FOR_CANCELING',
                        side=counter_k_side,
                        qty=new_qty,
                        price=cmp))

                else:
                    # cancel furthest counter order
                    log.info(f'PENDING_ORDER: cancel farthest at counter side')
                    furthest_order = self.iom.get_further_order(cmp=cmp,
                                                                k_side=counter_k_side,
                                                                min_distance=0.0)  # no need for this criteria
                    canceled_side_orders = [order for order in self.iom.canceled_orders
                                            if order.k_side == counter_k_side]
                    if furthest_order and len(canceled_side_orders) < self.P_CANCEL_MAX:
                        log.info(f'PENDING_ORDER: cancel order {furthest_order}')
                        self.market_api_out.cancel_orders([furthest_order])
                        self.iom.canceled_orders.append(furthest_order)

    def allow_new_pt_creation(self,
                              cmp: float,
                              consolidated_profit: float,
                              gap: float,
                              cmp_pattern_short: List[float],
                              cmp_pattern_long: List[float]) -> (bool, float):
        # 1. check liquidity
        # check base liquidity and try to get if not enough
        if not self.strategy_manager.is_asset_liquidity_enough(asset=self.symbol.base_asset(),
                                                               new_pt_need=self.P_QUANTITY):
            self.base_negative_try_count += 1
            if self.base_negative_try_count > self.P_TRIES_TO_FORCE_GET_LIQUIDITY:
                # get furthest order (or NOne)
                furthest_sell_order = self.iom.get_further_order(cmp=cmp,
                                                                 k_side=k_binance.SIDE_SELL,
                                                                 min_distance=self.P_MIN_DISTANCE_FOR_CANCELING_ORDER)
                canceled_sell_orders = [order for order in self.iom.canceled_orders
                                        if order.k_side == k_binance.SIDE_SELL]
                if furthest_sell_order and len(canceled_sell_orders) < self.P_CANCEL_MAX:
                    self.market_api_out.cancel_orders([furthest_sell_order])
                    self.iom.canceled_orders.append(furthest_sell_order)
                else:
                    # BUY base
                    log.info(f'PENDING_ORDER: trying to buy base to get enough liquidity to create new pt')

                    # check rate condition to limit the number of created actions based on consolidated profit
                    buy_actions, _, _ = self.get_actions_balance()
                    consolidated_actions_rate = consolidated_profit / (buy_actions + 1)
                    is_rate_ok = consolidated_actions_rate > self.P_CONSOLIDATED_VS_ACTIONS_COUNT_RATE
                    if is_rate_ok \
                            and self.strategy_manager.is_asset_liquidity_enough(asset=self.symbol.quote_asset(),
                                                                                new_pt_need=self.P_QUANTITY * cmp):
                        # prepare & place market order
                        new_qty = self.P_QUANTITY / 2.0
                        new_order = Order(symbol=self.symbol,
                                          order_id='NO_ID',
                                          k_side=k_binance.SIDE_BUY,
                                          price=cmp,
                                          amount=new_qty,
                                          status=OrderStatus.TO_BE_TRADED)
                        log.info(f'PENDING_ORDER: MARKET place order: {new_order}')
                        self.market_api_out.place_market_order(order=new_order)
                        # self.dbm.add_action(action=Action(
                        self.iom.actions.append(Action(
                            action_id='ACTION_TO_CREATE_NEW_PT',
                            side=k_binance.SIDE_BUY,
                            qty=new_qty,
                            price=cmp))

            return False, 0.0
        else:
            # reset negative tries counter
            self.base_negative_try_count = 0

        # check quote liquidity and try to get if not enough
        if not self.strategy_manager.is_asset_liquidity_enough(asset=self.symbol.quote_asset(),
                                                               new_pt_need=self.P_QUANTITY * cmp):
            self.quote_negative_try_count += 1
            if self.quote_negative_try_count > self.P_TRIES_TO_FORCE_GET_LIQUIDITY:
                # self.strategy_manager.try_to_get_liquidity(symbol=symbol, asset=symbol.quote_asset(), cmp=cmp)
                furthest_buy_order = self.iom.get_further_order(cmp=cmp,
                                                                k_side=k_binance.SIDE_BUY,
                                                                min_distance=self.P_MIN_DISTANCE_FOR_CANCELING_ORDER)
                canceled_buy_orders = [order for order in self.iom.canceled_orders
                                       if order.k_side == k_binance.SIDE_BUY]
                if furthest_buy_order and len(canceled_buy_orders) < self.P_CANCEL_MAX:
                    self.market_api_out.cancel_orders([furthest_buy_order])
                    self.iom.canceled_orders.append(furthest_buy_order)
                else:
                    # SELL base
                    log.info(f'PENDING_ORDER: trying to sell base to get enough liquidity to create new pt')

                    # check rate condition to limit the number of created actions based on consolidated profit
                    _, sell_actions, _ = self.get_actions_balance()
                    consolidated_actions_rate = consolidated_profit / (sell_actions + 1)
                    is_rate_ok = consolidated_actions_rate > self.P_CONSOLIDATED_VS_ACTIONS_COUNT_RATE
                    if is_rate_ok and self.strategy_manager.is_asset_liquidity_enough(asset=self.symbol.base_asset(),
                                                                                      new_pt_need=self.P_QUANTITY):
                        # prepare & place market order
                        new_qty = self.P_QUANTITY / 2.0
                        new_order = Order(symbol=self.symbol,
                                          order_id='NO_ID',
                                          k_side=k_binance.SIDE_SELL,
                                          price=cmp,
                                          amount=new_qty,
                                          status=OrderStatus.TO_BE_TRADED)
                        log.info(f'PENDING_ORDER: MARKET place order: {new_order}')
                        self.market_api_out.place_market_order(order=new_order)
                        # self.dbm.add_action(action=Action(
                        self.iom.actions.append(Action(
                            action_id='ACTION_TO_CREATE_NEW_PT',
                            side=k_binance.SIDE_SELL,
                            qty=new_qty,
                            price=cmp))

            return False, 0.0
        else:
            self.quote_negative_try_count = 0

        # check whether it is the last possible buy
        is_base_last, base_rel_dist = self.strategy_manager.is_last_possible(asset=self.symbol.base_asset(),
                                                                             new_pt_need=self.P_QUANTITY)
        is_quote_last, quote_rel_dist = self.strategy_manager.is_last_possible(asset=self.symbol.quote_asset(),
                                                                               new_pt_need=self.P_QUANTITY * cmp)

        # when both base and quote are in last zone, the one with less relative qty is chosen
        if is_base_last and is_quote_last:
            log.info(f'both base and quote are in last zone:')
            log.info(f'base_rel_dist: {base_rel_dist} quote_rel_dist: {quote_rel_dist}')
            # more relative distance means less liquidity
            if base_rel_dist > quote_rel_dist:
                # force buy
                shift = gap * 1.1 if gap != 0.0 else self.P_FORCED_SHIFT
                log.info(f'forced buy (base) with shift {shift}')
                return True, shift
            else:
                # force sell
                shift = gap * 1.1 * (-1) if gap != 0.0 else self.P_FORCED_SHIFT * (-1)
                log.info(f'forced sell (quote) with shift {shift}')
                return True, shift

        # when only one is in last zone
        if is_base_last:
            # force buy
            shift = gap * 1.1 if gap != 0.0 else self.P_FORCED_SHIFT
            log.info(f'forced buy (base) with shift {shift}')
            return True, shift
        if is_quote_last:
            # force sell
            shift = gap * 1.1 * (-1) if gap != 0.0 else self.P_FORCED_SHIFT * (-1)
            log.info(f'forced sell (quote) with shift {shift}')
            return True, shift

        # # 2. minimize span
        # all_orders = self.get_all_orders_for_symbol(symbol=symbol)
        # shift = self.strategy_manager.get_shift_to_minimize_span (all_orders=all_orders, cmp=cmp, gap=self.gap)
        # if shift != 0:
        #     return True, shift
        #
        # # 3. balance momentum
        # shift = self.strategy_manager.get_shift_to_balance_momentum(all_orders=all_orders, cmp=cmp, gap=self.gap)
        # return True, shift

        # Set shift based on predicted value
        if 0.0 not in cmp_pattern_short and 0.0 not in cmp_pattern_long:
            predicted_cmp = self.strategy_manager.get_tendency(cmp_pattern=cmp_pattern_short)
            shift_short = predicted_cmp - cmp
            print(f'cmp: {cmp} predicted value: {predicted_cmp} shift_short: {shift_short}')

            predicted_cmp = self.strategy_manager.get_tendency(cmp_pattern=cmp_pattern_long)
            shift_long = predicted_cmp - cmp
            print(f'cmp: {cmp} predicted value: {predicted_cmp} shift_long: {shift_long}')

            # set value as average from short and long
            short_weight = 0.5
            long_weight = 0.5
            shift = short_weight * shift_short + long_weight * shift_long
            print(f'applied shift: {shift}')

            return True, shift
        else:
            return True, 0.0

    def get_actions_balance(self) -> (int, int, float):
        buy_actions = [action for action in self.iom.actions if action.side == k_binance.SIDE_BUY]
        sell_actions = [action for action in self.iom.actions if action.side == k_binance.SIDE_SELL]
        buy_actions_count = len(buy_actions)
        sell_actions_count = len(sell_actions)

        actions_for_balance_count = min(buy_actions_count, sell_actions_count)

        actions_balance = 0.0
        for i in range(actions_for_balance_count):
            partial_balance = sell_actions[i].price * sell_actions[i].qty - buy_actions[i].price * buy_actions[i].qty
            actions_balance += partial_balance

        return buy_actions_count, sell_actions_count, actions_balance
