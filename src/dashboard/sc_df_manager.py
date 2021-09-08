# sc_df_manager.py

import pandas as pd
from typing import Dict, List
from binance import enums as k_binance

from sc_order import OrderStatus, Order
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
        self.symbol_names = [symbol.name for symbol in self.available_symbols]

        # set the active symbol in dashboard
        self.dashboard_active_symbol = self.available_symbols[0]

        print('data frame manager')

    def get_next_symbol(self, symbol_name: str) -> str:
        symbols_count = len(self.symbol_names)
        if symbols_count > 0 and symbol_name in self.symbol_names:
            index = self.symbol_names.index(symbol_name)
            return self.symbol_names[0] if index == symbols_count-1 else self.symbol_names[index + 1]
        else:
            raise Exception(f'symbol {symbol_name} not defined')

    def set_dashboard_active_symbol(self, symbol_name: str) -> None:
        # set the passed symbol as active if exist, otherwise do nothing
        position_in_list = 0

        # get list of available symbol names
        # names = [symbol.name for symbol in self.available_symbols]

        # get position in list for passed symbol name
        if symbol_name in self.symbol_names:
            position_in_list = self.symbol_names.index(symbol_name)

        # set the passed symbol as the one active in dashboard
        self.dashboard_active_symbol = self.available_symbols[position_in_list]

    def get_session_orders(self) -> List[Order]:
        symbol_name = self.dashboard_active_symbol.name
        session_orders = self.sm.active_sessions[symbol_name].ptm.get_orders_by_request(
            orders_status=[OrderStatus.MONITOR, OrderStatus.ACTIVE],
            pt_status=[PerfectTradeStatus.NEW, PerfectTradeStatus.BUY_TRADED,
                       PerfectTradeStatus.SELL_TRADED, PerfectTradeStatus.COMPLETED])
        return session_orders

    def get_isolated_orders(self) -> List[Order]:
        symbol_name = self.dashboard_active_symbol.name
        isolated_orders = [order for order in self.sm.iom.isolated_orders if order.symbol.name == symbol_name]
        return isolated_orders

    def get_all_orders(self) -> List[Order]:
        return self.get_session_orders() + self.get_isolated_orders()

    def get_all_orders_df(self) -> pd.DataFrame:
        # get list with all orders:
        symbol_name = self.dashboard_active_symbol.name
        if self.sm.active_sessions[symbol_name]:
            all_orders = self.get_all_orders()

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

    # def get_span_depth_momentum(self) -> Dict[str, float]:
    #     symbol_name = self.dashboard_active_symbol.name
    #     return dict(
    #         buy_span=self.sm.active_sessions[symbol_name].get_gap_span(side=k_binance.SIDE_BUY),
    #         sell_span=self.sm.active_sessions[symbol_name].get_gap_span(side=k_binance.SIDE_SELL),
    #         buy_depth=self.sm.active_sessions[symbol_name].get_gap_depth(side=k_binance.SIDE_BUY),
    #         sell_depth=self.sm.active_sessions[symbol_name].get_gap_depth(side=k_binance.SIDE_SELL),
    #         buy_momentum=self.sm.active_sessions[symbol_name].get_gap_momentum(side=k_binance.SIDE_BUY),
    #         sell_momentum=self.sm.active_sessions[symbol_name].get_gap_momentum(side=k_binance.SIDE_SELL)
    #     )
