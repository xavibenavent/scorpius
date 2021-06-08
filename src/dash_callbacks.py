# dash_callbacks.py

from dash.dependencies import Input, Output
from dash_app import app


@app.callback(
    Output('title', 'children'),
    Input('dropdown_1', 'value')
)
def display_value(value):
    return f'good afternoon {value}'