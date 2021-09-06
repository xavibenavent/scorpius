# dash_callbacks.py

from dash.dependencies import Input, Output
from dashboard.dash_app import app
from dashboard.dash_aux import get_pending_html_table
from sc_session import QuitMode
from dashboard.sc_df_manager import DataframeManager
from binance import enums as k_binance
from datetime import datetime, timedelta
from sc_perfect_trade import PerfectTradeStatus

print('dash_callbacks.py')

dfm = DataframeManager()


# first line data
@app.callback(Output('current-time', 'children'),
              Output('neb', 'children'),  # perfect trade net profit
              Output('qty', 'children'),  # orders quantity
              Output('target', 'children'),  # session target net profit
              Output('max-negative-profit-allowed', 'children'),  # if reached, session ended at price
              Input('update', 'n_intervals'))
def display_value(value):
    symbol_name = dfm.dashboard_active_symbol.name
    quote_name = dfm.dashboard_active_symbol.quote_asset().name()
    base_name = dfm.dashboard_active_symbol.base_asset().name()

    return \
        f'{datetime.now().strftime("%H:%M:%S")}',\
        f'n: {dfm.sm.active_sessions[symbol_name].net_quote_balance:,.2f} {quote_name}',\
        f'q: {dfm.sm.active_sessions[symbol_name].quantity:,.4f} {base_name}',\
        f't: {dfm.sm.active_sessions[symbol_name].target_total_net_profit:,.2f} {quote_name}',\
        f'({dfm.sm.active_sessions[symbol_name].max_negative_profit_allowed:,.2f})'


# **********************************
# ********** Session data **********
# **********************************

# elapsed time
@app.callback(Output('session-cycle-count', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    symbol_name = dfm.dashboard_active_symbol.name
    return f'{timedelta(seconds=dfm.sm.active_sessions[symbol_name].cmp_count)}'


# perfect trade status info
@app.callback(Output('pt-new', 'children'),
              Output('pt-buy', 'children'),
              Output('pt-sell', 'children'),
              Output('pt-end', 'children'),
              Input('update', 'n_intervals'))
def display_value(value):
    symbol_name = dfm.dashboard_active_symbol.name
    ptm = dfm.sm.active_sessions[symbol_name].ptm
    return \
        len(ptm.get_pt_by_request(pt_status=[PerfectTradeStatus.NEW])),\
        len(ptm.get_pt_by_request(pt_status=[PerfectTradeStatus.BUY_TRADED])),\
        len(ptm.get_pt_by_request(pt_status=[PerfectTradeStatus.SELL_TRADED])),\
        len(ptm.get_pt_by_request(pt_status=[PerfectTradeStatus.COMPLETED]))


# span, depth, momentum & TBD data
@app.callback(Output('pt-span', 'children'),
              Output('pt-span-buy', 'children'),
              Output('pt-span-sell', 'children'),
              Output('pt-depth', 'children'),
              Output('pt-depth-buy', 'children'),
              Output('pt-depth-sell', 'children'),
              Output('pt-mtm', 'children'),
              Output('pt-mtm-buy', 'children'),
              Output('pt-mtm-sell', 'children'),
              Input('update', 'n_intervals'))
def display_value(value):
    data = dfm.get_span_depth_momentum()
    total_span = data.get("buy_span") + data.get("sell_span")
    total_depth = data.get('buy_depth') + data.get('sell_depth')
    total_momentum = data.get('buy_momentum') + data.get('sell_momentum')
    return \
        f'{total_span:.2f}',\
        f'{data.get("buy_span"):.2f}',\
        f'{data.get("sell_span"):.2f}', \
        f'{total_depth:.2f}', \
        f'{data.get("buy_depth"):.2f}', \
        f'{data.get("sell_depth"):.2f}', \
        f'{total_momentum:.2f}', \
        f'{data.get("buy_momentum"):.2f}', \
        f'{data.get("sell_momentum"):.2f}'


# ********** stop at cmp **********
@app.callback(Output('actual-profit', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    symbol_name = dfm.dashboard_active_symbol.name
    quote_asset_name = dfm.dashboard_active_symbol.quote_asset().name()
    cmp = dfm.sm.active_sessions[symbol_name].cmp
    return f'{dfm.sm.active_sessions[symbol_name].ptm.get_total_actual_profit_at_cmp(cmp=cmp):,.2f}'  # {quote_asset_name}'


# ********** stop at price **********
@app.callback(Output('stop-price-profit', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    symbol = dfm.dashboard_active_symbol
    symbol_name = symbol.name
    cmp = dfm.sm.active_sessions[symbol_name].cmps[-1]
    qp = symbol.quote_asset().pv()
    coin_symbol = symbol.quote_asset().name()
    return f'{dfm.sm.active_sessions[symbol_name].ptm.get_stop_price_profit(cmp=cmp):,.{qp}f}'  # {coin_symbol}'


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
    expected_at_cmp = dfm.sm.iom.get_expected_profit_at_cmp(cmp=cmp, symbol_name=symbol_name)
    return f'{consolidated:,.{qp}f} / ' \
           f'{expected:,.{qp}f} / ' \
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
    sell = len(
        [order for order in dfm.sm.iom.isolated_orders
         if order.k_side == k_binance.SIDE_SELL and order.symbol.name == symbol_name]
    )
    buy = len(
        [order for order in dfm.sm.iom.isolated_orders
         if order.k_side == k_binance.SIDE_BUY and order.symbol == symbol_name]
    )
    return f'p: {placed} / i: {still_isolated} (s: {sell} b: {buy})'


# ********** session count **********
@app.callback(Output('session-count', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    symbol_name = dfm.dashboard_active_symbol.name
    consolidated_count = dfm.sm.terminated_sessions[symbol_name]['global_consolidated_session_count']
    expected_count = dfm.sm.terminated_sessions[symbol_name]['global_expected_session_count']
    session_count = consolidated_count + expected_count
    return f's: {session_count}  (c:{consolidated_count}  e:{expected_count})'







# ********** symbol & accounts data **********
@app.callback(
    Output('symbol', 'children'),
    Output('cmp-max', 'children'),
    Output('cmp', 'children'),
    Output('cmp-min', 'children'),
    Output('base-asset', 'children'),
    Output('base-asset-free', 'children'),
    Output('base-asset-locked', 'children'),
    Output('quote-asset', 'children'),
    Output('quote-asset-free', 'children'),
    Output('quote-asset-locked', 'children'),
    Output('bnb-free', 'children'),
    Output('bnb-locked', 'children'),
    Input('update', 'n_intervals')
)
def display_value(value):
    symbol = dfm.dashboard_active_symbol
    symbol_name = symbol.name
    bm = dfm.sm.active_sessions[symbol_name].am
    base_account = bm.get_account(symbol.base_asset().name())
    quote_account = bm.get_account(symbol.quote_asset().name())
    bnb_account = bm.get_account('BNB')
    quote_pv = symbol.quote_asset().pv()

    return \
        symbol_name, \
        f'{dfm.sm.active_sessions[symbol_name].max_cmp:,.{quote_pv}f}', \
        f'{dfm.sm.active_sessions[symbol_name].cmp:,.{quote_pv}f}', \
        f'{dfm.sm.active_sessions[symbol_name].min_cmp:,.{quote_pv}f}', \
        symbol.base_asset().name(),\
        f'{base_account.free:,.{symbol.base_asset().pv()}f}', \
        f'{base_account.locked:,.{symbol.base_asset().pv()}f}', \
        symbol.quote_asset().name(), \
        f'{quote_account.free:,.{symbol.quote_asset().pv()}f}', \
        f'{quote_account.locked:,.{symbol.quote_asset().pv()}f}',\
        f'{bnb_account.free:,.6f}',\
        f'{bnb_account.locked:,.6f}'


# ********** symbol selection buttons *********
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


# update symbol selection button colors (green/gray)
@app.callback(Output('button-btceur', 'color'),
              Output('button-bnbeur', 'color'),
              Input('update', 'n_intervals'),
              )
def on_button_click(n):
    # identify last button clicked
    btceur_color = 'success' if dfm.dashboard_active_symbol.name == 'BTCEUR' else 'light'
    bnbeur_color = 'success' if dfm.dashboard_active_symbol.name == 'BNBEUR' else 'light'
    return btceur_color, bnbeur_color


# Stop buttons
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


@app.callback(Output('button-stop-cancel', 'children'), Input('button-stop-cancel', 'n_clicks'))
def on_button_click(n):
    if n is None:
        return ''
    else:
        symbol_name = dfm.dashboard_active_symbol.name
        dfm.sm.active_sessions[symbol_name].quit_particular_session(quit_mode=QuitMode.CANCEL_ALL)
        return 'Stop-cancel'


@app.callback(Output('button-stop-global-session', 'children'), Input('button-stop-global-session', 'n_clicks'))
def on_button_click(n):
    if n is None:
        return ''
    else:
        dfm.sm.stop_global_session()
        return 'Stop Session'


@app.callback(Output('button-new-pt', 'children'), Input('button-new-pt', 'n_clicks'))
def on_button_click(n):
    if n:
        symbol = dfm.dashboard_active_symbol
        symbol_name = symbol.name
        cmp = dfm.sm.active_sessions[symbol_name].cmps[-1] if dfm.sm.active_sessions[symbol_name].cmps else 0
        dfm.sm.active_sessions[symbol_name].manually_create_new_pt(cmp=cmp, symbol=symbol)
    return 'New PT'


@app.callback(Output('button-increase-cmp', 'children'), Input('button-increase-cmp', 'n_clicks'))
def on_button_click(n):
    if n:
        symbol_name = dfm.dashboard_active_symbol.name
        # dfm.sm.active_sessions[symbol_name].market.update_fake_client_cmp(step=10.0, symbol_name=symbol_name)
    return '+ 10.0 €'


@app.callback(Output('button-decrease-cmp', 'children'), Input('button-decrease-cmp', 'n_clicks'))
def on_button_click(n):
    if n:
        symbol_name = dfm.dashboard_active_symbol.name
        # dfm.sm.active_sessions[symbol_name].market.update_fake_client_cmp(step=-10.0, symbol_name=symbol_name)
    return '- 10.0 €'


# ********** others **********
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


