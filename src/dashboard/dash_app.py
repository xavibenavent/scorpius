# dash_app.py

# ********** important **********
# the app entry point is main.py, not dash_app.py


import dash
import dash_auth
import dash_bootstrap_components as dbc
from dash_layout import DashLayout

import logging

VALID_USERNAME_PASSWORD_PAIRS = {
    'xavi': '7639'
}

print('dash_app.py')

app = dash.Dash(__name__,
                suppress_callback_exceptions=True,
                external_stylesheets=[dbc.themes.DARKLY]
                )
# set basic authentication
auth = dash_auth.BasicAuth(app=app, username_password_list=VALID_USERNAME_PASSWORD_PAIRS)

server = app.server
app.layout = DashLayout().get_layout()

# This is the default behavior of the logger that Flask uses
# change this default behavior to only produce logs for errors:
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

