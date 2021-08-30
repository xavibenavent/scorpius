# dash_callbacks.py

import dash
from dash.dependencies import Input, Output
from dash_app import app
from dash_aux import get_profit_line_chart, get_cmp_line_chart, get_pending_html_table
from sc_session import QuitMode
from sc_df_manager import DataframeManager
from binance import enums as k_binance

# import dash_bootstrap_components as dbc

import pandas as pd
from datetime import datetime, timedelta

print('dash_callbacks.py')

dfm = DataframeManager()

# SYMBOL = 'BTCEUR'


# ********** cmp **********
@app.callback(Output('cmp', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    symbol_name = dfm.dashboard_active_symbol.name
    return f'{dfm.sm.active_sessions[symbol_name].cmps[-1] if dfm.sm.active_sessions[symbol_name].cmps else 0:,.2f}'


@app.callback(Output('current-time', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    return f'{datetime.now().strftime("%H:%M:%S")}'


@app.callback(Output('neb', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    symbol_name = dfm.dashboard_active_symbol.name
    quote_name = dfm.dashboard_active_symbol.quote_asset().name()
    return f'n: {dfm.sm.active_sessions[symbol_name].net_quote_balance:,.2f} {quote_name}'


@app.callback(Output('qty', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    symbol_name = dfm.dashboard_active_symbol.name
    base_name = dfm.dashboard_active_symbol.base_asset().name()
    return f'q: {dfm.sm.active_sessions[symbol_name].quantity:,.4f} {base_name}'


@app.callback(Output('target', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    symbol_name = dfm.dashboard_active_symbol.name
    quote_name = dfm.dashboard_active_symbol.quote_asset().name()
    return f't: {dfm.sm.active_sessions[symbol_name].target_total_net_profit:,.2f} {quote_name}'


@app.callback(Output('max-negative-profit-allowed', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    symbol_name = dfm.dashboard_active_symbol.name
    return f'({dfm.sm.active_sessions[symbol_name].max_negative_profit_allowed:,.2f})'


# ********** buttons *********
@app.callback(Output('button-btceur-hidden-msg', 'color'),
              Input('button-btceur', 'n_clicks'),
              )
def on_button_click(n):
    # set BTCEUR as active symbol if button pressed
    if n is not None:
        dfm.set_dashboard_active_symbol(symbol_name='BTCEUR')
    return ''


@app.callback(Output('button-bnbeur-hidden-msg', 'children'),
              Input('button-bnbeur', 'n_clicks'),
              )
def on_button_click(n):
    # set BNBEUR as active symbol if button pressed
    if n is not None:
        dfm.set_dashboard_active_symbol(symbol_name='BNBEUR')
    return ''


@app.callback(Output('button-btceur', 'color'),
              Output('button-bnbeur', 'color'),
              Input('update', 'n_intervals'),
              )
def on_button_click(n):
    # identify last button clicked
    # changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    btceur_color = 'success' if dfm.dashboard_active_symbol.name == 'BTCEUR' else 'light'
    bnbeur_color = 'success' if dfm.dashboard_active_symbol.name == 'BNBEUR' else 'light'
    # print(btceur_color, bnbeur_color)
    return btceur_color, bnbeur_color


# @app.callback(Output('msg', 'children'), Input('button-stop-cmp', 'n_clicks'))
@app.callback(Output('button-stop-cmp', 'children'), Input('button-stop-cmp', 'n_clicks'))
def on_button_click(n):
    if n is not None:
        symbol_name = dfm.dashboard_active_symbol.name
        dfm.sm.active_sessions[symbol_name].quit_particular_session(quit_mode=QuitMode.TRADE_ALL_PENDING)
    return 'Stop at cmp'


@app.callback(Output('button-stop-price', 'children'), Input('button-stop-price', 'n_clicks'))
def on_button_click(n):
    if n is not None:
        symbol_name = dfm.dashboard_active_symbol.name
        dfm.sm.active_sessions[symbol_name].quit_particular_session(quit_mode=QuitMode.PLACE_ALL_PENDING)
    return 'Stop at price'


@app.callback(Output('stop-cancel', 'children'), Input('button-stop-cancel', 'n_clicks'))
def on_button_click(n):
    if n is None:
        return ''
    else:
        symbol_name = dfm.dashboard_active_symbol.name
        dfm.sm.active_sessions[symbol_name].quit_particular_session(quit_mode=QuitMode.CANCEL_ALL)
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
        symbol = dfm.dashboard_active_symbol
        symbol_name = symbol.name
        cmp = dfm.sm.active_sessions[symbol_name].cmps[-1] if dfm.sm.active_sessions[symbol_name].cmps else 0
        dfm.sm.active_sessions[symbol_name].manually_create_new_pt(cmp=cmp, symbol=symbol)
    return ''


@app.callback(Output('msg-increase-cmp', 'children'), Input('increase-cmp', 'n_clicks'))
def on_button_click(n):
    if n:
        symbol_name = dfm.dashboard_active_symbol.name
        dfm.sm.active_sessions[symbol_name].market.update_fake_client_cmp(step=10.0, symbol_name=symbol_name)
    return ''


@app.callback(Output('msg-decrease-cmp', 'children'), Input('decrease-cmp', 'n_clicks'))
def on_button_click(n):
    if n:
        symbol_name = dfm.dashboard_active_symbol.name
        dfm.sm.active_sessions[symbol_name].market.update_fake_client_cmp(step=-10.0, symbol_name=symbol_name)
    return ''


# ********** accounts data **********

@app.callback(
    Output('base-asset-free', 'children'), Output('base-asset-locked', 'children'),
    Input('update', 'n_intervals')
)
def display_value(value):
    symbol = dfm.dashboard_active_symbol
    symbol_name = symbol.name
    bm = dfm.sm.active_sessions[symbol_name].am
    base_account = bm.get_account(symbol.base_asset().name())
    return f'{base_account.free:,.{symbol.base_asset().pv()}f}', f'{base_account.locked:,.{symbol.base_asset().pv()}f}'


@app.callback(
    Output('quote-asset-free', 'children'),
    Input('update', 'n_intervals')
)
def display_value(value):
    symbol = dfm.dashboard_active_symbol
    symbol_name = symbol.name
    bm = dfm.sm.active_sessions[symbol_name].am
    quote_account = bm.get_account(symbol.quote_asset().name())
    return f'{quote_account.free:,.{symbol.quote_asset().pv()}f}'



@app.callback(
    Output('quote-asset-locked', 'children'),
    Input('update', 'n_intervals')
)
def display_value(value):
    symbol = dfm.dashboard_active_symbol
    symbol_name = symbol.name
    bm = dfm.sm.active_sessions[symbol_name].am
    quote_account = bm.get_account(symbol.quote_asset().name())
    return f'{quote_account.locked:,.{symbol.quote_asset().pv()}f}'


@app.callback(
    Output('bnb-free', 'children'),
    Input('update', 'n_intervals')
)
def display_value(value):
    symbol = dfm.dashboard_active_symbol
    symbol_name = symbol.name
    bm = dfm.sm.active_sessions[symbol_name].am
    bnb_account = bm.get_account('BNB')
    return f'{bnb_account.free:,.6f}'


@app.callback(
    Output('bnb-locked', 'children'),
    Input('update', 'n_intervals')
)
def display_value(value):
    symbol = dfm.dashboard_active_symbol
    symbol_name = symbol.name
    bm = dfm.sm.active_sessions[symbol_name].am
    bnb_account = bm.get_account('BNB')
    return f'{bnb_account.locked:,.6f}'


# ********** others **********

@app.callback(Output('symbol', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    return dfm.dashboard_active_symbol.name


@app.callback(Output('base-asset', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    return dfm.dashboard_active_symbol.base_asset().name()


@app.callback(Output('quote-asset', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    return dfm.dashboard_active_symbol.quote_asset().name()


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
    qp = dfm.dashboard_active_symbol.quote_asset().pv()
    df_pending['price'] = df_pending['price'].map(f'{{:,.{qp}f}}'.format)  # two {{ }} to escape { in f-string
    df_pending['total'] = df_pending['total'].map(f'{{:,.{qp}f}}'.format)

    return get_pending_html_table(df=df_pending[['pt_id', 'name', 'price', 'amount', 'total', 'status']])


# ********** time [h] **********
@app.callback(Output('cycle-count', 'children'), Input('update', 'n_intervals'))
def display_value(value):

    # todo: use momentum
    # print(dfm.sm.session.get_info()['momentum'])

    # return f'{dfm.sm.session.get_info()["cmp_count"] / 3600:,.2f} h'
    symbol_name = dfm.dashboard_active_symbol.name
    return f'{timedelta(seconds=dfm.sm.active_sessions[symbol_name].cmp_count)}'


# ********** stop at cmp **********
@app.callback(Output('actual-profit', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    symbol_name = dfm.dashboard_active_symbol.name
    cmp = dfm.sm.active_sessions[symbol_name].cmps[-1]
    return f'{dfm.sm.active_sessions[symbol_name].ptm.get_total_actual_profit_at_cmp(cmp=cmp):,.2f} €'


# ********** stop at price **********
@app.callback(Output('stop-price-profit', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    symbol = dfm.dashboard_active_symbol
    symbol_name = symbol.name
    cmp = dfm.sm.active_sessions[symbol_name].cmps[-1]
    qp = symbol.quote_asset().pv()
    coin_symbol = symbol.quote_asset().name()
    return f'{dfm.sm.active_sessions[symbol_name].ptm.get_stop_price_profit(cmp=cmp):,.{qp}f} {coin_symbol}'


# ********** completed profit **********
@app.callback(Output('pt-completed-profit', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    symbol = dfm.dashboard_active_symbol
    symbol_name = symbol.name
    qp = symbol.quote_asset().pv()
    coin_symbol = symbol.quote_asset().name()
    return f'{dfm.sm.active_sessions[symbol_name].ptm.get_consolidated_profit():,.{qp}f} {coin_symbol}'


# ********** traded orders profit **********
@app.callback(Output('global-partial-profit', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    symbol = dfm.dashboard_active_symbol
    symbol_name = symbol.name
    cmp = dfm.sm.active_sessions[symbol_name].cmps[-1]
    qp = symbol.quote_asset().pv()
    coin_symbol = symbol.quote_asset().name()
    # called the method in session to check buy_count == sell_count
    consolidated = dfm.sm.terminated_sessions[symbol_name]['global_consolidated_profit']
    expected = dfm.sm.terminated_sessions[symbol_name]['global_expected_profit']
    expected_at_cmp = dfm.sm.iom.get_expected_profit_at_cmp(cmp=cmp)
    return f'{consolidated:,.{qp}f} {coin_symbol} / ' \
           f'{expected:,.{qp}f} {coin_symbol} / ' \
           f'{expected_at_cmp:,.{qp}f} {coin_symbol}'


# ********** PT count / traded orders count **********
@app.callback(Output('trade-info', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    symbol_name = dfm.dashboard_active_symbol.name
    pt_count = len(dfm.sm.active_sessions[symbol_name].ptm.perfect_trades)
    buy_count = dfm.sm.active_sessions[symbol_name].buy_count
    sell_count = dfm.sm.active_sessions[symbol_name].sell_count
    return f'pt: {pt_count}   b: {buy_count}   s: {sell_count}'


@app.callback(Output('cycles-to-new-pt', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    symbol_name = dfm.dashboard_active_symbol.name
    ccfi = dfm.sm.active_sessions[symbol_name].cycles_count_for_inactivity
    cycles_to_new_pt = ccfi - dfm.sm.active_sessions[symbol_name].cycles_from_last_trade
    time_to_new_pt = timedelta(seconds=cycles_to_new_pt)
    return f'({ccfi})  {time_to_new_pt}'


@app.callback(Output('accounts-info', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    accounts_info = [f'{account.name}: {account.free:,.2f} ' for account in dfm.sm.am.accounts.values()]
    accounts_info_s = ' '.join(map(str, accounts_info))
    return accounts_info_s


# ********** session cycle count **********
@app.callback(Output('global-cycle-count', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    symbol_name = dfm.dashboard_active_symbol.name
    global_cmp = dfm.sm.terminated_sessions[symbol_name]["global_cmp_count"]
    session_cmp = dfm.sm.active_sessions[symbol_name].cmp_count
    return f'{timedelta(seconds=global_cmp + session_cmp)}'


# ********** session cycle count **********
@app.callback(Output('global-placed-orders', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    symbol_name = dfm.dashboard_active_symbol.name
    placed = dfm.sm.terminated_sessions[symbol_name]['global_placed_orders_count_at_price']
    still_isolated = dfm.sm.terminated_sessions[symbol_name]['global_placed_pending_orders_count']
    sell = len([order for order in dfm.sm.iom.isolated_orders if order.k_side == k_binance.SIDE_SELL])
    buy = len([order for order in dfm.sm.iom.isolated_orders if order.k_side == k_binance.SIDE_BUY])
    return f'p: {placed} / i: {still_isolated} (s: {sell} b: {buy})'


# ********** session count **********
@app.callback(Output('session-count', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    symbol_name = dfm.dashboard_active_symbol.name
    consolidated_count = dfm.sm.terminated_sessions[symbol_name]['global_consolidated_session_count']
    expected_count = dfm.sm.terminated_sessions[symbol_name]['global_expected_session_count']
    session_count = consolidated_count + expected_count
    # session_count = dfm.sm.session_count - 1  # todo: fix it. it must reflect the value per symbol
    return f's: {session_count}  (c:{consolidated_count}  e:{expected_count})'


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
    symbol_name = dfm.dashboard_active_symbol.name
    pls = dfm.sm.active_sessions[symbol_name].total_profit_series
    df = pd.DataFrame(data=pls, columns=['cmp'])
    df['rate'] = df.index
    fig = get_profit_line_chart(df=df, pls=pls)
    return fig


@app.callback(Output('cmp-line', 'figure'), Input('update', 'n_intervals'))
def update_profit_line(timer):
    symbol_name = dfm.dashboard_active_symbol.name
    cmps = dfm.sm.active_sessions[symbol_name].cmps
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
