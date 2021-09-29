# sc_action.py

from binance import enums as k_binance


class Action:
    def __init__(self, action_id: str, side: k_binance, qty: float, price: float):
        self.action_id = action_id
        self.side = side
        self.qty = qty
        self.price = price

    def get_tuple(self) -> (str, k_binance, float, float):
        return self.action_id, self.side, self.qty, self.price

    def __repr__(self):
        return f'{self.action_id} {self.side} {self.qty} {self.price}'
