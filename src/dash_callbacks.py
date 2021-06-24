# dash_callbacks.py

from dash.dependencies import Input, Output
from dash_app import app
from dash_aux import get_balance_bar_chart
from sc_session import QuitMode
from sc_df_manager import DataframeManager

import pandas as pd

print('dash_callbacks.py')

dfm = DataframeManager()


# ********** cmp **********
@app.callback(Output('cmp', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    return f'{dfm.session.get_last_cmp():,.2f}'


# ********** buttons *********
@app.callback(Output('msg', 'children'), Input('button-stop', 'n_clicks'))
def on_button_click(n):
    if n is None:
        return ''
    else:
        dfm.session.quit(quit_mode=QuitMode.CANCEL_ALL_PLACED)
        return 'cmp stop'


@app.callback(Output('msg-2', 'children'), Input('button-new-pt', 'n_clicks'))
def on_button_click(n):
    if n:
        dfm.session.ptm.create_new_pt(dfm.session.get_last_cmp())
    return ''


@app.callback(Output('msg-increase-cmp', 'children'), Input('increase-cmp', 'n_clicks'))
def on_button_click(n):
    if n:
        dfm.session.market.update_fake_client_cmp(step=10.0)
    return ''


@app.callback(Output('msg-decrease-cmp', 'children'), Input('decrease-cmp', 'n_clicks'))
def on_button_click(n):
    if n:
        dfm.session.market.update_fake_client_cmp(step=-10.0)
    return ''


@app.callback(
    Output(component_id='btc-balance-chart', component_property='figure'),
    Output(component_id='eur-balance-chart', component_property='figure'),
    Output(component_id='bnb-balance-chart', component_property='figure'),
    Input(component_id='update', component_property='n_intervals')
)
def update_figure(timer):
    ab = dfm.session.bm.get_account_balance()

    df_btc = pd.DataFrame([
        dict(asset='btc', amount=ab.s1.free, type='free'),
        dict(asset='btc', amount=ab.s1.locked, type='locked'),
    ])
    df_eur = pd.DataFrame([
        dict(asset='eur', amount=ab.s2.free, type='free'),
        dict(asset='eur', amount=ab.s2.locked, type='locked'),
    ])
    df_bnb = pd.DataFrame([
        dict(asset='bnb', amount=ab.bnb.free, type='free'),
        dict(asset='bnb', amount=ab.bnb.locked, type='locked'),
    ])

    fig_btc = get_balance_bar_chart(df=df_btc, asset='btc', y_max=0.2)
    fig_eur = get_balance_bar_chart(df=df_eur, asset='eur', y_max=10000)
    fig_bnb = get_balance_bar_chart(df=df_bnb, asset='bnb', y_max=55)
    return fig_btc, fig_eur, fig_bnb



@app.callback(
    Output('pending-table', 'data'),
    Input('update', 'n_intervals')
)
def update_table(timer):
    df = dfm.get_all_orders_df_with_cmp()
    # sort by price
    df1 = df.sort_values(by=['price'], ascending=False)
    # filter by status for each table (monitor-placed & traded)
    df_pending = df1[df1.status.isin(['monitor', 'placed', 'cmp'])]
    return df_pending.to_dict('records')

