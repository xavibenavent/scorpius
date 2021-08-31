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

    def get_app_mode(self) -> str:
        return self._config.get('APP_MODE', 'client_mode')

    def get_fake_cmp_mode(self) -> str:
        return self._config.get('FAKE_CMP_MODE', 'simulator_mode')

    def get_simulator_data(self, symbol_name: str) -> Dict:
        return dict(self._config.items(symbol_name + '_SIMULATOR_DATA'))

    def get_simulator_update_rate(self) -> float:
        return float(self._config.get('SIMULATOR_GLOBAL_DATA', 'update_rate'))

    def get_simulator_global_data(self) -> Dict:
        return dict(self._config.items('SIMULATOR_GLOBAL_DATA'))

    def get_simulator_choice_values(self, symbol_name: str) -> List[float]:
        # convert [1, 2, 3] from config.ini in list of float
        values_s = self._config.get(symbol_name + '_SIMULATOR_DATA', 'cmp_generator_choice_values')
        return [float(value.replace(' ', '').replace('[', '').replace(']', ''))
                for value in values_s.split(',')]

    def get_max_allowed_loss_for_liquidity(self, symbol_name: str) -> float:
        return float(self._config.get(symbol_name, 'accepted_loss_to_get_liquidity'))