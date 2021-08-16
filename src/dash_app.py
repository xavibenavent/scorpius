# dash_app.py

# ********** important **********
# the app entry point is main.py, not dash_app.py


import dash
import dash_bootstrap_components as dbc
from dash_layout import DashLayout

import logging

print('dash_app.py')

app = dash.Dash(__name__,
                suppress_callback_exceptions=True,
                external_stylesheets=[dbc.themes.SLATE])
server = app.server
app.layout = DashLayout().get_layout()

# This is the default behavior of the logger that Flask uses
# change this default behavior to only produce logs for errors:
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

