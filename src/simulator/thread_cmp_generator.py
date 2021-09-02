# thread_cmp_generator.py
from typing import Callable, List, Dict
import time
from random import choice


class ThreadCmpGenerator:
    def __init__(self,
                 symbol_name: str,
                 interval: float,
                 f_callback: Callable[[Dict], None],
                 choice_values: List[float]):
        self._running = True
        self._symbol_name = symbol_name
        self.f_callback = f_callback
        self._interval = interval
        self._choice_values = choice_values

    def terminate(self):
        print(f'cmp thread for symbol {self._symbol_name} terminated')
        self._running = False
        raise Exception(f'generator for symbol {self._symbol_name} terminated')  # todo: check if it is feasible

    def run(self):
        # generate a new cmp, between choice_values, every _interval seconds and send it to update_cmp callback function
        print(f'cmp thread for symbol {self._symbol_name} started')
        while self._running:
            time.sleep(self._interval)
            msg = dict(
                e='24hrTicker',
                s=self._symbol_name,
                c=str(choice(self._choice_values))
            )
            self.f_callback(msg)
