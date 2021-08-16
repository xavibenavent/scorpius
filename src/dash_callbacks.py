# dash_callbacks.py

from dash.dependencies import Input, Output
from dash_app import app
from dash_aux import get_balance_bar_chart, get_profit_line_chart, get_cmp_line_chart
from sc_session import QuitMode
from sc_df_manager import DataframeManager

import dash_bootstrap_components as dbc

import pandas as pd

print('dash_callbacks.py')

dfm = DataframeManager()


# ********** cmp **********
@app.callback(Output('cmp', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    return f'{dfm.sm.session.get_last_cmp():,.2f}'


# ********** buttons *********
@app.callback(Output('msg', 'children'), Input('button-stop-cmp', 'n_clicks'))
def on_button_click(n):
    if n is None:
        return ''
    else:
        dfm.sm.session.quit_particular_session(quit_mode=QuitMode.TRADE_ALL_PENDING)
        return 'cmp stop'


@app.callback(Output('stop-price', 'children'), Input('button-stop-price', 'n_clicks'))
def on_button_click(n):
    if n is None:
        return ''
    else:
        dfm.sm.session.quit_particular_session(quit_mode=QuitMode.PLACE_ALL_PENDING)
        return 'cmp stop'


@app.callback(Output('stop-cancel', 'children'), Input('button-stop-cancel', 'n_clicks'))
def on_button_click(n):
    if n is None:
        return ''
    else:
        dfm.sm.session.quit_particular_session(quit_mode=QuitMode.CANCEL_ALL)
        return 'cmp stop'


@app.callback(Output('msg-start', 'children'), Input('button-start', 'n_clicks'))
def on_button_click(n):
    print('click')
    if n is None:
        return ''
    else:
        dfm.sm.session.market.start_sockets()
        return 'cmp start'


@app.callback(Output('msg-2', 'children'), Input('button-new-pt', 'n_clicks'))
def on_button_click(n):
    if n:
        dfm.sm.session.ptm.create_new_pt(dfm.sm.session.get_last_cmp())
    return ''


@app.callback(Output('msg-increase-cmp', 'children'), Input('increase-cmp', 'n_clicks'))
def on_button_click(n):
    if n:
        dfm.sm.session.market.update_fake_client_cmp(step=10.0)
    return ''


@app.callback(Output('msg-decrease-cmp', 'children'), Input('decrease-cmp', 'n_clicks'))
def on_button_click(n):
    if n:
        dfm.sm.session.market.update_fake_client_cmp(step=-10.0)
    return ''


@app.callback(
    Output(component_id='btc-balance-chart', component_property='figure'),
    Output(component_id='eur-balance-chart', component_property='figure'),
    Output(component_id='bnb-balance-chart', component_property='figure'),
    Input(component_id='update', component_property='n_intervals')
)
def update_figure(timer):
    # ab = dfm.session.bm.get_account_balance()
    ab = dfm.sm.session.bm.current_ab

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

    fig_btc = get_balance_bar_chart(df=df_btc, asset='btc', y_max=0.3)
    fig_eur = get_balance_bar_chart(df=df_eur, asset='eur', y_max=15000)
    fig_bnb = get_balance_bar_chart(df=df_bnb, asset='bnb', y_max=50)
    return fig_btc, fig_eur, fig_bnb


# @app.callback(
#     Output('pending-table', 'data'),
#     Input('update', 'n_intervals')
# )
# def update_table(timer):
#     df = dfm.get_all_orders_df_with_cmp()
#     # sort by price
#     df1 = df.sort_values(by=['price'], ascending=False)
#     # filter by status for each table (monitor-placed & traded)
#     df_pending = df1[df1.status.isin(['monitor', 'active', 'cmp'])]
#     return df_pending.to_dict('records')


@app.callback(
    Output('new-table', 'children'),
    Input('update', 'n_intervals')
)
def update_table(timer):
    df = dfm.get_all_orders_df_with_cmp()
    # sort by price
    df1 = df.sort_values(by=['price'], ascending=False)
    # filter by status for each table (monitor-placed & traded)
    df_pending = df1[df1.status.isin(['monitor', 'active', 'cmp'])]
    return dbc.Table.from_dataframe(df_pending[['name', 'price', 'total', 'status']])


# ********** time [h] **********
@app.callback(Output('cycle-count', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    return f'{dfm.sm.session.cmp_count / 3600:,.2f}'


# ********** stop at cmp **********
@app.callback(Output('actual-profit', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    # return f'{dfm.session.ptm.get_total_actual_profit(cmp=dfm.session.cmps[-1]):,.2f}'
    return f'{dfm.sm.session.ptm.get_stop_cmp_profit(cmp=dfm.sm.session.cmps[-1]):,.2f}'


# ********** stop at price **********
@app.callback(Output('stop-price-profit', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    # return f'{dfm.session.ptm.get_total_actual_profit(cmp=dfm.session.cmps[-1]):,.2f}'
    return f'{dfm.sm.session.ptm.get_stop_price_profit(cmp=dfm.sm.session.cmps[-1]):,.2f}'


# ********** completed profit **********
@app.callback(Output('pt-completed-profit', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    return f'{dfm.sm.session.ptm.get_pt_completed_profit():,.2f}'


# ********** traded orders profit **********
@app.callback(Output('global-partial-profit', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    # called the method in session to check buy_count == sell_count
    return f'{dfm.sm.global_profit:,.2f}'


# ********** PT count / traded orders count **********
@app.callback(Output('trade-info', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    pt_count = len(dfm.sm.session.ptm.perfect_trades)
    trades_count = dfm.sm.session.buy_count + dfm.sm.session.sell_count
    # print(pt_count, trades_count)
    return f'{pt_count} / {trades_count}'


# # ********** eur needed **********
# @app.callback(Output('eur-needed', 'children'), Input('update', 'n_intervals'))
# def display_value(value):
#     eur_needed, btc_needed = dfm.sm.session.ptm.get_total_eur_btc_needed()
#     return f'{eur_needed:,.2f}'


# ********** session cycle count **********
@app.callback(Output('global-cycle-count', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    return f'{dfm.sm.global_cmp_count/3600.0:,.2f}'


# ********** session cycle count **********
@app.callback(Output('global-placed-orders', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    return f'{dfm.sm.placed_orders_count}'


# ********** session count **********
@app.callback(Output('session-count', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    return f'{dfm.sm.session_count}'


# # ********** actual profit **********
# @app.callback(Output('btc-needed', 'children'), Input('update', 'n_intervals'))
# def display_value(value):
#     _, btc_needed = dfm.sm.session.ptm.get_total_eur_btc_needed()
#     return f'{btc_needed:,.4f}'


# ********** actual profit **********
@app.callback(Output('equivalent-price', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    return f'***'


# ********** actual profit **********
@app.callback(Output('equivalent-qty', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    return f'***'


@app.callback(Output('profit-line', 'figure'), Input('update', 'n_intervals'))
def update_profit_line(timer):
    pls = dfm.sm.session.total_profit_series
    df = pd.DataFrame(data=pls, columns=['cmp'])
    df['rate'] = df.index
    fig = get_profit_line_chart(df=df, pls=pls)
    return fig


@app.callback(Output('cmp-line', 'figure'), Input('update', 'n_intervals'))
def update_profit_line(timer):
    cmps = dfm.sm.session.cmps
    df = pd.DataFrame(data=cmps, columns=['cmp'])
    df['rate'] = df.index
    fig = get_cmp_line_chart(df=df, cmps=cmps)
    return fig
