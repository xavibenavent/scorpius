# dash_app.py

# ********** important **********
# the app entry point is main.py, not dash_app.py


import dash
import dash_bootstrap_components as dbc
from dash_layout import DashLayout

print('dash_app.py')

app = dash.Dash(__name__,
                suppress_callback_exceptions=True,
                external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server
app.layout = DashLayout().get_layout()
