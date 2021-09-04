# dash_aux.py

from typing import List
import dash_bootstrap_components as dbc
from dash_html_components import Th, Tr, Td, Thead, Tbody, H6

import pandas as pd


def get_pending_html_table(df: pd.DataFrame) -> dbc.Table:
    column_names: List[Th] = []
    for col in df.columns:
        column_names.append(Th(col))
    table_header = [Thead(Tr(column_names))]

    row_values: List[Td] = []
    for index, row in df.iterrows():
        class_name: str
        if row['name'] == 'b1':
            class_name = 'buy-order'
        elif row['name'] == 's1':
            class_name = 'sell-order'
        else:
            class_name = 'cmp-order'

        row_values.append(
            Tr([
                Td(row['pt_id']),
                Td(row['price']),
                Td(row['total']),
                Td(row['amount']),
                Td(row['status'])
            ], className=class_name)
        )
    table_body = [Tbody(row_values)]

    return dbc.Table(table_body, bordered=False)
