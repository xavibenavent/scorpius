# dash_callbacks.py

from dash.dependencies import Input, Output
from dash_app import app
from dash_aux import get_profit_line_chart, get_cmp_line_chart, get_pending_html_table
from sc_session import QuitMode
from sc_df_manager import DataframeManager

# import dash_bootstrap_components as dbc

import pandas as pd
from datetime import datetime, timedelta

print('dash_callbacks.py')

dfm = DataframeManager()


# ********** cmp **********
@app.callback(Output('cmp', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    return f'{dfm.sm.session.get_info()["last_cmp"]:,.2f}'


@app.callback(Output('current-time', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    return f'{datetime.now().strftime("%H:%M:%S")}'


@app.callback(Output('neb', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    return f'n: {dfm.sm.session.net_eur_balance:,.2f} EUR'


@app.callback(Output('qty', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    return f'q: {dfm.sm.session.quantity:,.4f} BTC'


@app.callback(Output('target', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    return f't: {dfm.sm.session.target_total_net_profit:,.2f} EUR'


@app.callback(Output('max-negative-profit-allowed', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    return f'({dfm.sm.session.max_negative_profit_allowed:,.2f})'


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


@app.callback(Output('stop-global-session', 'children'), Input('button-stop-global-session', 'n_clicks'))
def on_button_click(n):
    if n is None:
        return ''
    else:
        dfm.sm.stop_global_session()
        return 'cmp stop'


@app.callback(Output('msg-start', 'children'), Input('button-start', 'n_clicks'))
def on_button_click(n):
    print('button start')
    if n is None:
        return ''
    else:
        # dfm.sm.session = dfm.sm.start_new_session()
        print("trying to restart connection")
        # todo: reconnect when Exception connection error
        # raise Exception("fix it")
        # dfm.sm = dfm.start_session_manager()
        dfm.sm.market.hot_reconnect()
        return 'cmp start'


@app.callback(Output('msg-2', 'children'), Input('button-new-pt', 'n_clicks'))
def on_button_click(n):
    if n:
        cmp = dfm.sm.session.get_info()['last_cmp']
        if dfm.sm.session.allow_new_pt_creation(cmp=cmp):
            dfm.sm.session.ptm.create_new_pt(cmp=cmp)
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
    Output(component_id='eur-free', component_property='children'),
    Output(component_id='eur-locked', component_property='children'),
    Output(component_id='btc-free', component_property='children'),
    Output(component_id='btc-locked', component_property='children'),
    Output(component_id='bnb-free', component_property='children'),
    Output(component_id='bnb-locked', component_property='children'),
    Input(component_id='update', component_property='n_intervals')
)
def update_figure(timer):
    ab = dfm.sm.session.bm.accounts
    return f'{ab[1].free:,.2f}', f'{ab[1].locked:,.2f}',\
           f'{ab[0].free:,.6f}', f'{ab[0].locked:,.6f}',\
           f'{ab[2].free:,.6f}', f'{ab[2].locked:,.6f}'
    # ab = dfm.sm.session.bm.current_ab
    # return f'{ab.s2.free:,.2f}', f'{ab.s2.locked:,.2f}',\
    #        f'{ab.s1.free:,.6f}', f'{ab.s1.locked:,.6f}',\
    #        f'{ab.bnb.free:,.6f}', f'{ab.bnb.locked:,.6f}'


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
    df_pending['price'] = df_pending['price'].map('{:,.2f}'.format)
    df_pending['total'] = df_pending['total'].map('{:,.2f}'.format)

    return get_pending_html_table(df=df_pending[['pt_id', 'name', 'price', 'amount', 'total', 'status']])


# ********** time [h] **********
@app.callback(Output('cycle-count', 'children'), Input('update', 'n_intervals'))
def display_value(value):

    # todo: use momentum
    # print(dfm.sm.session.get_info()['momentum'])

    # return f'{dfm.sm.session.get_info()["cmp_count"] / 3600:,.2f} h'

    return f'{timedelta(seconds=dfm.sm.session.get_info()["cmp_count"])}'


# ********** stop at cmp **********
@app.callback(Output('actual-profit', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    # return f'{dfm.session.ptm.get_total_actual_profit(cmp=dfm.session.cmps[-1]):,.2f}'
    return f'{dfm.sm.session.ptm.get_stop_cmp_profit(cmp=dfm.sm.session.cmps[-1]):,.2f} €'


# ********** stop at price **********
@app.callback(Output('stop-price-profit', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    # return f'{dfm.session.ptm.get_total_actual_profit(cmp=dfm.session.cmps[-1]):,.2f}'
    return f'{dfm.sm.session.ptm.get_stop_price_profit(cmp=dfm.sm.session.cmps[-1]):,.2f} €'


# ********** completed profit **********
@app.callback(Output('pt-completed-profit', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    return f'{dfm.sm.session.ptm.get_pt_completed_profit():,.2f} €'


# ********** traded orders profit **********
@app.callback(Output('global-partial-profit', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    # called the method in session to check buy_count == sell_count
    return f'{dfm.sm.global_consolidated_profit:,.2f} € / {dfm.sm.global_expected_profit:,.2f} €'


# ********** PT count / traded orders count **********
@app.callback(Output('trade-info', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    pt_count = len(dfm.sm.session.ptm.perfect_trades)
    buy_count = dfm.sm.session.buy_count
    sell_count = dfm.sm.session.sell_count
    return f'pt: {pt_count}   b: {buy_count}   s: {sell_count}'


@app.callback(Output('cycles-to-new-pt', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    ccfi = dfm.sm.session.cycles_count_for_inactivity
    cycles_to_new_pt = ccfi - dfm.sm.session.cycles_from_last_trade
    time_to_new_pt = timedelta(seconds=cycles_to_new_pt)
    return f'({ccfi})  {time_to_new_pt}'


# ********** session cycle count **********
@app.callback(Output('global-cycle-count', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    return f'{timedelta(seconds=dfm.sm.global_cmp_count + dfm.sm.session.cmp_count)}'


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


# @app.callback([Output('modal', 'is_open'), Output('modal-body', 'children')],
#               [Input('update', 'n_intervals')],
#               [State('modal', 'is_open')])
# def toggle_modal(timer, is_open: bool):
#     if not is_open:
#         if len(dfm.sm.session.modal_alert_messages) > 0:
#             return  True, dfm.sm.session.modal_alert_messages
#         else:
#             return False, ''
#     else:
#         if close_tapped_count == dfm.sm.session.buy_count + dfm.sm.session.sell_count:
#             button_click = close_tapped_count
#             if len(dfm.sm.session.modal_alert_messages) > 0:
#                 dfm.sm.session.modal_alert_messages.pop(0)
#             return False, ''
#         else:
#             return  True, dfm.sm.session.modal_alert_messages
