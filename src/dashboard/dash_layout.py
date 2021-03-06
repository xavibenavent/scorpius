# dash_layout.py

import pandas as pd
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_core_components as dcc

print('dash_layout.py')

# with lower values the dashboard does not refresh itself correctly
K_UPDATE_INTERVAL = 2000.0  # milisecs


class DashLayout:
    @staticmethod
    def get_layout() -> html.Div:
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
                            html.H1(id='max-negative-profit-allowed', children='',
                                    className='max-negative-profit-allowed'),
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
                                                html.H6(id='session-count', className="session-count")
                                            ], align='center'),
                                            dbc.Col([
                                                html.H6(id='session-cycle-count', children='0',
                                                        className='session-cycle-count'),
                                            ], align='center'),
                                        ]),
                                        html.Br(),
                                        dbc.Row([
                                            dbc.Col([
                                                html.H6('NEW ', className='session-info-subtitle'),
                                                html.H6(id='pt-new', children='0', className='pt-info-1')
                                            ]),
                                            dbc.Col([
                                                html.H6('BUY', className='session-info-subtitle'),
                                                html.H6(id='pt-buy', children='0', className='pt-info-1')
                                            ]),
                                            dbc.Col([
                                                html.H6('SELL', className='session-info-subtitle'),
                                                html.H6(id='pt-sell', children='0', className='pt-info-1')
                                            ]),
                                            dbc.Col([
                                                html.H6('END', className='session-info-subtitle'),
                                                html.H6(id='pt-end', children='0', className='pt-info-1')
                                            ]),
                                        ]),
                                        html.Br(),
                                        dbc.Row([
                                            dbc.Col([
                                                html.H6('SPAN ', className='session-info-subtitle'),
                                                html.H6(id='pt-span-sell', children='0', className='pt-info-sell'),
                                                html.H6(id='pt-span', children='0', className='pt-info'),
                                                html.H6(id='pt-span-buy', children='0', className='pt-info-buy')
                                            ]),
                                            dbc.Col([
                                                html.H6('DEPTH', className='session-info-subtitle'),
                                                html.H6(id='pt-depth-sell', children='0', className='pt-info-sell'),
                                                html.H6(id='pt-depth', children='0', className='pt-info'),
                                                html.H6(id='pt-depth-buy', children='0', className='pt-info-buy')
                                            ]),
                                            dbc.Col([
                                                html.H6('MTM', className='session-info-subtitle'),
                                                html.H6(id='pt-mtm-sell', children='0', className='pt-info-sell'),
                                                html.H6(id='pt-mtm', children='0', className='pt-info'),
                                                html.H6(id='pt-mtm-buy', children='0', className='pt-info-buy')
                                            ]),
                                            dbc.Col([
                                                html.H6('TBD', className='session-info-subtitle'),
                                                html.H6(id='pt-btd-sell', children='0', className='pt-info-sell'),
                                                html.H6(id='pt-btd', children='0', className='pt-info'),
                                                html.H6(id='pt-btd-buy', children='0', className='pt-info-buy')
                                            ]),
                                        ]),
                                        html.Br(),
                                        dbc.Row([
                                            dbc.Col([
                                                html.H6('STOP-PRICE ', className='session-info-subtitle-2'),
                                                html.H6(id='stop-price-profit', children='0', className='pt-info-1')
                                            ]),
                                            dbc.Col([
                                                html.H6('STOP-CMP', className='session-info-subtitle-2'),
                                                html.H6(id='actual-profit', children='0', className='pt-info-1')
                                            ]),
                                        ]),
                                        html.Br(),
                                        dbc.Row([
                                            dbc.Col([
                                                # Negative Try Count
                                                html.H6('NEG-TRY', className='global-info-subtitle-2'),
                                                html.H6(id='ntc', children='0', className='pt-info-1')
                                            ]),
                                            dbc.Col([
                                                html.H6('NEXT TRY', className='global-info-subtitle-2'),
                                                html.H6(id='time-to-next-try', children='0', className='pt-info-1')
                                            ]),
                                        ]),
                                        html.Br(),
                                        dbc.Row([
                                            dbc.Col([
                                                html.H6('IS ACTIVE', className='global-info-subtitle-2'),
                                                html.H6(id='is-active', children='0', className='pt-info-1')
                                            ]),
                                            dbc.Col([
                                                html.H6('TBD-004', className='global-info-subtitle-2'),
                                                html.H6(id='tbd-004', children='0', className='pt-info-1')
                                            ]),
                                        ]),
                                        html.Br(),
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
                                                html.H6("Global", className="card-header-global"),
                                            ], align='center'),
                                            dbc.Col([
                                                html.H6(id='global-cycle-count', children='0',
                                                        className='global-cycle-count'),
                                            ], align='center'),
                                        ]),
                                        html.Br(),
                                        dbc.Row([
                                            dbc.Col([
                                                html.H6('PLCD ', className='global-info-subtitle-3'),
                                                html.H6(id='isol-orders-placed', children='0', className='order-info')
                                            ]),
                                            dbc.Col([
                                                html.H6('PEND', className='global-info-subtitle-3'),
                                                html.H6(id='isol-orders-pending', children='0', className='order-info')
                                            ]),
                                            dbc.Col([
                                                html.H6('BUY', className='global-info-subtitle-3'),
                                                html.H6(id='isol-orders-pending-buy', children='0',
                                                        className='order-info')
                                            ]),
                                            dbc.Col([
                                                html.H6('SELL', className='global-info-subtitle-3'),
                                                html.H6(id='isol-orders-pending-sell', children='0',
                                                        className='order-info')
                                            ]),
                                        ]),
                                        html.Br(),
                                        dbc.Row([
                                            dbc.Col([
                                                html.H6('SPAN ', className='session-info-subtitle'),
                                                html.H6(id='is-span-sell', children='0', className='pt-info-sell'),
                                                html.H6(id='is-span', children='0', className='pt-info'),
                                                html.H6(id='is-span-buy', children='0', className='pt-info-buy')
                                            ]),
                                            dbc.Col([
                                                html.H6('DEPTH', className='session-info-subtitle'),
                                                html.H6(id='is-depth-sell', children='0', className='pt-info-sell'),
                                                html.H6(id='is-depth', children='0', className='pt-info'),
                                                html.H6(id='is-depth-buy', children='0', className='pt-info-buy')
                                            ]),
                                            dbc.Col([
                                                html.H6('MTM', className='session-info-subtitle'),
                                                html.H6(id='is-mtm-sell', children='0', className='pt-info-sell'),
                                                html.H6(id='is-mtm', children='0', className='pt-info'),
                                                html.H6(id='is-mtm-buy', children='0', className='pt-info-buy')
                                            ]),
                                            dbc.Col([
                                                html.H6('TBD', className='session-info-subtitle'),
                                                html.H6(id='is-btd-sell', children='0', className='pt-info-sell'),
                                                html.H6(id='is-btd', children='0', className='pt-info'),
                                                html.H6(id='is-btd-buy', children='0', className='pt-info-buy')
                                            ]),
                                        ]),
                                        html.Br(),
                                        dbc.Row([
                                            dbc.Col([
                                                html.H6('DONE', className='global-info-subtitle-2'),
                                                html.H6(id='consolidated-profit', children='0',
                                                        className='order-info-1')
                                            ]),
                                            dbc.Col([
                                                html.H6('ACTUAL', className='global-info-subtitle-2'),
                                                html.H6(id='expected-profit-at-cmp', children='0',
                                                        className='order-info-1')
                                            ]),
                                        ]),
                                        html.Br(),
                                        dbc.Row([
                                            dbc.Col([
                                                html.H6('EXPECT', className='global-info-subtitle-2'),
                                                html.H6(id='expected-profit', children='0', className='order-info-1')
                                            ]),
                                            dbc.Col([
                                                html.H6('ACTIONS', className='global-info-subtitle-2'),
                                                html.H6(id='actions-info', children='0', className='order-info-1')
                                            ]),
                                        ]),
                                        html.Br(),
                                        dbc.Row([
                                            dbc.Col([
                                                html.H6('ACTIONS RATE', className='global-info-subtitle-2'),
                                                html.H6(id='actions-rate', children='0', className='order-info-1')
                                            ]),
                                            dbc.Col([
                                                html.H6('CANCELED', className='global-info-subtitle-2'),
                                                html.H6(id='canceled-count', children='0', className='order-info-1')
                                            ]),
                                        ])
                                    ]),
                                    # dbc.CardFooter('Footer')
                                ], color='dark', inverse=True, className='scorpius-card'
                            ),
                        ])
                    ], xs=12, sm=12, md=12, lg=12, xl=12),
                ]),
                html.Br(), html.Br(), html.Br(),
                # session data #2
                # dbc.Row([
                #     dbc.Col([
                #         dbc.Row([
                #             html.H1(id='cycles-to-new-pt', children='XXX', className='cycles-to-new-pt'),
                #             html.H1(id='accounts-info', children='accounts info: (...)', className='accounts-info'),
                #             # html.H1(id='short-prediction', children='0.0', className='short-prediction'),
                #             # html.H1(id='long-prediction', children='0.0', className='long-prediction'),
                #
                #         ]),
                #     ]),
                # ]),
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
                                html.H6(id='base-asset-alive', children='0.00', className='alive'),
                                html.H6(id='base-asset-free', children='0.00', className='free'),
                                html.H6(id='base-asset-total', children='0.00', className='total')
                            ])
                        ], className='liquidity-card'),
                    ],  xs=3, sm=3, md=3, lg=3, xl=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6(id='quote-asset', className="liquidity-card-title"),
                                html.H6(id='quote-asset-locked', children='0.00', className='locked'),
                                html.H6(id='quote-asset-alive', children='0.00', className='alive'),
                                html.H6(id='quote-asset-free', children='0.00', className='free'),
                                html.H6(id='quote-asset-total', children='0.00', className='total')
                            ])
                        ], className='liquidity-card'),
                    ],  xs=3, sm=3, md=3, lg=3, xl=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("BNB", className="liquidity-card-title"),
                                html.H6(id='bnb-locked', children='0.00', className='locked'),
                                html.H6(id='bnb-alive', children='0.00', className='alive'),
                                html.H6(id='bnb-free', children='0.00', className='free'),
                                html.H6(id='bnb-total', children='0.00', className='total')
                            ])
                        ], className='liquidity-card'),
                    ], xs=3, sm=3, md=3, lg=3, xl=3),
                ]),
                html.Br(),
                dbc.Row([
                    dbc.Col([
                        html.H6(id='alert-msg', children='N/A', className='alert-msg'),
                    ])
                ]),
                html.Br(),
                dbc.Row([
                    dbc.Col([
                        dbc.Button('SYMBOL', id='button-symbols', color='success', block=True, className='sc-button'),
                        html.Br(),
                    ]),
                    dbc.Col([
                        dbc.Button('TBD-03', id='TBD-03', color='light', block=True, className='sc-button'),
                        html.Br(),
                    ]),
                    dbc.Col([
                        dbc.Button('TBD-04', id='TBD-04', color='light', block=True, className='sc-button'),
                        html.Br(),
                    ]),
                    dbc.Col([
                        dbc.Button("STOP-PRICE", id='button-stop-price', color='danger', block=True,
                                   className='sc-button'),
                        html.Br(),
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
                        dbc.Button("STOP-CMP", id='button-stop-cmp', color='danger', block=True,
                                   className='sc-button'),
                        dbc.Button('TBD', id='tbd-010', disabled=False, color='warning', block=True,
                                   className='sc-button'),
                    ]),
                    dbc.Col([
                        dbc.Button("STOP-CANCEL", id='button-stop-cancel', color='danger', block=True,
                                   className='sc-button'),
                        dbc.Button('NEW-PT', id='button-new-pt', color='warning', block=True,
                                   className='sc-button'),
                    ]),
                    dbc.Col([
                        dbc.Button('TBD-02', id='button-tbd-02', disabled=False, color='danger', block=True,
                                   className='sc-button'),
                        dbc.Button('+ 10.0 ???', id='button-increase-cmp', color='warning', block=True,
                                   className='sc-button'),
                    ]),
                    dbc.Col([
                        dbc.Button('REBOOT-SESSION', id='button-reboot-global-session', color='danger', block=True,
                                   className='sc-button'),
                        dbc.Button('- 10.0 ???', id='button-decrease-cmp', color='warning', block=True,
                                   className='sc-button'),
                    ]),
                ]),
                dcc.Interval(id='update', n_intervals=0, interval=K_UPDATE_INTERVAL)
            ],)
        ])
        return layout
