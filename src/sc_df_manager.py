# sc_df_manager.py

import pandas as pd

from sc_session import Session
from sc_order import OrderStatus
from sc_perfect_trade import PerfectTradeStatus

print('sc_df_manager.py')


class DataframeManager:
    def __init__(self):
        self.session = Session()
        print('Session init')

    def get_all_orders_df(self) -> pd.DataFrame:
        # get list with all orders:
        all_orders = self.session.ptm.get_orders_by_request(
            orders_status=[OrderStatus.MONITOR, OrderStatus.ACTIVE],
            pt_status=[PerfectTradeStatus.NEW, PerfectTradeStatus.BUY_TRADED,
                       PerfectTradeStatus.SELL_TRADED, PerfectTradeStatus.COMPLETED])
        # create dataframe
        df = pd.DataFrame([order.to_dict_for_df() for order in all_orders])
        return df

    def get_all_orders_df_with_cmp(self) -> pd.DataFrame:
        df = self.get_all_orders_df()
        # create cmp order-like and add to dataframe
        cmp_order = dict(pt_id='CMP', status='cmp', price=self.session.get_last_cmp())
        df1 = df.append(other=cmp_order, ignore_index=True)
        return df1
