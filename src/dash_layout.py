# dash_layout.py

import pandas as pd
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import plotly.express as px

import dash_aux as daux

print('dash_layout.py')

# with lower values the dashboard does not refresh itself correctly
K_UPDATE_INTERVAL = 1000  # milisecs


class DashLayout:
    def get_layout(self) -> html.Div:
        layout = html.Div(className='app-overall', children=[
            html.Div(children=[
                html.H1(id='title', children='Scorpius Session V1.0'),
                dbc.Row([
                    dbc.Col([
                        self.get_card(),
                        dbc.Button('New PT', id='button-new-pt', color='info', block=True, className='sc-button'),
                        dbc.Button('Start Session', id='button-start', color='success', block=True, className='sc-button'),
                        dbc.Button("Stop at cmp", id='button-stop-cmp', color="warning", block=True, className='sc-button'),
                        dbc.Button("Stop at price", id='button-stop-price', color="danger", block=True, className='sc-button'),
                        dbc.Button("Stop-cancel", id='button-stop-cancel', color="dark", block=True, className='sc-button'),
                        dbc.Button('+ 10.0 €', id='increase-cmp', color='light', block=True, className='sc-button'),
                        dbc.Button('- 10.0 €', id='decrease-cmp', color='light', block=True, className='sc-button'),
                    ], xs=2, sm=2, md=2, lg=2, xl=2),  # width=1),
                    dbc.Col([
                        dbc.Row([
                            dbc.Col([
                                dcc.Graph(id='btc-balance-chart', className='balance-chart'),
                            ]),  # xs=2, sm=2, md=2, lg=2, xl=2),
                            dbc.Col([
                                dcc.Graph(id='eur-balance-chart', className='balance-chart'),
                            ]),  # , xs=2, sm=2, md=2, lg=2, xl=2),
                            dbc.Col([
                                dcc.Graph(id='bnb-balance-chart', className='balance-chart'),
                            ]),  # , xs=2, sm=2, md=2, lg=2, xl=2),
                        ]),
                        dbc.Row([
                            dbc.Col([
                                daux.get_pending_datatable(data=[{}])
                            ])  #, xs=6, sm=6, md=6, lg=6, xl=6)
                        ])
                    ], xs=6, sm=6, md=6, lg=6, xl=6),
                    dbc.Col([
                        dbc.Card(
                            [
                                dbc.CardBody([
                                    html.H6("time [h]", className="card-title"),
                                    html.H6(id='cycle-count', children='0', className='pt-info')
                                ])
                            ]
                        ),
                        dbc.Card(
                            [
                                dbc.CardBody([
                                    html.H6("stop at cmp", className="card-title"),
                                    html.H6(id='actual-profit', children='0', className='pt-info')
                                ])
                            ]
                        ),
                        dbc.Card(
                            [
                                dbc.CardBody([
                                    html.H1("stop at price", className="card-title"),
                                    html.H6(id='stop-price-profit', children='0', className='pt-info')
                                ])
                            ]
                        ),
                        dbc.Card(
                            [
                                dbc.CardBody([
                                    html.H6("PT / orders", className="card-title"),
                                    html.H6(id='trade-info', children='0', className='pt-info')
                                ])
                            ]
                        ),
                    ], xs=2, sm=2, md=2, lg=2, xl=2),
                    dbc.Col([
                        dbc.Card(
                            [
                                dbc.CardBody([
                                    html.H6("global [h]", className="card-title"),
                                    html.H6(id='global-cycle-count', children='0', className='pt-info')
                                ])
                            ]
                        ),
                        dbc.Card(
                            [
                                dbc.CardBody([
                                    html.H6("global count", className="card-title"),
                                    html.H6(id='session-count', children='0', className='session-count-info')
                                ])
                            ]
                        ),
                        dbc.Card(
                            [
                                dbc.CardBody([
                                    html.H1("placed orders", className="card-title"),
                                    html.H6(id='global-placed-orders', children='0', className='placed-orders-info')
                                ])
                            ]
                        ),
                        dbc.Card(
                            [
                                dbc.CardBody([
                                    html.H6("global profit", className="card-title"),
                                    html.H6(id='global-partial-profit', children='0', className='global-profit')
                                ])
                            ]
                        ),
                    ], xs=2, sm=2, md=2, lg=2, xl=2),
                ]),
                dbc.Row([
                    dbc.Col([
                        dcc.Graph(id='profit-line', figure={}, config={'displayModeBar': False})
                    ], xs=12, sm=12, md=12, lg=12, xl=12)
                ]),
                dbc.Row([
                    dbc.Col([
                        dcc.Graph(id='cmp-line', figure={}, config={'displayModeBar': False})
                    ], xs=12, sm=12, md=12, lg=12, xl=12)
                ]),

                dcc.Interval(id='update', n_intervals=0, interval=K_UPDATE_INTERVAL)
            ],)
        ])
        return layout

    def get_card(self) -> dbc.Card:
        card = dbc.Card(
            [
                dbc.CardImg(src="assets/bitcoin.png", top=True, bottom=False),
                dbc.CardBody(
                    [
                        html.H6(id='symbol', children='BTCEUR', className='symbol'),
                        html.H6(id='cmp', children='', className="card-title-symbol-cmp"),
                        html.H6(id='msg', children=''),
                        html.H6(id='stop-price', children=''),
                        html.H6(id='stop-cancel', children=''),
                        html.H6(id='msg-2', children=''),
                        html.H6(id='msg-start', children=''),
                        html.H6(id='msg-increase-cmp', children=''),
                        html.H6(id='msg-decrease-cmp', children='')
                    ], style={'text-align': 'center'}
                ),
            ],
            # color="dark",  # https://bootswatch.com/default/ for more card colors
            # inverse=True,  # change color of text (black or white)
            outline=False,  # True = remove the block colors from the background and header
        )

        return card

