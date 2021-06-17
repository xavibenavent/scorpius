# dash_layout.py

import pandas as pd
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import plotly.express as px

import dash_aux as daux

print('dash_layout.py')

K_UPDATE_INTERVAL = 1000  # milisecs


class DashLayout:
    def get_layout(self) -> html.Div:
        layout = html.Div(className='app-overall', children=[
            html.Div(
                className="app-header",
                children=[
                    html.Div('Plotly Dash', className="app-header--title")
                ]
            ),
            html.Div(children=[
                html.H1(id='title', children='Scorpius Session V1.0'),
                dbc.Row([
                    dbc.Col([
                        dbc.Button('New PT', id='button-new-pt', color='secondary', block=True, className='sc-button'),
                        dbc.Button("Stop Session", id='button-stop', color="primary", block=True, className='sc-button'),
                        dbc.Button('+ 10.0 €', id='increase-cmp', color='warning', block=True, className='sc-button'),
                        dbc.Button('- 10.0 €', id='decrease-cmp', color='warning', block=True, className='sc-button'),
                    ], width=2),
                    dbc.Col([
                        self.get_card()
                    ], width=2),
                    # ********** pending orders table **********
                    dbc.Col([
                        daux.get_pending_datatable(data=[{}])
                    ], width=6, className='sc-col'),
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
                        html.H6(id='cmp', children="Learn Dash with Charming Data", className="card-title"),
                        html.H6(id='msg', children=''),
                        html.H6(id='msg-2', children=''),
                        html.H6(id='msg-increase-cmp', children=''),
                        html.H6(id='msg-decrease-cmp', children='')
                    ]
                ),
            ],
            color="dark",  # https://bootswatch.com/default/ for more card colors
            inverse=True,  # change color of text (black or white)
            outline=False,  # True = remove the block colors from the background and header
        )

        return card

