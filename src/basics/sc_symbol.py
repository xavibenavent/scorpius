# sc_symbol.py

from typing import Dict
from basics.sc_asset import Asset


class Symbol:
    def __init__(self, name: str, base_asset: Asset, quote_asset: Asset, symbol_info: Dict, config_data: Dict):
        self.name = name.upper()
        self._base_asset = base_asset
        self._quote_asset = quote_asset
        self.symbol_info = symbol_info
        self.config_data = config_data

        filters = {}  # create dictionary from list of filters
        for f in symbol_info['filters']:
            filters[f['filterType']] = f
        self._filters = filters

    def get_name(self) -> str:
        return self._base_asset.name() + self._quote_asset.name()

    def base_asset(self) -> Asset:
        # related to quantity (BTC in BTCEUR)
        return self._base_asset

    def quote_asset(self) -> Asset:
        # related to price (EUR in BTCEUR)
        return self._quote_asset

    def base_tp(self) -> int:
        return self.symbol_info['baseAssetPrecision']

    def quote_tp(self) -> int:
        return self.symbol_info['quoteAssetPrecision']

    def filters(self) -> Dict:
        return self._filters

    def get_symbol_filter(self, filter_type: str) -> Dict:
        return self._filters[filter_type]

    def _is_price_filter_ok(self, price: float) -> bool:
        # check the three conditions for PRICE are matched (important before placing a LIMIT order)
        # get the filter from the dictionary
        price_filter = self.get_symbol_filter(filter_type='PRICE_FILTER')

        # get reference values from filter
        min_price = float(price_filter['minPrice'])
        max_price = float(price_filter['maxPrice'])
        # tick_size = float(price_filter['tickSize'])

        # this condition is not taken into consideration because of float behaviour
        # that does not give 0 when the condition is matched
        # added a round() in order creation to guarantee it
        # tick_size_condition = round((price - min_price) % tick_size, 0) == 0

        # check the three conditions are matched
        conditions = min_price <= price <= max_price  # and tick_size_condition
        return True if conditions else False

    def _is_lot_size_filter_ok(self, qty: float) -> bool:
        # check the three conditions for QUANTITY are matched (important before placing an order)
        # get the filter from the dictionary
        lot_size_filter = self.get_symbol_filter(filter_type='LOT_SIZE')

        # get reference values from filter
        min_qty = float(lot_size_filter['minQty'])
        max_qty = float(lot_size_filter['maxQty'])
        # step_size = float(lot_size_filter['stepSize'])

        # this condition is not taken into consideration because of float behaviour
        # that does not give 0 when the condition is matched
        # added a round() in order creation to guarantee it
        # step_size_condition = round((qty - min_qty) % step_size == 0, 0)

        # check the three conditions are matched
        conditions = min_qty <= qty <= max_qty  # and step_size_condition
        return True if conditions else False

    def _is_min_notional_ok(self, notional_value: float) -> bool:  # notional_value = price * qty
        # check the notional value is above the minimum required
        min_notional_filter = self.get_symbol_filter(filter_type='MIN_NOTIONAL')
        min_notional = float(min_notional_filter['minNotional'])
        condition = notional_value > min_notional
        return True if condition else False

    def are_filters_ok(self, price: float, qty: float) -> bool:
        # return True if the three filters are passed
        notional_value = price * qty

        if self._is_price_filter_ok(price=price) \
                and self._is_lot_size_filter_ok(qty=qty) \
                and self._is_min_notional_ok(notional_value=notional_value):
            return True
        else:
            raise Exception()
            # return False
