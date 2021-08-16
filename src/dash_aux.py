# dash_aux.py

from typing import List
# import dash_table
# from dash_table.Format import Format, Scheme
import dash_bootstrap_components as dbc
from dash_html_components import Th, Tr, Td, Thead, Tbody, H6

import pandas as pd
import plotly.express as px
from plotly.graph_objects import Figure  # Indicator


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
                Td(row['name']),
                Td(row['price']),
                Td(row['total']),
                Td(row['status'])
            ], className=class_name)
        )
    table_body = [Tbody(row_values)]

    return dbc.Table(table_header + table_body, bordered=False)


def get_balance_bar_card(asset: str, free: float, locked: float) -> dbc.Card:
    card = dbc.Card(
        [
            dbc.CardBody(
                [
                    dbc.CardHeader(asset, className='balance-card-header'),
                    H6(id='balance-free', children='X', className='balance-card-free'),
                    H6(id='balance-locked', children='X', className="balance-card-locked"),
                ], style={'text-align': 'center'}
            ),
        ],
        # color="dark",  # https://bootswatch.com/default/ for more card colors
        # inverse=True,  # change color of text (black or white)
        outline=False  # True = remove the block colors from the background and header
    )
    return card


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
    # fig.update_layout(plot_bgcolor='#fff', margin_l=0, margin_r=0)
    fig.update_layout(margin_l=0, margin_r=0)
    return fig



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
