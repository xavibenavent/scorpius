# dash_callbacks.py

from dash.dependencies import Input, Output
from dashboard.dash_app import app
from dashboard.dash_aux import get_pending_html_table
from session.sc_helpers import QuitMode
from dashboard.sc_df_manager import DataframeManager
from binance import enums as k_binance
from datetime import datetime, timedelta
from basics.sc_perfect_trade import PerfectTradeStatus
from basics.sc_asset import Asset

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
        f'n: {dfm.sm.active_sessions[symbol_name].P_NET_QUOTE_BALANCE:,.2f} {quote_name}',\
        f'q: {dfm.sm.active_sessions[symbol_name].P_QUANTITY:,.4f} {base_name}',\
        f't: {dfm.sm.active_sessions[symbol_name].checks_manager.P_TARGET_TOTAL_NET_PROFIT:,.2f} {quote_name}',\
        f'({dfm.sm.active_sessions[symbol_name].checks_manager.P_MAX_NEGATIVE_PROFIT_ALLOWED:,.2f})'


# **********************************
# ********** Session data **********
# **********************************

# elapsed time
@app.callback(Output('session-count', 'children'),
              Output('session-cycle-count', 'children'),
              Input('update', 'n_intervals'))
def display_value(value):
    symbol_name = dfm.dashboard_active_symbol.name
    return f'#{dfm.sm.session_count[symbol_name]:03d}', \
           f'{timedelta(seconds=dfm.sm.active_sessions[symbol_name].cmp_count)}'


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
    session_orders = dfm.get_session_orders()

    symbol_name = dfm.dashboard_active_symbol.name
    active_session = dfm.sm.active_sessions[symbol_name]
    cmp = active_session.cmp
    gap = active_session.gap

    buy_gap_span, sell_gap_span = active_session.helpers.get_gap_span_from_list(orders=session_orders, cmp=cmp, gap=gap)
    total_gap_span = buy_gap_span + sell_gap_span
    buy_gap_depth, sell_gap_depth = active_session.helpers.get_gap_depth_from_list(orders=session_orders, cmp=cmp, gap=gap)
    total_gap_depth = buy_gap_depth + sell_gap_depth
    buy_gap_momentum, sell_gap_momentum = active_session.helpers.get_gap_momentum_from_list(orders=session_orders, cmp=cmp, gap=gap)
    total_gap_momentum = buy_gap_momentum + sell_gap_momentum
    return \
        f'{total_gap_span:.2f}', \
        f'{buy_gap_span:.2f}', \
        f'{sell_gap_span:.2f}', \
        f'{total_gap_depth:.2f}', \
        f'{buy_gap_depth:.2f}', \
        f'{sell_gap_depth:.2f}', \
        f'{total_gap_momentum:.2f}', \
        f'{buy_gap_momentum:.2f}', \
        f'{sell_gap_momentum:.2f}'


# ********** Session STOP profits **********
@app.callback(Output('actual-profit', 'children'),
              Output('stop-price-profit', 'children'),
              Output('ntc', 'children'),
              Output('time-to-next-try', 'children'),
              Output('is-active', 'children'),
              Input('update', 'n_intervals'))
def display_value(value):
    symbol = dfm.dashboard_active_symbol
    symbol_name = symbol.name
    cmp = dfm.sm.active_sessions[symbol_name].cmp
    qp = symbol.quote_asset().pv()
    base_ntc = dfm.sm.active_sessions[symbol_name].checks_manager.base_negative_try_count
    quote_ntc = dfm.sm.active_sessions[symbol_name].checks_manager.quote_negative_try_count
    
    cycles_count_for_inactivity = dfm.sm.active_sessions[symbol_name].cycles_count_for_inactivity
    cycles_to_new_pt = cycles_count_for_inactivity - dfm.sm.active_sessions[symbol_name].cycles_from_last_trade
    cycles_to_new_pt = 0.0 if cycles_to_new_pt < 0 else cycles_to_new_pt
    time_to_next_try = timedelta(seconds=cycles_to_new_pt)

    is_active = 'ON' if dfm.sm.active_sessions[symbol_name].is_active else 'OFF'

    return f'{dfm.sm.active_sessions[symbol_name].ptm.get_total_actual_profit_at_cmp(cmp=cmp):,.{qp}f}',\
           f'{dfm.sm.active_sessions[symbol_name].ptm.get_stop_price_profit(cmp=cmp):,.{qp}f}', \
           f'{base_ntc} - {quote_ntc}', \
           f'{time_to_next_try}', \
           f'{is_active}'


# @app.callback(Output('cycles-to-new-pt', 'children'), Input('update', 'n_intervals'))
# def display_value(value):
#     symbol_name = dfm.dashboard_active_symbol.name
#     cycles_count_for_inactivity = dfm.sm.active_sessions[symbol_name].cycles_count_for_inactivity
#     cycles_to_new_pt = cycles_count_for_inactivity - dfm.sm.active_sessions[symbol_name].cycles_from_last_trade
#     time_to_new_pt = timedelta(seconds=cycles_to_new_pt)
#     return f'({cycles_count_for_inactivity})  {time_to_new_pt}'



# **********************************
# ********** Global data **********
# **********************************


# ********** Global elapsed time **********
@app.callback(Output('global-cycle-count', 'children'), Input('update', 'n_intervals'))
def display_value(value):
    symbol_name = dfm.dashboard_active_symbol.name
    global_cmp = dfm.sm.terminated_sessions[symbol_name]["global_cmp_count"]
    session_cmp = dfm.sm.active_sessions[symbol_name].cmp_count
    return f'{timedelta(seconds=global_cmp + session_cmp)}'


# isolated orders info
@app.callback(
    Output('isol-orders-placed', 'children'),
    Output('isol-orders-pending', 'children'),
    Output('isol-orders-pending-buy', 'children'),
    Output('isol-orders-pending-sell', 'children'),
    Input('update', 'n_intervals'))
def display_value(value):
    symbol_name = dfm.dashboard_active_symbol.name

    placed = dfm.sm.terminated_sessions[symbol_name]['global_placed_orders_count_at_price']
    sell = len(
        [order for order in dfm.sm.iom.isolated_orders
         if order.k_side == k_binance.SIDE_SELL and order.symbol.name == symbol_name])
    buy = len(
        [order for order in dfm.sm.iom.isolated_orders
         if order.k_side == k_binance.SIDE_BUY and order.symbol.name == symbol_name])
    pending = buy + sell
    return placed, pending, buy, sell


# Global span, depth, momentum & TBD data
@app.callback(Output('is-span', 'children'),
              Output('is-span-buy', 'children'),
              Output('is-span-sell', 'children'),
              Output('is-depth', 'children'),
              Output('is-depth-buy', 'children'),
              Output('is-depth-sell', 'children'),
              Output('is-mtm', 'children'),
              Output('is-mtm-buy', 'children'),
              Output('is-mtm-sell', 'children'),
              Input('update', 'n_intervals'))
def display_value(value):
    all_orders = dfm.get_all_orders()

    symbol_name = dfm.dashboard_active_symbol.name
    active_session = dfm.sm.active_sessions[symbol_name]
    cmp = active_session.cmp
    gap = active_session.gap

    buy_gap_span, sell_gap_span = active_session.helpers.get_gap_span_from_list(orders=all_orders, cmp=cmp, gap=gap)
    total_gap_span = buy_gap_span + sell_gap_span
    buy_gap_depth, sell_gap_depth = active_session.helpers.get_gap_depth_from_list(orders=all_orders, cmp=cmp, gap=gap)
    total_gap_depth = buy_gap_depth + sell_gap_depth
    buy_gap_momentum, sell_gap_momentum = \
        active_session.helpers.get_gap_momentum_from_list(orders=all_orders, cmp=cmp, gap=gap)
    total_gap_momentum = buy_gap_momentum + sell_gap_momentum
    return \
        f'{total_gap_span:.2f}',\
        f'{buy_gap_span:.2f}',\
        f'{sell_gap_span:.2f}', \
        f'{total_gap_depth:.2f}', \
        f'{buy_gap_depth:.2f}', \
        f'{sell_gap_depth:.2f}', \
        f'{total_gap_momentum:.2f}', \
        f'{buy_gap_momentum:.2f}', \
        f'{sell_gap_momentum:.2f}'


# ********** Global STOP profits **********
@app.callback(Output('consolidated-profit', 'children'),
              Output('expected-profit-at-cmp', 'children'),
              Output('expected-profit', 'children'),
              Output('actions-info', 'children'),
              Output('actions-rate', 'children'),
              Output('canceled-count', 'children'),
              Input('update', 'n_intervals'))
def display_value(value):
    symbol = dfm.dashboard_active_symbol
    symbol_name = symbol.name
    cmp = dfm.sm.active_sessions[symbol_name].cmp  # s[-1]
    qp = symbol.quote_asset().pv()
    # coin_symbol = symbol.quote_asset().name()
    # called the method in session to check buy_count == sell_count
    consolidated = dfm.sm.terminated_sessions[symbol_name]['global_consolidated_profit']
    expected = dfm.sm.terminated_sessions[symbol_name]['global_expected_profit']
    expected_at_cmp = dfm.sm.iom.get_expected_profit_at_cmp(cmp=cmp, symbol_name=symbol_name)
    buy_actions_count, sell_actions_count, actions_balance = \
        dfm.sm.active_sessions[symbol_name].checks_manager.get_actions_balance()
    buy_actions_rate = consolidated / (buy_actions_count +1)
    sell_actions_rate = consolidated / (sell_actions_count +1)
    canceled_buy_orders = [order for order in dfm.sm.iom.canceled_orders if order.k_side == k_binance.SIDE_BUY]
    canceled_sell_orders = [order for order in dfm.sm.iom.canceled_orders if order.k_side == k_binance.SIDE_SELL]
    return f'{consolidated:,.{qp}f}',\
           f'{expected_at_cmp:,.{qp}f}',\
           f'{expected:,.{qp}f}', \
           f'{buy_actions_count}/{sell_actions_count} {actions_balance:,.2f}', \
           f'{buy_actions_rate:,.0f} / {sell_actions_rate:,.0f}', \
           f'{len(canceled_buy_orders)} / {len(canceled_sell_orders)}'


# ********** PT count / traded orders count **********
# @app.callback(Output('trade-info', 'children'), Input('update', 'n_intervals'))
# def display_value(value):
#     symbol_name = dfm.dashboard_active_symbol.name
#     pt_count = len(dfm.sm.active_sessions[symbol_name].ptm.perfect_trades)
#     buy_count = dfm.sm.active_sessions[symbol_name].buy_count
#     sell_count = dfm.sm.active_sessions[symbol_name].sell_count
#     return f'pt: {pt_count}   b: {buy_count}   s: {sell_count}'




# @app.callback(Output('short-prediction', 'children'),
#               Output('long-prediction', 'children'),
#               Input('update', 'n_intervals'))
# def display_value(value):
#     symbol_name = dfm.dashboard_active_symbol.name
#     session = dfm.sm.active_sessions[symbol_name]
#     short_prediction = session.strategy_manager.get_tendency(session.cmp_pattern_short) - session.cmp
#     long_prediction = session.strategy_manager.get_tendency(session.cmp_pattern_long) - session.cmp
#     return f'short: {short_prediction:,.0f}', f'long: {long_prediction:,.0f}'


# @app.callback(Output('accounts-info', 'children'), Input('update', 'n_intervals'))
# def display_value(value):
#     accounts_info = [f'{account.name}: {account.free:,.2f} ' for account in dfm.sm.am.accounts.values()]
#     accounts_info_s = ' '.join(map(str, accounts_info))
#     return accounts_info_s


# ********** symbol & accounts data **********
@app.callback(
    Output('symbol', 'children'),
    Output('cmp-max', 'children'),
    Output('cmp', 'children'),
    Output('cmp-min', 'children'),
    Output('base-asset', 'children'),
    Output('base-asset-locked', 'children'),
    Output('base-asset-alive', 'children'),
    Output('base-asset-free', 'children'),
    Output('base-asset-total', 'children'),
    Output('quote-asset', 'children'),
    Output('quote-asset-locked', 'children'),
    Output('quote-asset-alive', 'children'),
    Output('quote-asset-free', 'children'),
    Output('quote-asset-total', 'children'),
    Output('bnb-locked', 'children'),
    Output('bnb-alive', 'children'),
    Output('bnb-free', 'children'),
    Output('bnb-total', 'children'),
    Input('update', 'n_intervals')
)
def display_value(value):
    symbol = dfm.dashboard_active_symbol
    symbol_name = symbol.name
    # am = dfm.sm.active_sessions[symbol_name].am
    am = dfm.sm.am
    base_account = am.get_account(symbol.base_asset().name())
    quote_account = am.get_account(symbol.quote_asset().name())
    bnb_account = am.get_account('BNB')
    quote_pv = symbol.quote_asset().pv()

    base_alive = dfm.sm.get_liquidity_for_alive_orders(asset=symbol.base_asset())
    quote_alive = dfm.sm.get_liquidity_for_alive_orders(asset=symbol.quote_asset())
    bnb_alive = dfm.sm.get_liquidity_for_alive_orders(asset=Asset(name='BNB', pv=6))
    # bnb_alive = 1.0

    return \
        symbol_name, \
        f'{dfm.sm.active_sessions[symbol_name].max_cmp:,.{quote_pv}f}', \
        f'{dfm.sm.active_sessions[symbol_name].cmp:,.{quote_pv}f}', \
        f'{dfm.sm.active_sessions[symbol_name].min_cmp:,.{quote_pv}f}', \
        symbol.base_asset().name(),\
        f'{base_account.locked:,.{symbol.base_asset().pv()}f}', \
        f'{base_alive:,.{symbol.base_asset().pv()}f}', \
        f'{base_account.free - base_alive:,.{symbol.base_asset().pv()}f}', \
        f'{base_account.get_total():,.{symbol.base_asset().pv()}f}', \
        symbol.quote_asset().name(), \
        f'{quote_account.locked:,.{symbol.quote_asset().pv()}f}', \
        f'{quote_alive:,.{symbol.quote_asset().pv()}f}', \
        f'{quote_account.free - quote_alive:,.{symbol.quote_asset().pv()}f}',\
        f'{quote_account.get_total():,.{symbol.quote_asset().pv()}f}',\
        f'{bnb_account.locked:,.6f}',\
        f'{bnb_alive:,.6f}', \
        f'{bnb_account.free - bnb_alive:,.6f}', \
        f'{bnb_account.get_total():,.6f}'


# ********** alert message **********
@app.callback(Output('alert-msg', 'children'),
              Input('update', 'n_intervals'))
def display_value(value):
    symbol = dfm.dashboard_active_symbol

    # check bnb liquidity and raise ALERT
    bnb_liquidity = dfm.sm.active_sessions[symbol.name].am.get_account('BNB').free
    if bnb_liquidity < 1.0:
        return f'BNB LIQUIDITY ALERT {bnb_liquidity:,.6f}'
    else:
        return ''


# ********** symbol selection buttons *********
@app.callback(Output('button-symbols', 'children'),
              Input('button-symbols', 'n_clicks'),
              )
def on_button_click(n):
    # set BTCEUR as active symbol if button pressed
    current_symbol_name = dfm.dashboard_active_symbol.name
    if n is not None:
        next_symbol = dfm.get_next_symbol(symbol_name=current_symbol_name)
        dfm.set_dashboard_active_symbol(symbol_name=next_symbol)
        return next_symbol
    else:
        return current_symbol_name


# Stop buttons
@app.callback(Output('button-stop-cmp', 'children'), Input('button-stop-cmp', 'n_clicks'))
def on_button_click(n):
    if n is not None:
        symbol = dfm.dashboard_active_symbol
        symbol_name = symbol.name
        session = dfm.sm.active_sessions[symbol_name]
        session.helpers.quit_particular_session(
            quit_mode=QuitMode.TRADE_ALL_PENDING,
            session_id=session.session_id,
            symbol=session.symbol,
            cmp=session.cmp,
            iom=session.iom,
            cmp_count=session.cmp_count)

    return 'STOP-CMP'


@app.callback(Output('button-stop-price', 'children'), Input('button-stop-price', 'n_clicks'))
def on_button_click(n):
    if n is not None:
        symbol = dfm.dashboard_active_symbol
        symbol_name = symbol.name
        session = dfm.sm.active_sessions[symbol_name]
        session.helpers.quit_particular_session(
            quit_mode=QuitMode.PLACE_ALL_PENDING,
            session_id=session.session_id,
            symbol=session.symbol,
            cmp=session.cmp,
            iom=session.iom,
            cmp_count=session.cmp_count)

    return 'STOP-PRICE'


@app.callback(Output('button-stop-cancel', 'children'), Input('button-stop-cancel', 'n_clicks'))
def on_button_click(n):
    if n is not None:
        symbol = dfm.dashboard_active_symbol
        symbol_name = symbol.name
        session = dfm.sm.active_sessions[symbol_name]
        session.helpers.quit_particular_session(
            quit_mode=QuitMode.CANCEL_ALL,
            session_id=session.session_id,
            symbol=session.symbol,
            cmp=session.cmp,
            iom=session.iom,
            cmp_count=session.cmp_count)
    return 'STOP-CANCEL'


@app.callback(Output('button-reboot-global-session', 'children'), Input('button-reboot-global-session', 'n_clicks'))
def on_button_click(n):
    if n is not None:
        # as first step, perform STOP-PRICE actions
        symbol = dfm.dashboard_active_symbol
        symbol_name = symbol.name
        for session in dfm.sm.active_sessions.values():
            # session = dfm.sm.active_sessions[symbol_name]
            session.helpers.quit_particular_session(
                quit_mode=QuitMode.PLACE_ALL_PENDING,
                session_id=session.session_id,
                symbol=session.symbol,
                cmp=session.cmp,
                iom=session.iom,
                cmp_count=session.cmp_count)

        # finish app ans it will cause a gunicorn workers reboot (reset-like app)
        dfm.sm.reboot_global_session()
    return 'REBOOT-SESSION'


@app.callback(Output('button-new-pt', 'children'), Input('button-new-pt', 'n_clicks'))
def on_button_click(n):
    if n:
        symbol = dfm.dashboard_active_symbol
        symbol_name = symbol.name
        dfm.sm.active_sessions[symbol_name].manually_create_new_pt()
    return 'NEW-PT'


@app.callback(Output('button-increase-cmp', 'children'), Input('button-increase-cmp', 'n_clicks'))
def on_button_click(n):
    if n:
        symbol_name = dfm.dashboard_active_symbol.name
        dfm.sm.client_manager.on_button_step(symbol_name=symbol_name, step=10.0)
    return '+ 10.0 €'


@app.callback(Output('button-decrease-cmp', 'children'), Input('button-decrease-cmp', 'n_clicks'))
def on_button_click(n):
    if n:
        symbol_name = dfm.dashboard_active_symbol.name
        dfm.sm.client_manager.on_button_step(symbol_name=symbol_name, step=-10.0)
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
    df_pending = df1[df1.status.isin(['monitor', 'active', 'cmp', 'to_be_traded', 'canceled'])]
    qp = dfm.dashboard_active_symbol.quote_asset().pv()
    df_pending['price'] = df_pending['price'].map(f'{{:,.{qp}f}}'.format)  # two {{ }} to escape { in f-string
    df_pending['total'] = df_pending['total'].map(f'{{:,.{qp}f}}'.format)

    return get_pending_html_table(df=df_pending[['pt_id', 'name', 'price', 'amount', 'total', 'status']])
