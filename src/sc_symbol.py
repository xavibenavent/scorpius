# sc_symbol.py

from typing import Dict


class Asset:
    def __init__(self,
                 name: str,
                 precision_for_transaction: int,
                 precision_for_visualization: int
                 ):
        self._name = name.upper()
        self._precision_for_transaction = precision_for_transaction
        self._precision_for_visualization = precision_for_visualization

    def get_name(self) -> str:
        return self._name

    def get_precision_for_visualization(self) -> int:
        return self._precision_for_visualization

    def get_precision_for_transaction(self) -> int:
        return self._precision_for_transaction


class Symbol:
    def __init__(self, name: str, base_asset: Asset, quote_asset: Asset, filters: Dict):
        self.name = name.upper()
        self._base_asset = base_asset
        self._quote_asset = quote_asset
        self.filters = filters

    def get_name(self) -> str:
        return self._base_asset.get_name() + self._quote_asset.get_name()

    def get_base_asset(self) -> Asset:
        # related to quantity (BTC in BTCEUR)
        return self._base_asset

    def get_quote_asset(self) -> Asset:
        # related to price (EUR in BTCEUR)
        return self._quote_asset
