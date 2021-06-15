# sc_df_manager.py

import pandas as pd

from sc_session import Session, ClientMode

print('sc_df_manager.py')
# create session
# session = Session(client_mode=ClientMode.CLIENT_MODE_SIMULATOR)


class DataframeManager:
    def __init__(self):
        self.session = Session(client_mode=ClientMode.CLIENT_MODE_SIMULATOR)

    def get_all_orders_df(self) -> pd.DataFrame:
        # get list with all orders: pending (monitor + placed) & traded (completed + pending_pt_id)
        all_orders = self.session.pob.get_pending_orders() + self.session.tob.get_all_traded_orders()
        # create dataframe
        # df = pd.DataFrame([order.__dict__ for order in all_orders])
        df = pd.DataFrame([order.to_dict_for_df() for order in all_orders])
        # delete status column because it returns a tuple and raises an error in the dash callback
        # there is the property status_name that substitutes status
        df1 = df.drop(columns='status', axis=1)
        return df1

    def get_all_orders_df_with_cmp(self) -> pd.DataFrame:
        df = self.get_all_orders_df()
        # create cmp order-like and add to dataframe
        cmp_order = dict(pt_id='CMP', status='cmp', price=self.session.get_last_cmp())
        df1 = df.append(other=cmp_order, ignore_index=True)
        return df1
