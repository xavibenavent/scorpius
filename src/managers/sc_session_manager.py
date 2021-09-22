# sc_session_manager.py
from datetime import datetime
from typing import Optional, List, Dict
import logging
import os
import signal

from managers.config_manager import ConfigManager

from session.sc_session import Session
from market.sc_market_api_out import MarketAPIOut
from market.sc_market_sockets_in import MarketSocketsIn
from managers.sc_account_manager import Account, AccountManager
from managers.sc_isolated_manager import IsolatedOrdersManager
from basics.sc_symbol import Symbol, Asset
from basics.sc_order import Order, OrderStatus
from basics.sc_perfect_trade import PerfectTrade
from managers.sc_client_manager import ClientManager

log = logging.getLogger('log')


class SessionManager:
    def __init__(self):
        print('session manager')

        # global sessions info
        self.all_symbols_session_count = 0

        # MANAGERS
        self.iom = IsolatedOrdersManager()
        self.cm = ConfigManager(config_file='config_new.ini')

        self.market_sockets_in = MarketSocketsIn(
            order_traded_callback=self._order_traded_callback,
            account_balance_callback=self._account_balance_callback,
            symbol_ticker_callback=self._symbol_ticker_callback
        )

        self.client_manager = ClientManager(
            symbol_ticker_callback=self.market_sockets_in.binance_symbol_ticker_callback,
            user_callback=self.market_sockets_in.binance_user_socket_callback
        )
        self.market_api_out = MarketAPIOut(client=self.client_manager.client,
                                           hot_reconnect_callback=self.client_manager.hot_reconnect)

        # session will be started within start_session method
        self.active_sessions: Dict[str, Optional[Session]] = {}
        self.terminated_sessions: Dict[str, Dict] = {}
        self.session_count: Dict[str, int] = {}

        # DATA: get list of symbols info from config.ini & market
        self.symbols = self._get_symbols()
        [log.info(symbol.name) for symbol in self.symbols]

        # get initial accounts to create the balance manager (all own accounts managed in Binance)
        accounts = self.market_api_out.get_account_info()
        self.am = AccountManager(accounts=accounts)

        # start first sessions
        for symbol in self.symbols:
            self._init_global_data(symbol=symbol)
            self.session_count[symbol.name] = 0
            self.active_sessions[symbol.name] = self.start_new_session(symbol=symbol)

        self.client_manager.start_sockets()

        # get orders placed in previous app runs and append them to previous runs orders list
        msg = self.market_api_out.get_open_orders()
        for order in msg:
            symbol_name = order['symbol']
            # get symbol by name
            symbols = [symbol for symbol in self.symbols if symbol.name == symbol_name]
            # append only orders from symbols managed by session manager
            if len(symbols) > 0:
                symbol = symbols[0]

                open_order = Order(
                    symbol=symbol,
                    order_id=order['clientOrderId'],
                    k_side=order['side'],
                    price=float(order['price']),
                    amount=float(order['origQty']),
                    status=OrderStatus.TO_BE_TRADED,
                    binance_id=order['orderId'],
                    name='b1' if order['side'] == 'BUY' else 's1'
                )
                open_order.pt = PerfectTrade(pt_id='*', orders=[open_order, open_order])
                self.iom.previous_runs_orders.append(open_order)

    def _get_symbols(self) -> List[Symbol]:
        # list to return
        symbols: List[Symbol] = []

        # cm = ConfigManager(config_file='config_new.ini')
        # get the list of symbol names in config.ini
        symbols_name = self.cm.get_symbol_names()

        for symbol_name in symbols_name:
            # get filters from Binance API
            symbol_filters = self.market_api_out.get_all_symbol_info(symbol_name=symbol_name)
            # symbol_filters = self.market_api_out.get_symbol_info(symbol_name=symbol_name)

            # get session data from config.ini
            symbol_config_data = self.cm.get_symbol_data(symbol_name=symbol_name)

            # fix Binance mistake in EUR precision by reading the values from config.ini
            symbol_filters['baseAssetPrecision'] = int(symbol_config_data['base_pt'])
            symbol_filters['quoteAssetPrecision'] = int(symbol_config_data['quote_pt'])

            # set symbol to pass at sessions start
            symbol = Symbol(
                name=symbol_name,
                base_asset=Asset(
                    name=symbol_filters.get('baseAsset'),
                    pv=int(symbol_config_data['base_pv'])
                ),
                quote_asset=Asset(
                    name=symbol_filters.get('quoteAsset'),
                    pv=int(symbol_config_data['quote_pv'])
                ),
                symbol_info=symbol_filters,
                config_data=symbol_config_data
            )
            # update list
            symbols.append(symbol)
        return symbols

    # ********** market callbacks **********
    def _account_balance_callback(self, accounts: List[Account]) -> None:
        self.am.update_current_accounts(received_accounts=accounts)

    def _symbol_ticker_callback(self, symbol_name: str, cmp: float) -> None:
        # depending on symbol name, send the last price to the right session
        self.active_sessions[symbol_name].symbol_ticker_callback(cmp=cmp)

    def _order_traded_callback(self, symbol_name: str, uid: str, price: float, bnb_commission: float) -> None:
        # depending on symbol name, send the traded order data to the right session
        self.active_sessions[symbol_name].order_traded_callback(
            uid=uid,
            order_price=price,
            bnb_commission=bnb_commission)

    def _session_stopped_callback(self,
                                  symbol: Symbol,
                                  is_session_fully_consolidated: bool,
                                  consolidated_profit: float,
                                  expected_profit: float,
                                  cmp_count: int,
                                  market_orders_count_at_cmp: int,
                                  placed_orders_count_at_price: int
                                  ) -> None:

        # update terminated sessions or create if first session terminated
        if symbol.name in self.terminated_sessions.keys():
            self.terminated_sessions[symbol.name]['global_consolidated_session_count'] += \
                1 if is_session_fully_consolidated else 0
            self.terminated_sessions[symbol.name]['global_expected_session_count'] += \
                1 if not is_session_fully_consolidated else 0
            self.terminated_sessions[symbol.name]['global_cmp_count'] += cmp_count
            self.terminated_sessions[symbol.name]['global_consolidated_profit'] += consolidated_profit
            self.terminated_sessions[symbol.name]['global_expected_profit'] += expected_profit
            self.terminated_sessions[symbol.name]['global_market_orders_count_at_cmp'] += market_orders_count_at_cmp
            self.terminated_sessions[symbol.name]['global_placed_orders_count_at_price'] += placed_orders_count_at_price
            self.terminated_sessions[symbol.name]['global_placed_pending_orders_count'] += placed_orders_count_at_price
        else:
            raise Exception(f'global data for {symbol.name} should already exist')

        # check for session manager end
        if self.all_symbols_session_count < 100_000:
            self.active_sessions[symbol.name] = self.start_new_session(symbol=symbol)
        else:
            self.reboot_global_session()
            # self.market.stop()
            # raise Exception('********** GLOBAL SESSION MANAGER FINISHED **********')

    def _init_global_data(self, symbol: Symbol):
        self.terminated_sessions[symbol.name] = {}
        self.terminated_sessions[symbol.name]['global_consolidated_session_count'] = 0
        self.terminated_sessions[symbol.name]['global_expected_session_count'] = 0
        self.terminated_sessions[symbol.name]['global_cmp_count'] = 0
        self.terminated_sessions[symbol.name]['global_consolidated_profit'] = 0.0
        self.terminated_sessions[symbol.name]['global_expected_profit'] = 0.0
        self.terminated_sessions[symbol.name]['global_market_orders_count_at_cmp'] = 0
        self.terminated_sessions[symbol.name]['global_placed_orders_count_at_price'] = 0
        self.terminated_sessions[symbol.name]['global_placed_pending_orders_count'] = 0

    def start_new_session(self, symbol: Symbol) -> Session:
        session_id = f'SESSION{self.all_symbols_session_count + 1:03d}' \
                     f'{symbol.name}{datetime.now().strftime("%m%d%H%M")}'
        session = Session(
            symbol=symbol,
            session_id=session_id,
            isolated_orders_manager=self.iom,
            session_stopped_callback=self._session_stopped_callback,
            market=self.market_api_out,
            account_manager=self.am,
            isolated_order_traded_callback=self._isolated_order_traded_callback,
            get_liquidity_needed_callback=self._get_liquidity_needed_callback,
        )

        # update counter for all symbols
        self.all_symbols_session_count += 1

        # update counter for current symbol
        self.session_count[symbol.name] += 1

        # info
        print(f'******** {symbol.name} NEW SESSION STARTED: {session_id}********')
        log.info(f'******** {symbol.name} NEW SESSION STARTED: {session_id}********')

        return session

    def reboot_global_session(self):
        # stop market (binance sockets)
        self.client_manager.stop()
        log.critical("********** SESSION TERMINATED FROM BUTTON ********")

        # send SIGINT to own app (identical to CTRL-C)
        pid = os.getpid()
        os.kill(pid, signal.SIGINT)

        # exit
        raise Exception("********** SESSION TERMINATED, PRESS CTRL-C ********")

    def get_liquidity_for_alive_orders(self, asset: Asset) -> float:
        return self._get_liquidity_needed_callback(asset=asset)

    # ********** session callbacks **********

    def _get_liquidity_needed_callback(self, asset: Asset) -> float:
        # if BUY => need for quote asset liquidity
        # if SELL => need for base asset liquidity
        # get orders
        liquidity_needed = 0.0
        for session in self.active_sessions.values():
            quote_asset_needed = 0.0
            base_asset_needed = 0.0
            # check whether the symbol session includes the asset
            if session.symbol.quote_asset().name() == asset.name():
                quote_asset_needed, _ = session.ptm.get_symbol_liquidity_needed()

            if session.symbol.base_asset().name() == asset.name():
                _, base_asset_needed = session.ptm.get_symbol_liquidity_needed()

            # get total for this session (only one of the two values will be > 0)
            liquidity_needed += quote_asset_needed + base_asset_needed
        return liquidity_needed

    def _isolated_order_traded_callback(self, symbol: Symbol, consolidated: float, expected: float):
        # update actual orders placed count, decrementing in one unit
        if symbol.name in self.terminated_sessions.keys():
            self.terminated_sessions[symbol.name]['global_placed_pending_orders_count'] -= 1

        # update global profit
        if symbol.name in self.terminated_sessions.keys():
            self.terminated_sessions[symbol.name]['global_consolidated_profit'] += consolidated
            # subtraction because expected is calculated as an absolut value
            self.terminated_sessions[symbol.name]['global_expected_profit'] -= expected
