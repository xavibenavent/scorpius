# dash_callbacks.py

from dash.dependencies import Input, Output
from dash_app import app
from sc_session import QuitMode
from sc_df_manager import DataframeManager

print('dash_callbacks.py')
# create session
# session = Session(client_mode=ClientMode.CLIENT_MODE_SIMULATOR)
dfm = DataframeManager()


@app.callback(
    Output('cmp', 'children'),
    Input('update', 'n_intervals')
)
def display_value(value):
    return f'{dfm.session.get_last_cmp():,.2f}'


@app.callback(
    Output('msg', 'children'),
    Input('button-stop', 'n_clicks')
)
def on_button_click(n):
    if n is None:
        return ''
    else:
        dfm.session.quit(quit_mode=QuitMode.CANCEL_ALL_PLACED)
        return 'cmp stop'
