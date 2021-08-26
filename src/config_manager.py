# config_manager.py

import configparser
from typing import List, Dict


class ConfigManager:
    def __init__(self, config_file: str):
        # set config
        self._config = configparser.ConfigParser()
        self._config.read(config_file)

        # create list from config.ini: symbols = [BTCEUR, BNBBTC]
        self._symbol_names = [s.replace(' ', '').replace('[', '').replace(']', '').replace("'", "")
                              for s in self._config.get('BINANCE', 'symbols').split(',')]

    def get_symbol_names(self) -> List[str]:
        return self._symbol_names

    def get_symbol_data(self, symbol_name: str) -> Dict:
        return dict(self._config.items(symbol_name))
