# sc_fake_simulator_out.py

from typing import List
from sc_account_manager import Account


class FakeSimulatorOut:
    def __init__(self):
        pass

    def get_account(self, accounts: List[Account]):
        # return a dictionary with the actual balance of each account in (fake) Binance
        return {
            "makerCommission": 15,
            "takerCommission": 15,
            "buyerCommission": 0,
            "sellerCommission": 0,
            "canTrade": True,
            "canWithdraw": True,
            "canDeposit": True,
            "balances": [
                {"asset": "BTC", "free": str(accounts[0].free), "locked": str(accounts[0].locked)},
                {"asset": "EUR", "free": str(accounts[1].free), "locked": str(accounts[1].locked)},
                {"asset": "BNB", "free": str(accounts[2].free), "locked": str(accounts[2].locked)},
            ]
        }

    def get_asset_balance(self, asset: str, accounts: List[Account]) -> dict:
        if asset == 'BTC':
            free = accounts[0].free
            locked = accounts[0].locked
        elif asset == 'EUR':
            free = accounts[1].free
            locked = accounts[1].locked
        elif asset == 'BNB':
            free = accounts[2].free
            locked = accounts[2].locked
        else:
            raise Exception(f'wrong asset: {asset}')

        return {"asset": asset, "free": str(free), "locked": str(locked)}

    def get_symbol_info(self, symbol: str) -> dict:
        if symbol == 'BTCEUR':
            return {
                "symbol": symbol,
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
                        {'filterType': 'PERCENT_PRICE', 'multiplierUp': '5', 'multiplierDown': '0.2', 'avgPriceMins': 5},
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
        elif symbol == 'BNBEUR':
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
        else:
            raise Exception(f'wrong symbol {symbol}')


