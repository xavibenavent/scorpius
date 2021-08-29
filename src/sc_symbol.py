# sc_symbol.py

from typing import Dict


class Asset:
    def __init__(self,
                 name: str,
                 pv: int  # precision for visualization
                 ):
        self._name = name.upper()
        self._pv = pv

    def name(self) -> str:
        return self._name

    def pv(self) -> int:
        return self._pv


class Symbol:
    def __init__(self, name: str, base_asset: Asset, quote_asset: Asset, filters: Dict, config_data: Dict):
        self.name = name.upper()
        self._base_asset = base_asset
        self._quote_asset = quote_asset
        self.filters = filters
        self.config_data = config_data

    # def get_name(self) -> str:
    #     return self._base_asset.name() + self._quote_asset.name()

    def base_asset(self) -> Asset:
        # related to quantity (BTC in BTCEUR)
        return self._base_asset

    def get_quote_asset(self) -> Asset:
        # related to price (EUR in BTCEUR)
        return self._quote_asset
