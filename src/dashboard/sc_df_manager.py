# sc_df_manager.py

import pandas as pd
from typing import Dict
from binance import enums as k_binance

from sc_order import OrderStatus
from sc_perfect_trade import PerfectTradeStatus
from sc_session_manager import SessionManager


# SYMBOL = 'BTCEUR'


class DataframeManager:
    def __init__(self):
        # init session manager
        self.sm = SessionManager()

        # get symbols
        self.available_symbols = self.sm.symbols
        if len(self.available_symbols) == 0:
            raise Exception('no symbols to show')

        # set the active symbol in dashboard
        self.dashboard_active_symbol = self.available_symbols[0]

        print('data frame manager')

    def set_dashboard_active_symbol(self, symbol_name: str) -> None:
        # set the passed symbol as active if exist, otherwise do nothing
        position_in_list = 0

        # get list of available symbol names
        names = [symbol.name for symbol in self.available_symbols]

        # get position in list for passed symbol name
        if symbol_name in names:
            position_in_list = names.index(symbol_name)

        # set the passed symbol as the one active in dashboard
        self.dashboard_active_symbol = self.available_symbols[position_in_list]

    def get_all_orders_df(self) -> pd.DataFrame:
        # get list with all orders:
        symbol_name = self.dashboard_active_symbol.name
        if self.sm.active_sessions[symbol_name]:
            all_orders = self.sm.active_sessions[symbol_name].ptm.get_orders_by_request(
                orders_status=[OrderStatus.MONITOR, OrderStatus.ACTIVE],
                pt_status=[PerfectTradeStatus.NEW, PerfectTradeStatus.BUY_TRADED,
                           PerfectTradeStatus.SELL_TRADED, PerfectTradeStatus.COMPLETED])
            # create dataframe
            df = pd.DataFrame([order.to_dict_for_df() for order in all_orders])
            return df
        else:
            return pd.DataFrame(columns=['foo'])

    def get_all_orders_df_with_cmp(self) -> pd.DataFrame:
        df = self.get_all_orders_df()
        symbol_name = self.dashboard_active_symbol.name
        price = self.sm.active_sessions[symbol_name].cmp

        # create cmp order-like and add to dataframe
        cmp_order = dict(
            pt_id='',
            status='cmp',
            price=price,
            total=0.0,
            name='',
            amount=''
        )
        df1 = df.append(other=cmp_order, ignore_index=True)
        return df1

    def get_span_depth_momentum(self) -> Dict[str, int]:
        symbol_name = self.dashboard_active_symbol.name
        orders = self.sm.active_sessions[symbol_name].ptm.get_orders_by_request(
            orders_status=[OrderStatus.MONITOR, OrderStatus.ACTIVE],
            pt_status=[PerfectTradeStatus.NEW, PerfectTradeStatus.BUY_TRADED, PerfectTradeStatus.SELL_TRADED])
        buy_orders_values = [order.price for order in orders if order.k_side == k_binance.SIDE_BUY]
        sell_orders_values = [order.price for order in orders if order.k_side == k_binance.SIDE_SELL]
        cmp = self.sm.active_sessions[symbol_name].cmp
        # min_buy = int(min(buy_orders_values)) if len(buy_orders_values) > 0 else 0
        # max_buy = int(max(buy_orders_values)) if len(buy_orders_values) > 0 else 0

        return dict(
            buy_span=int(cmp - min(buy_orders_values)) if len(buy_orders_values) > 0 else 0,
            buy_depth=int(cmp - max(buy_orders_values)) if len(buy_orders_values) > 0 else 0,
            sell_span=int(max(sell_orders_values) - cmp) if len(sell_orders_values) > 0 else 0,
            sell_depth=int(min(sell_orders_values) - cmp) if len(sell_orders_values) > 0 else 0,
        )
