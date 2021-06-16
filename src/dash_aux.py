# dash_aux.py

from typing import List
import dash_table
from dash_table.Format import Format, Scheme


def get_pending_datatable(data: List[dict]):
    datatable = dash_table.DataTable(
        id='pending-table',  # used in the css file
        columns=[
            {'id': 'pt_id', 'name': 'pt id', 'type': 'text'},
            {'id': 'name', 'name': 'name', 'type': 'text'},
            {'id': 'price', 'name': 'price', 'type': 'numeric',
             'format': Format(
                 scheme=Scheme.fixed,
                 precision=2,
                 group=True,
             )},
            {'id': 'amount', 'name': 'amount', 'type': 'numeric',
             'format': Format(
                 precision=6,
                 scheme=Scheme.fixed)},
            {'id': 'total', 'name': 'total', 'type': 'numeric',
             'format': Format(
                 precision=2,
                 scheme=Scheme.fixed,
                 group=True
             )},
            {'id': 'status', 'name': 'status', 'type': 'text',
             # 'format': Format(
             #     precision=0,
             # )
             },
            {'id': 'split_count', 'name': 'split', 'type': 'numeric',
             'format': Format(
                 precision=0,
             )},
            {'id': 'concentration_count', 'name': 'concentration', 'type': 'numeric',
             'format': Format(
                 precision=0,
             )}
        ],
        data=data,
        page_action='none',  # disable pagination (default is after 250 rows)
        style_table={'height': '800px', 'overflowY': 'auto'},  # , 'backgroundColor': K_BACKGROUND_COLOR},
        style_cell={'fontSize': 16, 'font-family': 'Arial', 'background': 'black'},
        # set table height and vertical scroll
        style_data={
            'width': '90px',
            'maxWidth': '90px',
            'minWidth': '50px',
            'border': 'none'
        },
        css=[{"selector": ".show-hide", "rule": "display: none"}],  # hide toggle button on top of the table
        style_header={'border': 'none', 'textAlign': 'center', 'fontSize': 16, 'fontWeight': 'bold'},
        fixed_rows={'headers': True},
        hidden_columns=['k_side'],
        style_cell_conditional=[
            {
                'if': {'column_id': ['pt_id', 'name']},
                'textAlign': 'center'
            }
        ],
        style_data_conditional=[
            {
                'if': {
                    'filter_query': '{k_side} = SELL && {status} = placed',
                    'column_id': ['pt_id', 'name', 'price', 'amount', 'total', 'status'],
                },
                'color': 'red'
            },
            {
                'if': {
                    'filter_query': '{k_side} = BUY && {status} = placed',
                    'column_id': ['pt_id', 'name', 'price', 'amount', 'total', 'status'],
                },
                'color': 'green'
            },
            {
                'if': {
                    'filter_query': '{k_side} = SELL && {status} = monitor',
                    'column_id': ['pt_id', 'name', 'price', 'amount', 'total', 'status'],
                },
                'color': 'pink'
            },
            {
                'if': {
                    'filter_query': '{k_side} = BUY && {status} = monitor',
                    'column_id': ['pt_id', 'name', 'price', 'amount', 'total', 'status'],
                },
                'color': 'Aquamarine'
            },
            {
                'if': {
                    'filter_query': '{status} = cmp',
                    'column_id': ['pt_id', 'name', 'price', 'name', 'pt_id', 'total', 'status'],
                },
                'color': 'orange'
            }
        ],
        sort_action='native'
    )
    return datatable
