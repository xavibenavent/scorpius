# sc_df_manager.py

import pandas as pd

from sc_order import OrderStatus
from sc_perfect_trade import PerfectTradeStatus
from sc_session_manager import SessionManager


SYMBOL = 'BTCEUR'


class DataframeManager:
    def __init__(self):
        self.sm = SessionManager()
        # get symbols
        self.available_symbols = self.sm.symbols
        if len(self.available_symbols) == 0:
            raise Exception('no symbols to show')
        # set the active symbol in dashboard
        self.dashboard_active_symbol = self.available_symbols[0]
        print('data frame manager')

    def get_all_orders_df(self) -> pd.DataFrame:
        # get list with all orders:
        if self.sm.active_sessions[SYMBOL]:
            all_orders = self.sm.active_sessions[SYMBOL].ptm.get_orders_by_request(
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
        # create cmp order-like and add to dataframe
        cmp_order = dict(
            pt_id='',
            status='cmp',
            price=self.sm.active_sessions[SYMBOL].cmps[-1] if self.sm.active_sessions[SYMBOL].cmps else 0,
            total=0.0,
            name='',
            amount=''
        )
        df1 = df.append(other=cmp_order, ignore_index=True)
        return df1
