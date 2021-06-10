# dash_layout.py

import pandas as pd
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import plotly.express as px

print('dash_layout.py')

K_UPDATE_INTERVAL = 1000  # milisecs


class DashLayout:
    def get_layout(self) -> html.Div:
        layout = html.Div(children=[
            html.H1(id='title', children='Scorpius Session V1.0'),
            dbc.Row([
                dbc.Col([
                    dbc.ButtonGroup([
                        dbc.Button('New PT', id='button-new-pt', color='secondary', className='button'),
                        dbc.Button("Stop Session", id='button-stop', color="primary", className='button'),
                    ], vertical=True)
                ], width=1),
                dbc.Col([
                    self.get_card()
                ], width=3),
            ]),
            dcc.Interval(id='update', n_intervals=0, interval=K_UPDATE_INTERVAL)
        ])
        return layout

    def get_card(self) -> dbc.Card:
        card = dbc.Card(
            [
                dbc.CardImg(src="assets/bitcoin.png", top=True, bottom=False),
                dbc.CardBody(
                    [
                        html.H6(id='cmp', children="Learn Dash with Charming Data", className="card-title"),
                        html.H6(id='msg', children='')
                    ]
                ),
            ],
            color="dark",  # https://bootswatch.com/default/ for more card colors
            inverse=True,  # change color of text (black or white)
            outline=False,  # True = remove the block colors from the background and header
        )

        return card

