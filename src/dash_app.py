# dash_app.py

# ********** important **********
# the app entry point is main.py, not dash_app.py


import dash
from dash_layout import DashLayout


app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server
app.layout = DashLayout().get_layout()
