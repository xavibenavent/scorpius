# dash_callbacks.py

from dash.dependencies import Input, Output
from dash_app import app
from sc_session import QuitMode
from sc_df_manager import DataframeManager

print('dash_callbacks.py')

dfm = DataframeManager()


@app.callback(
    Output('cmp', 'children'),
    Input('update', 'n_intervals')
)
def display_value(value):
    return f'{dfm.session.get_last_cmp():,.2f}'


# ********** buttons *********
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


@app.callback(
    Output('msg-2', 'children'),
    Input('button-new-pt', 'n_clicks')
)
def on_button_click(n):
    if n is None:
        return ''
    else:
        dfm.session.ptm.create_new_pt(dfm.session.get_last_cmp())
        return 'new pt created'

@app.callback(
    Output('pending-table', 'data'),
    Input('update', 'n_intervals')
)
def update_table(timer):
    df = dfm.get_all_orders_df_with_cmp()
    # sort by price
    df1 = df.sort_values(by=['price'], ascending=False)
    # filter by status for each table (monitor-placed & traded)
    df_pending = df1[df1.status_name.isin(['monitor', 'placed', 'cmp'])]
    return df_pending.to_dict('records')

