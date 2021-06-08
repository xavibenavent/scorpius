# dash_layout.py

import pandas as pd
import dash_html_components as html
import dash_core_components as dcc
import plotly.express as px


class DashLayout:
    def get_layout(self) -> html.Div:
        layout = html.Div(children=[
            html.H1(id='title', children='Hello Dash'),

            html.Div(children='''
                Dash: A web application framework for Python.
            '''),

            dcc.Dropdown(id='dropdown_1',
                         options=[
                             {'label': 'New York City', 'value': 'NYC'},
                             {'label': 'Montreal', 'value': 'MTL'},
                             {'label': 'San Francisco', 'value': 'SF'}
                         ],
                         value='NYC'
                         ),

            dcc.Graph(
                id='example-graph',
                figure=self.get_fig()
            )
        ])
        return layout

    def get_fig(self) -> px.bar():
        df = pd.DataFrame({
            "Fruit": ["Apples", "Oranges", "Bananas", "Apples", "Oranges", "Bananas"],
            "Amount": [4, 1, 2, 2, 4, 5],
            "City": ["SF", "SF", "SF", "Montreal", "Montreal", "Montreal"]
        })

        fig = px.bar(df, x="Fruit", y="Amount", color="City", barmode="group")

        return fig

