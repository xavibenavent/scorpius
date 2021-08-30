# thread_cmp_generator.py
from typing import Callable
import time
from random import choice


class ThreadCmpGenerator:
    def __init__(self, interval: float, f_callback: Callable[[float], None]):
        self._running = True
        self.f_callback = f_callback
        self._interval = interval

    def terminate(self):
        print('cmp thread terminated')
        self._running = False

    def run(self):
        # generate a new cmp every _interval seconds and send it to update_cmp
        print('thread started')
        while self._running:
            # print(f'cmp thread running: {self._running}')
            time.sleep(self._interval)
            new_cmp = choice([-12, -10, -4, 0, 4, 10, 12])
            self.f_callback(new_cmp)
