# sc_symbol.py

from typing import Dict


class Asset:
    def __init__(self,
                 name: str,
                 # precision_for_visualization: int
                 ):
        self._name = name.upper()
        self._precision_for_visualization = self.set_precision_for_visualization(name=name)

    def get_name(self) -> str:
        return self._name

    def get_precision_for_visualization(self) -> int:
        return self._precision_for_visualization

    def set_precision_for_visualization(self, name: str) -> int:
        # todo: move to config.ini
        precisions = {
            'BTC': 6,
            'BNB': 6,
            'EUR': 2,
            'TVK': 2,
            'ETH': 6,
            'DOGE': 2
        }
        if name in precisions.keys():
            return precisions[name]
        else:
            return 2  # default value


class Symbol:
    def __init__(self, name: str, base_asset: Asset, quote_asset: Asset, filters: Dict, config_data: Dict):
        self.name = name.upper()
        self._base_asset = base_asset
        self._quote_asset = quote_asset
        self.filters = filters
        self.config_data = config_data

    def get_name(self) -> str:
        return self._base_asset.get_name() + self._quote_asset.get_name()

    def get_base_asset(self) -> Asset:
        # related to quantity (BTC in BTCEUR)
        return self._base_asset

    def get_quote_asset(self) -> Asset:
        # related to price (EUR in BTCEUR)
        return self._quote_asset
