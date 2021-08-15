# dash_aux.py

from typing import List
import dash_table
from dash_table.Format import Format, Scheme

import pandas as pd
import plotly.express as px
from plotly.graph_objects import Figure, Indicator


def get_balance_bar_chart(df: pd.DataFrame, asset: str, y_max: float) -> Figure:
    fig = px.bar(
        df,
        x='asset',
        y='amount',
        text='amount',
        color='type',
        barmode='stack',
        range_y=[0, y_max],
        # width=220,  # 220,
        # height=400,
        color_discrete_sequence=['green', 'red']
    )
    fig.update_layout(showlegend=False)  # , transition_duration=300)
    # fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_traces(marker_line_color='rgb(8,48,107)',
                      marker_line_width=1.5, opacity=0.6, textfont_size=16)
    if asset == 'eur':
        fig.update_traces(texttemplate='%{y:,.2f}')
    else:
        fig.update_traces(texttemplate='%{y:,.6f}')
    fig.update_layout(plot_bgcolor='#fff', margin_l=0, margin_r=0)
    return fig


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
            # {'id': 'split_count', 'name': 'split', 'type': 'numeric',
            #  'format': Format(
            #      precision=0,
            #  )},
            # {'id': 'concentration_count', 'name': 'concentration', 'type': 'numeric',
            #  'format': Format(
            #      precision=0,
            #  )}
        ],
        data=data,
        page_action='none',  # disable pagination (default is after 250 rows)
        style_table={'height': '800px', 'overflowY': 'auto'},  # , 'backgroundColor': K_BACKGROUND_COLOR},
        style_cell={'fontSize': 16, 'font-family': 'Arial',},  # 'background': 'black'},
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
                    'filter_query': '{k_side} = SELL && {status} = active',
                    'column_id': ['pt_id', 'name', 'price', 'amount', 'total', 'status'],
                },
                'color': 'red'
            },
            {
                'if': {
                    'filter_query': '{k_side} = BUY && {status} = active',
                    'column_id': ['pt_id', 'name', 'price', 'amount', 'total', 'status'],
                },
                'color': 'green'
            },
            {
                'if': {
                    'filter_query': '{k_side} = SELL && {status} = monitor',
                    'column_id': ['pt_id', 'name', 'price', 'amount', 'total', 'status'],
                },
                'color': 'Crimson'
            },
            {
                'if': {
                    'filter_query': '{k_side} = BUY && {status} = monitor',
                    'column_id': ['pt_id', 'name', 'price', 'amount', 'total', 'status'],
                },
                'color': 'LimeGreen'
            },
            {
                'if': {
                    'filter_query': '{status} = traded',
                    'column_id': ['pt_id', 'name', 'price', 'amount', 'total', 'status'],
                },
                'color': 'Black'
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


def get_profit_line_chart(df: pd.DataFrame, pls: List[float]) -> Figure:
    fig = px.line(df, x='rate', y='cmp', range_y=[-6, 1])
    fig.update_layout(
        margin=dict(t=0, r=0, l=0, b=20),
        # paper_bgcolor='rgba(0, 0, 0, 0)',
        # plot_bgcolor='rgba(0, 0, 0, 0)',
        yaxis=dict(title='profit line', showgrid=True, showticklabels=True),
        xaxis=dict(title=None, showgrid=False, showticklabels=True),
        height=230,
        # width=800,
    )
    return fig


def get_cmp_line_chart(df: pd.DataFrame, cmps: List[float]) -> Figure:
    fig = px.line(df, x='rate', y='cmp')  # , range_y=[38000.0, 42000.0])
    fig.update_layout(
        margin=dict(t=0, r=0, l=0, b=20),
        # paper_bgcolor='rgba(0, 0, 0, 0)',
        # plot_bgcolor='rgba(0, 0, 0, 0)',
        yaxis=dict(title='cmp line', showgrid=True, showticklabels=True),
        xaxis=dict(title=None, showgrid=False, showticklabels=True),
        height=230,
        # width=800,
    )
    fig.update_traces(line={'color': 'green'})
    return fig
