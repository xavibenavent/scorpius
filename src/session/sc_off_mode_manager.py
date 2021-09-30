# sc_off_mode_manager.py

from typing import Optional
import logging

from managers.sc_isolated_manager import IsolatedOrdersManager
from managers.sc_strategy_manager import StrategyManager
from session.sc_helpers import Helpers
from session.sc_pt_manager import PTManager
from basics.sc_symbol import Symbol
from basics.sc_order import Order, OrderStatus
from market.sc_market_api_out import MarketAPIOut

log = logging.getLogger('log')


class OffModeManager:
    def __init__(self,
                 symbol: Symbol,
                 iom: IsolatedOrdersManager,
                 strategy_manager: StrategyManager,
                 helpers: Helpers,
                 ptm: PTManager,
                 market_api_out: MarketAPIOut,
                 config: dict):
        self.symbol = symbol
        self.iom = iom
        self.strategy_manager = strategy_manager
        self.helpers = helpers
        self.ptm = ptm
        self.market_api_out = market_api_out

        self.P_LOSS_FOR_ACTIVATION_FLAG = float(config['loss_for_activation_flag'])

        self.monitor_order: Optional[Order] = None

    def check_to_update_activation_flag(self, cmp: float) -> bool:
        loss_at_cmp = self.iom.get_expected_profit_at_cmp(cmp=cmp, symbol_name=self.symbol.name)
        return False if loss_at_cmp < (-1) * self.P_LOSS_FOR_ACTIVATION_FLAG else True

    def check_monitor_order(self, cmp: float):
        if self.monitor_order and self.monitor_order.get_distance(cmp=cmp) > 2000.0:
            self.market_api_out.place_market_order(order=self.monitor_order)
            log.info(f'******** PLACED AT LOSS ORDER {self.monitor_order} ********')
            self.monitor_order = None
