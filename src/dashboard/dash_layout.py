# dash_layout.py

import pandas as pd
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_core_components as dcc

print('dash_layout.py')

# with lower values the dashboard does not refresh itself correctly
K_UPDATE_INTERVAL = 500  # milisecs


class DashLayout:
    def get_layout(self) -> html.Div:
        layout = html.Div(className='app-overall', children=[
            html.Div(children=[
                # app info & session data #1
                dbc.Row([
                    dbc.Col([
                        html.Img(src='/assets/btc_001.jpg', className='header-image'),
                        # html.Img(src='src/assets/btc_001.jpg', className='header-image'),
                        dbc.Row([
                            html.H1(id='current-time', children='', className='app-current-time'),
                            html.H1(id='neb', children='', className='neb'),
                            html.H1(id='qty', children='', className='qty'),
                            html.H1(id='target', children='', className='target'),
                            html.H1(id='max-negative-profit-allowed', children='', className='max-negative-profit-allowed'),
                            html.H1(id='title', children='Scorpius 1.0', className='app-title'),
                        ]),
                    ]),
                ]),
                # session KPI
                dbc.Row([
                    dbc.Col([
                        dbc.CardDeck([
                            dbc.Card(
                                [
                                    # dbc.CardHeader('Session', className='card-header-session'),
                                    dbc.CardBody([
                                        dbc.Row([
                                            dbc.Col([
                                                html.H6("Session", className="card-header-session"),
                                            ], align='center'),
                                            dbc.Col([
                                                html.H6(id='session-cycle-count', children='0', className='cycle-count'),
                                            ], align='center'),
                                        ]),
                                        html.Br(),
                                        dbc.Row([
                                            dbc.Col([
                                                html.H6('NEW ', className='session-info-subtitle-3'),
                                                html.H6(id='pt-new', children='0', className='pt-info')
                                            ]),
                                            dbc.Col([
                                                html.H6('BUY', className='session-info-subtitle-3'),
                                                html.H6(id='pt-buy', children='0', className='pt-info')
                                            ]),
                                            dbc.Col([
                                                html.H6('SELL', className='session-info-subtitle-3'),
                                                html.H6(id='pt-sell', children='0', className='pt-info')
                                            ]),
                                            dbc.Col([
                                                html.H6('END', className='session-info-subtitle-3'),
                                                html.H6(id='pt-end', children='0', className='pt-info')
                                            ]),
                                        ]),
                                        html.Br(),
                                        dbc.Row([
                                            dbc.Col([
                                                html.H6('SPAN ', className='session-info-subtitle-4'),
                                                html.H6(id='pt-span-buy', children='0', className='pt-info'),
                                                html.H6(id='pt-span-sell', children='0', className='pt-info')
                                            ]),
                                            dbc.Col([
                                                html.H6('DEPTH', className='session-info-subtitle-4'),
                                                html.H6(id='pt-depth-buy', children='0', className='pt-info'),
                                                html.H6(id='pt-depth-sell', children='0', className='pt-info')
                                            ]),
                                            dbc.Col([
                                                html.H6('MTM', className='session-info-subtitle-4'),
                                                html.H6(id='pt-mtm-buy', children='0', className='pt-info'),
                                                html.H6(id='pt-mtm-sell', children='0', className='pt-info')
                                            ]),
                                            dbc.Col([
                                                html.H6('TBD', className='session-info-subtitle-4'),
                                                html.H6(id='pt-btd-buy', children='0', className='pt-info'),
                                                html.H6(id='pt-btd-sell', children='0', className='pt-info')
                                            ]),
                                        ]),
                                        html.Br(),
                                        dbc.Row([
                                            dbc.Col([
                                                html.H6('Stop at price ', className='session-info-subtitle-2'),
                                                html.H6(id='stop-price-profit', children='0', className='pt-info')
                                            ]),
                                            dbc.Col([
                                                html.H6('Stop at cmp', className='session-info-subtitle-2'),
                                                html.H6(id='actual-profit', children='0', className='pt-info')
                                            ]),
                                        ]),
                                        html.Br(),
                                        # html.H6("Perfect Trades / Buy / Sell", className="card-title"),
                                        # html.H6(id='trade-info', children='0', className='pt-info'),
                                    ]),
                                    # dbc.CardFooter('Footer')
                                ], color='dark', inverse=True, className='scorpius-card'
                            ),
                            dbc.Card(
                                [
                                    # dbc.CardHeader('Session', className='card-header-session'),
                                    dbc.CardBody([
                                        dbc.Row([
                                            dbc.Col([
                                                html.H6("Global", className="card-header-session"),
                                            ], align='center'),
                                            dbc.Col([
                                                html.H6(id='global-cycle-count', children='0', className='cycle-count'),
                                            ], align='center'),
                                        ]),
                                        html.Br(),
                                        dbc.Row([
                                            dbc.Col([
                                                html.H6('PLAC ', className='global-info-subtitle-3'),
                                                html.H6(id='orders-placed', children='0', className='order-info')
                                            ]),
                                            dbc.Col([
                                                html.H6('PEND', className='global-info-subtitle-3'),
                                                html.H6(id='orders-pending', children='0', className='order-info')
                                            ]),
                                            dbc.Col([
                                                html.H6('BUY', className='global-info-subtitle-3'),
                                                html.H6(id='orders-pending-buy', children='0', className='order-info')
                                            ]),
                                            dbc.Col([
                                                html.H6('SELL', className='global-info-subtitle-3'),
                                                html.H6(id='orders-pending-sell', children='0', className='order-info')
                                            ]),
                                        ]),
                                        html.Br(),
                                        dbc.Row([
                                            dbc.Col([
                                                html.H6('CONS ', className='global-info-subtitle-4'),
                                                html.H6(id='consolidated-session', children='0', className='pt-info'),
                                                html.H6(id='consolidated-profit', children='0', className='pt-info')
                                            ]),
                                            dbc.Col([
                                                html.H6('EXPE', className='global-info-subtitle-4'),
                                                html.H6(id='expected-session', children='0', className='pt-info'),
                                                html.H6(id='expected-profit', children='0', className='pt-info')
                                            ]),
                                            dbc.Col([
                                                html.H6('CMP', className='global-info-subtitle-4'),
                                                html.H6(id='expected-session-at-cmp', children='0', className='pt-info'),
                                                html.H6(id='expected-profit-at-cmp', children='0', className='pt-info')
                                            ]),
                                            dbc.Col([
                                                html.H6('TBD', className='global-info-subtitle-4'),
                                                html.H6(id='xpt-btd-buy', children='0', className='pt-info'),
                                                html.H6(id='xpt-btd-sell', children='0', className='pt-info')
                                            ]),
                                        ]),
                                        html.Br(),
                                        dbc.Row([
                                            dbc.Col([
                                                html.H6('Stop at price ', className='global-info-subtitle-2'),
                                                html.H6(id='xstop-price-profit', children='0', className='pt-info')
                                            ]),
                                            dbc.Col([
                                                html.H6('Stop at cmp', className='global-info-subtitle-2'),
                                                html.H6(id='xactual-profit', children='0', className='pt-info')
                                            ]),
                                        ]),
                                        html.Br(),
                                        html.H6("Perfect Trades / Buy / Sell", className="card-title"),
                                        html.H6(id='xtrade-info', children='0', className='pt-info'),
                                    ]),
                                    # dbc.CardFooter('Footer')
                                ], color='dark', inverse=True, className='scorpius-card'
                            ),
                        ])
                    ], xs=12, sm=12, md=12, lg=12, xl=12),
                ]),
                # html.Br(), html.Br(), html.Br(),
                # session data #2
                dbc.Row([
                    dbc.Col([
                        dbc.Row([
                            html.H1(id='cycles-to-new-pt', children='XXX', className='cycles-to-new-pt'),
                            html.H1(id='accounts-info', children='XXX', className='accounts-info'),
                        ]),
                    ]),
                ]),
                # symbol & balance cards
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6(id='symbol', children='', className='symbol-card-title'),
                                html.H6(id='cmp-max', children='45,000.00', className='cmp-max'),
                                html.H6(id='cmp', children='', className="symbol-cmp"),
                                html.H6(id='cmp-min', children='38,000.00', className='cmp-min'),
                            ])
                        ], className='symbol-card'),
                    ], xs=3, sm=3, md=3, lg=3, xl=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6(id='base-asset', className="liquidity-card-title"),
                                html.H6(id='base-asset-locked', children='0.00', className='locked'),
                                html.H6(id='base-asset-alive', children='0.00', className='locked'),
                                html.H6(id='base-asset-free', children='0.00', className='free')
                            ])
                        ], className='liquidity-card'),
                    ],  xs=3, sm=3, md=3, lg=3, xl=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6(id='quote-asset', className="liquidity-card-title"),
                                html.H6(id='quote-asset-locked', children='0.00', className='locked'),
                                html.H6(id='quote-asset-alive', children='0.00', className='locked'),
                                html.H6(id='quote-asset-free', children='0.00', className='free')
                            ])
                        ], className='liquidity-card'),
                    ],  xs=3, sm=3, md=3, lg=3, xl=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("BNB", className="liquidity-card-title"),
                                html.H6(id='bnb-locked', children='0.00', className='locked'),
                                html.H6(id='bnb-alive', children='0.00', className='locked'),
                                html.H6(id='bnb-free', children='0.00', className='free')
                            ])
                        ], className='liquidity-card'),
                    ], xs=3, sm=3, md=3, lg=3, xl=3),
                ]),
                html.Br(), html.Br(),
                dbc.Row([
                    dbc.Col([
                        dbc.Button('BTCEUR', id='button-btceur', disabled=False, color='light', block=True,
                                   className='sc-button'),
                        html.Br(),
                        dbc.Button("Stop at cmp", id='button-stop-cmp', color='danger', block=True,
                                   className='sc-button'),
                    ]),
                    dbc.Col([
                        dbc.Button('BNBEUR', id='button-bnbeur', color='light', block=True, className='sc-button'),
                        html.Br(),
                        dbc.Button("Stop-cancel", id='button-stop-cancel', color='danger', block=True,
                                   className='sc-button'),
                    ]),
                    dbc.Col([
                        dbc.Button('TBD-01', id='button-tbd-01', disabled=False, color='light', block=True,
                                   className='sc-button'),
                        html.Br(),
                        dbc.Button("Stop at price", id='button-stop-price', color='danger', block=True,
                                   className='sc-button'),
                    ]),
                    dbc.Col([
                        dbc.Button('TBD-02', id='button-tbd-02', disabled=False, color='light', block=True,
                                   className='sc-button'),
                        html.Br(),
                        dbc.Button('Stop session', id='button-stop-global-session', color='success', block=True,
                                   className='sc-button'),
                    ]),
                ]),

                html.Br(),
                # orders table
                dbc.Row([
                    dbc.Col([
                        dbc.Table.from_dataframe(id='new-table', df=pd.DataFrame({'first': ['1', '2']})),
                    ], xs=12, sm=12, md=12, lg=12, xl=12),
                ]),
                html.Br(), html.Br(), html.Br(),
                # buttons
                dbc.Row([
                    dbc.Col([
                        dbc.Button('TBD', id='tbd-010', disabled=False, color='primary', block=True, className='sc-button'),
                    ]),
                    dbc.Col([
                        dbc.Button('New PT', id='button-new-pt', color='warning', block=True,
                                   className='sc-button'),
                    ]),
                    dbc.Col([
                        dbc.Button('+ 10.0 €', id='button-increase-cmp', disabled=False, color='warning', block=True,
                                   className='sc-button'),
                    ]),
                    dbc.Col([
                        dbc.Button('- 10.0 €', id='button-decrease-cmp', disabled=False, color='warning', block=True,
                                   className='sc-button'),
                    ]),
                ]),
                # todo: needed to allow buttons functionality
                html.Br(), html.Br(),
                dbc.Row([
                    dbc.Col([
                        self.get_card()
                    ], xs=12, sm=12, md=12, lg=12, xl=12),
                ]),
                dcc.Interval(id='update', n_intervals=0, interval=K_UPDATE_INTERVAL)
            ],)
        ])
        return layout

    def get_card(self) -> dbc.Card:
        card = dbc.Card(
            [
                dbc.CardBody(
                    [
                        html.H6(id='button-btceur-hidden-msg', children=''),
                        html.H6(id='button-bnbeur-hidden-msg', children=''),
                    ], style={'text-align': 'center'}
                ),
            ],
            outline=False,  # True = remove the block colors from the background and header
            style={'opacity': 0}
        )
        return card
