# sc_session_manager.py
import pprint
from datetime import datetime
from typing import Optional, List, Dict
import logging
import os
import signal

from config_manager import ConfigManager

from sc_session import Session
# from sc_market import MarketApiOut
from sc_market_api_out import MarketAPIOut
from sc_market_sockets_in import MarketSocketsIn
from sc_account_manager import Account, AccountManager
from sc_isolated_manager import IsolatedOrdersManager
from sc_order import Order
from sc_symbol import Symbol, Asset
from sc_client_manager import ClientManager

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
        # self.market_api_out = MarketApiOut(client_manager=self.client_manager)
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

    def _update_global_profit(self, symbol: Symbol, consolidated: float, expected: float):
        # update
        if symbol.name in self.terminated_sessions.keys():
            self.terminated_sessions[symbol.name]['global_consolidated_profit'] += consolidated
            # subtraction because expected is calculated as an absolut value
            self.terminated_sessions[symbol.name]['global_expected_profit'] -= expected

        # log
        # log.info(f'********** global profit updated for symbol {symbol.name} **********')
        # log.info(f'consolidated: {consolidated:,.2f} expected: {expected:,.2f}')
        # log.info('*****************************************************************************')

    def _session_stopped_callback(self,
                                  symbol: Symbol,
                                  session_id: str,
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
        if self.all_symbols_session_count < 1000:
            self.active_sessions[symbol.name] = self.start_new_session(symbol=symbol)
        else:
            self.stop_global_session()
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
        session_id = f'SESSION{self.all_symbols_session_count + 1:03d}{symbol.name}{datetime.now().strftime("%m%d%H%M")}'
        session = Session(
            symbol=symbol,
            session_id=session_id,
            session_stopped_callback=self._session_stopped_callback,
            market=self.market_api_out,
            account_manager=self.am,
            check_isolated_callback=self._check_isolated_callback,
            placed_isolated_callback=self._placed_isolated_callback,
            try_to_get_liquidity_callback=self._try_to_get_liquidity_callback,
            get_liquidity_needed_callback=self._get_liquidity_needed_callback
        )

        # update counter for all symbols
        self.all_symbols_session_count += 1

        # update counter for current symbol
        self.session_count[symbol.name] += 1

        # info
        print(f'******** {symbol.name} NEW SESSION STARTED: {session_id}********')
        log.info(f'******** {symbol.name} NEW SESSION STARTED: {session_id}********')

        return session

    def stop_global_session(self):
        # stop market (binance sockets)
        self.client_manager.stop()
        log.critical("********** SESSION TERMINATED FROM BUTTON ********")

        # send SIGINT to own app (identical to CTRL-C)
        pid = os.getpid()
        os.kill(pid, signal.SIGINT)

        # exit
        raise Exception("********** SESSION TERMINATED, PRESS CTRL-C ********")

    # ********** session callbacks **********

    def _get_liquidity_needed_callback(self, asset: Asset) -> float:
        # if BUY => need for quote asset liquidity
        # if SELL => need for base asset liquidity
        # get orders
        liquidity_needed = 0.0
        pv = asset.pv()
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

    def _check_isolated_callback(self, symbol: Symbol, uid: str, order_price: float):
        # check the isolated orders and, in case an order from previous session have been traded,
        # return the variation in profit (consolidated & expected), otherwise return zero
        is_known_order, consolidated, expected = \
            self.iom.check_isolated_orders(uid=uid, traded_price=order_price)

        # update actual orders placed count, decrementing in one unit
        if is_known_order:
            if symbol.name in self.terminated_sessions.keys():
                self.terminated_sessions[symbol.name]['global_placed_pending_orders_count'] -= 1

        # update profit
        self._update_global_profit(symbol=symbol, consolidated=consolidated, expected=expected)

    def _placed_isolated_callback(self, order: Order):
        # once the order have been placed in Binance, it is appended to the list
        self.iom.isolated_orders.append(order)

    def _try_to_get_liquidity_callback(self, symbol: Symbol, asset: Asset, cmp: float):
        # called from session
        log.debug(f'{symbol.name} {asset.name()} trying to get liquidity')

        order = self.iom.try_to_get_asset_liquidity(
            asset=asset,
            cmp=cmp,
            max_loss=self.cm.get_max_allowed_loss_for_liquidity(symbol_name=symbol.name))

        if order:
            # place at MARKET price
            log.info(f'order to place at market price with loss: {order}')
            # sanity check
            if order.symbol.name != symbol.name:
                raise Exception(f'{symbol.name} and {order.symbol.name} have to be equals')
            else:
                self.active_sessions[symbol.name].place_isolated_order(order=order)

            # cancel in Binance the previously placed order
            self.market_api_out.cancel_orders([order])
