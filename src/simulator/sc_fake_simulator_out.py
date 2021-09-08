# sc_fake_simulator_out.py

from typing import List, Dict
from sc_account_manager import Account, AccountManager
from config_manager import ConfigManager


class FakeSimulatorOut:
    def __init__(self, config_manager: ConfigManager):
        self.cm = config_manager

    def get_account(self) -> Dict:
        # get values from config.ini
        simulator_data = self.cm.get_simulator_global_data()
        initial_btc = float(simulator_data['initial_btc'])
        initial_eur = float(simulator_data['initial_eur'])
        initial_bnb = float(simulator_data['initial_bnb'])
        initial_eth = float(simulator_data['initial_eth'])

        return {
            'makerCommission': 10,
            'takerCommission': 10,
            'buyerCommission': 0,
            'sellerCommission': 0,
            'canTrade': True,
            'canWithdraw': True,
            'canDeposit': True,
            'updateTime': 1630337521166,
            'accountType': 'SPOT',
            'balances': [
                {'asset': 'BTC', 'free': initial_btc, 'locked': '0.00000000'},
                {'asset': 'BNB', 'free': initial_bnb, 'locked': '0.00000000'},
                {'asset': 'ETH', 'free': initial_eth, 'locked': '0.00000000'},
                {'asset': 'EUR', 'free': initial_eur, 'locked': '0.00000000'},
            ],
            'permissions': ['SPOT']
        }

    def get_asset_balance(self, asset: str, account_manager: AccountManager) -> dict:
        account = account_manager.get_account(name=asset)
        if account:
            return {"asset": asset, "free": account.free, "locked": account.locked}
        else:
            raise Exception(f'wrong asset: {asset}')


    def get_symbol_info(self, symbol_name: str) -> dict:
        if symbol_name == 'BTCEUR':
            return {
                "symbol": symbol_name,
                "status": "TRADING",
                "baseAsset": "BTC",
                "baseAssetPrecision": 8,
                "quoteAsset": "EUR",
                "quoteAssetPrecision": 8,
                "orderTypes": ["LIMIT", "MARKET"],
                "icebergAllowed": True,
                'filters':
                    [
                        {'filterType': 'PRICE_FILTER', 'minPrice': '0.01000000', 'maxPrice': '1000000.00000000',
                         'tickSize': '0.01000000'},
                        {'filterType': 'PERCENT_PRICE', 'multiplierUp': '5', 'multiplierDown': '0.2',
                         'avgPriceMins': 5},
                        {'filterType': 'LOT_SIZE', 'minQty': '0.00000100', 'maxQty': '9000.00000000',
                         'stepSize': '0.00000100'},
                        {'filterType': 'MIN_NOTIONAL', 'minNotional': '10.00000000', 'applyToMarket': True,
                         'avgPriceMins': 5}, {'filterType': 'ICEBERG_PARTS', 'limit': 10},
                        {'filterType': 'MARKET_LOT_SIZE', 'minQty': '0.00000000', 'maxQty': '53.77006166',
                         'stepSize': '0.00000000'}, {'filterType': 'MAX_NUM_ORDERS', 'maxNumOrders': 200},
                        {'filterType': 'MAX_NUM_ALGO_ORDERS', 'maxNumAlgoOrders': 5}
                    ],
                'permissions': ['SPOT', 'MARGIN']
            }
        elif symbol_name == 'BNBEUR':
            return {
                'symbol': 'BNBEUR',
                'status': 'TRADING',
                'baseAsset': 'BNB',
                'baseAssetPrecision': 3,
                'quoteAsset': 'EUR',
                'quotePrecision': 8,
                'quoteAssetPrecision': 1,
                'baseCommissionPrecision': 8,
                'quoteCommissionPrecision': 8,
                'orderTypes': ['LIMIT', 'LIMIT_MAKER', 'MARKET', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT_LIMIT'],
                'icebergAllowed': True,
                'ocoAllowed': True,
                'quoteOrderQtyMarketAllowed': True,
                'isSpotTradingAllowed': True,
                'isMarginTradingAllowed': False,
                'filters': [
                    {
                        'filterType': 'PRICE_FILTER',
                        'minPrice': '0.10000000',
                        'maxPrice': '10000.00000000',
                        'tickSize': '0.10000000'
                    },
                    {
                        'filterType': 'PERCENT_PRICE',
                        'multiplierUp': '5',
                        'multiplierDown': '0.2',
                        'avgPriceMins': 5
                    },
                    {
                        'filterType': 'LOT_SIZE',
                        'minQty': '0.00100000',
                        'maxQty': '9222449.00000000',
                        'stepSize': '0.00100000'
                    },
                    {
                        'filterType': 'MIN_NOTIONAL',
                        'minNotional': '10.00000000',
                        'applyToMarket': True,
                        'avgPriceMins': 5
                    },
                    {
                        'filterType': 'ICEBERG_PARTS',
                        'limit': 10},
                    {
                        'filterType': 'MARKET_LOT_SIZE',
                        'minQty': '0.00000000',
                        'maxQty': '2350.34381451',
                        'stepSize': '0.00000000'
                    },
                    {
                        'filterType': 'MAX_NUM_ORDERS',
                        'maxNumOrders': 200},
                    {
                        'filterType': 'MAX_NUM_ALGO_ORDERS',
                        'maxNumAlgoOrders': 5
                    }
                ],
                'permissions': ['SPOT']
            }
        elif symbol_name == 'ETHBTC':
            return {
                'symbol': 'ETHBTC',
                'status': 'TRADING',
                'baseAsset': 'ETH', 'baseAssetPrecision': 8,
                'quoteAsset': 'BTC', 'quotePrecision': 8,
                'quoteAssetPrecision': 8,
                'baseCommissionPrecision': 8,
                'quoteCommissionPrecision': 8,
                'orderTypes': ['LIMIT', 'LIMIT_MAKER', 'MARKET', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT_LIMIT'],
                'icebergAllowed': True,
                'ocoAllowed': True,
                'quoteOrderQtyMarketAllowed': True,
                'isSpotTradingAllowed': True,
                'isMarginTradingAllowed': True,
                'filters': [
                    {'filterType': 'PRICE_FILTER', 'minPrice': '0.00000100', 'maxPrice': '922327.00000000', 'tickSize': '0.00000100'},
                    {'filterType': 'PERCENT_PRICE', 'multiplierUp': '5', 'multiplierDown': '0.2', 'avgPriceMins': 5},
                    {'filterType': 'LOT_SIZE', 'minQty': '0.00010000', 'maxQty': '100000.00000000', 'stepSize': '0.00010000'},
                    {'filterType': 'MIN_NOTIONAL', 'minNotional': '0.00010000', 'applyToMarket': True, 'avgPriceMins': 5},
                    {'filterType': 'ICEBERG_PARTS', 'limit': 10},
                    {'filterType': 'MARKET_LOT_SIZE', 'minQty': '0.00000000', 'maxQty': '746.43672750', 'stepSize': '0.00000000'},
                    {'filterType': 'MAX_NUM_ORDERS', 'maxNumOrders': 200},
                    {'filterType': 'MAX_NUM_ALGO_ORDERS', 'maxNumAlgoOrders': 5}
                ],
                'permissions': ['SPOT', 'MARGIN']
            }
        else:
            raise Exception(f'wrong symbol {symbol_name}')
