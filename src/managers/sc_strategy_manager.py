# sc_strategy_manager.py

import numpy as np
from sklearn.linear_model import LinearRegression

import logging
from typing import Callable, List
from basics.sc_asset import Asset
from basics.sc_symbol import Symbol
from basics.sc_order import Order
from market.sc_market_api_out import MarketAPIOut
from managers.sc_isolated_manager import IsolatedOrdersManager
from session.sc_helpers import Helpers
from managers.sc_client_manager import ConfigManager

log = logging.getLogger('log')

BNB_BUFFER = 1.0


class StrategyManager:
    def __init__(self,
                 quantity: float,
                 market_api_out: MarketAPIOut,
                 isolated_orders_manager: IsolatedOrdersManager,
                 helpers: Helpers,
                 get_liquidity_needed_callback: Callable[[Asset], float],
                 ):
        self.quantity = quantity
        self.market_api_out = market_api_out
        self.iom = isolated_orders_manager
        self.helpers = helpers
        self._get_liquidity_needed_callback = get_liquidity_needed_callback
        self.config_manager = ConfigManager(config_file='config_new.ini')

    @staticmethod
    def get_tendency(cmp_pattern: List[float]) -> float:
        x_pattern = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        X = np.array(x_pattern).reshape(-1, 1)
        y = np.array(cmp_pattern).reshape(-1, 1)
        to_predict_x = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
        to_predict_x = np.array(to_predict_x).reshape(-1, 1)

        # predict
        regsr = LinearRegression()
        regsr.fit(X, y)
        predicted_y = regsr.predict(to_predict_x)

        slope = regsr.coef_

        last_y = cmp_pattern[-1]
        new_y = predicted_y[0, -1]
        percent_step = (new_y - last_y) / last_y * 100.0

        # return slope[0, 0] * 100.0
        return new_y

    def get_shift_to_minimize_span(self, all_orders: List[Order], cmp: float, gap: float) -> float:
        # return shift only if one of both sides is 0.0, otherwise return 0.0
        buy_span, sell_span = self.helpers.get_span_from_list(orders=all_orders, cmp=cmp)

        factor = - 0.8  # todo: convert to parameter in config.ini
        shift = gap * factor

        if buy_span == 0.0 and sell_span > 0:
            return shift
        if sell_span == 0.0 and buy_span > 0:
            return - shift
        return 0.0

    def get_shift_to_balance_momentum(self, all_orders: List[Order], cmp: float, gap: float) -> float:
        buy_mtm, sell_mtm = self.helpers.get_momentum_from_list(orders=all_orders, cmp=cmp)

        mtm_factor = 0.8  # todo: convert to parameter in config.ini
        shift = gap * mtm_factor

        return shift if buy_mtm > sell_mtm else - shift

    @staticmethod
    def get_new_inactivity_cycles(buy_count: int, sell_count: int, ref_cycles: int) -> int:
        diff = abs(buy_count - sell_count)
        return ref_cycles * (diff+1) if diff > 0 else ref_cycles

    def is_asset_liquidity_enough(self, asset: Asset, new_pt_need: float) -> bool:
        # special buffer for BNB
        if asset.name() == 'BNB':
            new_pt_need += BNB_BUFFER
        liquidity_needed = self._get_liquidity_needed_callback(asset) + new_pt_need
        liquidity_available = self.market_api_out.get_asset_liquidity(asset_name=asset.name())  # free
        return True if liquidity_available > liquidity_needed else False  # need for quote

    def is_symbol_liquidity_enough(self, cmp: float, symbol: Symbol) -> (bool, bool):
        is_base_enough = self.is_asset_liquidity_enough(asset=symbol.base_asset(), new_pt_need=self.quantity)
        is_quote_enough = self.is_asset_liquidity_enough(asset=symbol.quote_asset(), new_pt_need=self.quantity * cmp)
        return is_base_enough, is_quote_enough

    def try_to_get_liquidity(self, symbol: Symbol, asset: Asset, cmp: float):
        # return the order to trade to get liquidity for the asset or None
        # this is a LIMIT order placed in a previous session that will be traded at MARKET price with losses
        order = self.iom.try_to_get_asset_liquidity(
            asset=asset,
            cmp=cmp,
            max_loss=self.config_manager.get_max_allowed_loss_for_liquidity(symbol_name=symbol.name))

        if order:
            # place at MARKET price
            log.info(f'order to place at MARKET price with loss: {order}')

            # cancel in Binance the previously placed order
            self.market_api_out.cancel_orders([order])
            log.info(f'order canceled in Binance from previous sessions: {order}')

            # self.logbook.append(f'place isolated order at cmp to get liquidity: {order}')
            self.helpers.place_market_order(order=order)
            log.info(f'order placed at Market price with loss: {order}')


