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
                dbc.Row([
                    html.H1(id='title', children='Scorpius Session V1.0', className='app-title'),
                ]),
                # session KPI
                dbc.Row([
                    dbc.Col([
                        dbc.CardDeck([
                            dbc.Card(
                                [
                                    dbc.CardHeader('Session:'),
                                    dbc.CardBody([
                                        html.H6("Elapsed time [hours]", className="card-title"),
                                        html.H6(id='cycle-count', children='0', className='pt-info'),
                                        html.H1("Stop at price profit", className="card-title"),
                                        html.H6(id='stop-price-profit', children='0', className='pt-info'),
                                        html.H6("Stop at cmp profit", className="card-title"),
                                        html.H6(id='actual-profit', children='0', className='pt-info'),
                                        html.H6("Perfect Trades / Orders", className="card-title"),
                                        html.H6(id='trade-info', children='0', className='pt-info'),
                                    ]),
                                    # dbc.CardFooter('Footer')
                                ], color='dark', inverse=True
                            ),
                            dbc.Card(
                                [
                                    dbc.CardHeader('Global:'),
                                    dbc.CardBody([
                                        html.H6("global [h]", className="card-title"),
                                        html.H6(id='global-cycle-count', children='0', className='session-info'),
                                        html.H1("placed orders", className="card-title"),
                                        html.H6(id='global-placed-orders', children='0', className='session-info'),
                                        html.H6("global count", className="card-title"),
                                        html.H6(id='session-count', children='0', className='session-info'),
                                        html.H6("global profit", className="card-title"),
                                        html.H6(id='global-partial-profit', children='0', className='session-info')
                                    ]),
                                    # dbc.CardFooter('Footer')
                                ], color='dark', inverse=True
                            ),
                        ])
                    ], xs=12, sm=12, md=12, lg=12, xl=12),
                ]),
                html.Br(), html.Br(), html.Br(),
                # symbol & balance cards
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6(id='symbol', children='BTCEUR', className='symbol-card-title'),
                                html.H6(id='cmp-foo', children='-', className='locked'),
                                html.H6(id='cmp', children='', className="symbol-cmp"),
                            ])
                        ]),
                    ], xs=3, sm=3, md=3, lg=3, xl=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("EUR", className="liquidity-card-title"),
                                html.H6(id='eur-locked', children='0.00', className='locked'),
                                html.H6(id='eur-free', children='0.00', className='free')
                            ])
                        ], className='liquidity-card'),
                    ],  xs=3, sm=3, md=3, lg=3, xl=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("BTC", className="liquidity-card-title"),
                                html.H6(id='btc-locked', children='0.00', className='locked'),
                                html.H6(id='btc-free', children='0.00', className='free')
                            ])
                        ]),
                    ],  xs=3, sm=3, md=3, lg=3, xl=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("BNB", className="liquidity-card-title"),
                                html.H6(id='bnb-locked', children='0.00', className='locked'),
                                html.H6(id='bnb-free', children='0.00', className='free')
                            ])
                        ]),
                    ], xs=3, sm=3, md=3, lg=3, xl=3),
                ]),
                html.Br(), html.Br(),
                # orders table
                dbc.Row([
                    dbc.Col([
                        dbc.Table.from_dataframe(id='new-table', df=pd.DataFrame({'first': ['1', '2']})),
                    ], xs=12, sm=12, md=12, lg=12, xl=12),
                ]),
                html.Br(), html.Br(),
                # graphics
                # dbc.Row([
                #     dbc.Col([
                #         dcc.Graph(id='profit-line', figure={}, config={'displayModeBar': False})
                #     ], xs=12, sm=12, md=12, lg=12, xl=12)
                # ]),
                # dbc.Row([
                #     dbc.Col([
                #         dcc.Graph(id='cmp-line', figure={}, config={'displayModeBar': False})
                #     ], xs=12, sm=12, md=12, lg=12, xl=12)
                # ]),
                # buttons
                dbc.Row([
                    dbc.Col([
                        dbc.Button('New PT', id='button-new-pt', block=True, className='sc-button'),
                        dbc.Button('Start Session', id='button-start', block=True, className='sc-button'),
                    ]),
                    dbc.Col([
                        dbc.Button("Stop at cmp", id='button-stop-cmp', block=True, className='sc-button'),
                        dbc.Button("Stop at price", id='button-stop-price', block=True, className='sc-button'),
                    ]),
                    dbc.Col([
                        dbc.Button('+ 10.0 €', id='increase-cmp', block=True, className='sc-button'),
                        dbc.Button('- 10.0 €', id='decrease-cmp', block=True, className='sc-button'),
                    ]),
                    dbc.Col([
                        dbc.Button("Stop-cancel", id='button-stop-cancel', block=True, className='sc-button'),
                        dbc.Button('TBD', id='tbd-001', block=True, className='sc-button'),
                    ]),
                    dbc.Col([
                        dbc.Button('TBD', id='tbd-002', block=True, className='sc-button'),
                        dbc.Button('TBD', id='tbd-003', block=True, className='sc-button'),
                    ]),
                    dbc.Col([
                        dbc.Button("TBD", id='tbd-004', block=True, className='sc-button'),
                        dbc.Button('TBD', id='tbd-005', block=True, className='sc-button'),
                    ]),
                ]),
                # todo: needed to allow buttons functionality
                self.get_card(),
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
                        # html.H6(id='symbol', children='BTCEUR', className='symbol'),
                        # html.H6(id='cmp', children='', className="card-title-symbol-cmp"),
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

